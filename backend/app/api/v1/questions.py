import base64
import csv
import io
import logging
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, Response
from fastapi.responses import JSONResponse, RedirectResponse

from app.repositories.question_repository import (
    batch_update_question_status,
    delete_question,
    delete_questions_batch,
    get_question_by_id,
    get_question_status_counts,
    get_questions,
    get_repository_metrics,
    get_subtopic_reference_questions,
    hard_delete_question,
    hard_delete_questions_batch,
    override_question_duplicate,
    restore_question,
    save_question,
    save_questions_batch,
    update_question_status,
)
from app.schemas import (
    VALID_QUESTION_STATUSES,
    BatchDeleteRequest,
    DuplicateCheckRequest,
    Question,
    SingleStatusUpdateRequest,
    StatusUpdateRequest,
)
from app.services.deduplication import evaluate_duplicate

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Question Bank"])


@router.get("/questions")
async def list_questions(
    section: Annotated[str | None, Query()] = None,
    difficulty: Annotated[str | None, Query()] = None,
    search: Annotated[str | None, Query()] = None,
    combination_id: Annotated[str | None, Query()] = None,
    run_id: Annotated[str | None, Query()] = None,
    batch_id: Annotated[str | None, Query()] = None,
    passage_id: Annotated[str | None, Query()] = None,
    status: Annotated[str | None, Query()] = "in_bank",
    limit: Annotated[int | None, Query(ge=1, le=500)] = None,
    offset: Annotated[int | None, Query(ge=0)] = 0,
    slim: Annotated[bool, Query()] = False,
):
    """Lists saved questions from the Question Bank repository along with aggregated metrics."""
    effective_status = None if status == "all" else (status or "in_bank")
    questions = await get_questions(
        section=section,
        difficulty=difficulty,
        search=search,
        combination_id=combination_id,
        run_id=run_id,
        batch_id=batch_id,
        passage_id=passage_id,
        status=effective_status,
        limit=limit,
        offset=offset,
        slim=slim,
    )
    dumped = [q.model_dump() for q in questions]

    metrics = await get_repository_metrics(status=effective_status)

    return {
        "questions": dumped,
        "total_count": metrics["total_count"],
        "total_tokens": metrics["total_tokens"],
        "total_cost_usd": metrics["total_cost_usd"],
    }


@router.get("/questions/counts")
async def get_question_counts():
    """Returns counts of questions grouped by lifecycle status."""
    return await get_question_status_counts()


@router.get("/questions/{question_id}")
async def get_single_question(question_id: str):
    """Retrieves a single question by UUID4 primary key."""
    q = await get_question_by_id(question_id)
    if not q:
        raise HTTPException(status_code=404, detail="Question not found")
    return q.model_dump()


@router.get("/questions/{question_id}/image")
async def get_question_image(question_id: str):
    """Serves the visual stimulus image (AI FLUX image or Vector SVG diagram) for a question."""
    q = await get_question_by_id(question_id)
    if not q:
        raise HTTPException(status_code=404, detail="Question not found")

    img_url = q.image_url
    if not img_url and q.image_svg:
        return Response(content=q.image_svg, media_type="image/svg+xml")

    if not img_url:
        raise HTTPException(
            status_code=404, detail="No visual stimulus image found for this question"
        )

    if img_url.startswith("data:"):
        try:
            header, encoded = img_url.split(",", 1)
            media_type = header.split(";")[0].replace("data:", "") or "image/jpeg"
            image_bytes = base64.b64decode(encoded)
            return Response(content=image_bytes, media_type=media_type)
        except Exception as e:
            logger.error(f"Failed to decode base64 image: {e}")
            raise HTTPException(status_code=500, detail="Invalid base64 image encoding") from e

    return RedirectResponse(url=img_url)


@router.post("/questions")
async def approve_and_save_question(question: Question):
    """
    Admin approval endpoint: persists an approved candidate question into the Question Bank repository.
    """
    saved = await save_question(question)
    logger.info(
        f"Question approved by Admin and saved to Question Bank: {saved.id} ({saved.section_label})"
    )
    return {"success": True, "question": saved.model_dump()}


@router.post("/questions/batch")
async def batch_approve_and_save_questions(questions: list[Question]):
    """
    Bulk Admin approval endpoint: persists an array of approved candidate questions into the Question Bank repository in a single atomic transaction.
    """
    saved_list = await save_questions_batch(questions)
    logger.info(f"Atomic batch approved {len(saved_list)} questions into Question Bank.")
    return {"success": True, "saved_count": len(saved_list), "ids": saved_list}


@router.delete("/questions/{question_id}")
async def remove_question(question_id: str):
    """Deletes a question by primary key ID."""
    success = await delete_question(question_id)
    return {"success": success}


@router.post("/questions/delete-batch")
async def remove_questions_batch(payload: BatchDeleteRequest):
    """Bulk Admin deletion endpoint: removes multiple questions in a single atomic SQL transaction."""
    deleted_count = await delete_questions_batch(payload.ids)
    logger.info(f"Bulk deleted {deleted_count} questions from Question Bank.")
    return {"success": True, "deleted_count": deleted_count}


@router.delete("/questions/{question_id}/permanent")
async def purge_single_question(question_id: str):
    """Permanently deletes a single question by ID from the database."""
    success = await hard_delete_question(question_id)
    if not success:
        raise HTTPException(status_code=404, detail="Question not found")
    logger.info(f"Permanently purged question {question_id} from database.")
    return {"success": True}


@router.post("/questions/purge-batch")
async def purge_questions_batch_endpoint(payload: BatchDeleteRequest):
    """Permanently deletes multiple questions from database."""
    purged_count = await hard_delete_questions_batch(payload.ids)
    logger.info(f"Permanently purged {purged_count} questions from database.")
    return {"success": True, "purged_count": purged_count}


@router.post("/questions/{question_id}/restore")
async def restore_single_question(question_id: str):
    """Restores a soft-deleted question and its associated passage back to active status."""
    restored = await restore_question(question_id)
    if not restored:
        raise HTTPException(status_code=404, detail="Question not found")
    logger.info(f"Restored question {question_id} to active status.")
    return {"success": True, "question": restored.model_dump()}


@router.post("/questions/update-status")
async def batch_update_status(payload: StatusUpdateRequest):
    """Bulk update question lifecycle status."""
    status_val = payload.status.value if hasattr(payload.status, "value") else str(payload.status)
    if status_val not in VALID_QUESTION_STATUSES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status '{status_val}'. Must be one of {sorted(VALID_QUESTION_STATUSES)}",
        )
    updated_count = await batch_update_question_status(payload.ids, status_val)
    logger.info(f"Bulk updated {updated_count} questions to status '{status_val}'.")
    return {"success": True, "updated_count": updated_count, "status": status_val}


@router.patch("/questions/{question_id}/status")
async def update_single_status(question_id: str, payload: SingleStatusUpdateRequest | dict):
    """Update single question lifecycle status."""
    if isinstance(payload, dict):
        payload = SingleStatusUpdateRequest(**payload)
    new_status = payload.status.value if hasattr(payload.status, "value") else str(payload.status)
    if not new_status or new_status not in VALID_QUESTION_STATUSES:
        raise HTTPException(
            status_code=400,
            detail=f"Missing or invalid 'status'. Must be one of {sorted(VALID_QUESTION_STATUSES)}",
        )
    success = await update_question_status(question_id, new_status)
    if not success:
        raise HTTPException(status_code=404, detail="Question not found")
    return {"success": True, "question_id": question_id, "status": new_status}


@router.post("/questions/{question_id}/override-duplicate")
async def override_question_duplicate_endpoint(question_id: str):
    """
    Admin/Reviewer override endpoint: marks a question's duplicate alert as manually overridden
    and updates its status to 'in_bank'.
    """
    updated_q = await override_question_duplicate(question_id)
    if not updated_q:
        raise HTTPException(status_code=404, detail="Question not found")
    logger.info(f"Duplicate alert manually overridden for Question {question_id} by reviewer.")
    return {"success": True, "question": updated_q.model_dump()}


@router.post("/questions/check-duplicate")
async def check_question_duplicate_endpoint(payload: DuplicateCheckRequest | dict):
    """
    On-demand deduplication check: evaluates a candidate question draft against existing bank items.
    """
    if isinstance(payload, dict):
        payload = DuplicateCheckRequest(**payload)
    section = payload.section or ""
    subtopic = payload.subtopic or ""
    ref_pool = await get_subtopic_reference_questions(section=section, subtopic=subtopic, limit=50)
    dup_res = evaluate_duplicate(payload.model_dump(), ref_pool, threshold=0.80)
    return {"success": True, "duplicate_check": dup_res.model_dump()}


@router.get("/export")
async def export_questions(
    format: Annotated[str, Query(pattern="^(json|csv)$")] = "json",
):
    """Exports Question Bank in JSON or CSV format including manager matrix fields and UUIDs."""
    questions = await get_questions(status="in_bank")

    if format == "json":
        data = [q.model_dump() for q in questions]
        return JSONResponse(
            content=data,
            headers={"Content-Disposition": "attachment; filename=mcat_question_bank.json"},
        )

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(
        [
            "ID",
            "Run_ID",
            "Batch_ID",
            "Combination_ID",
            "Section",
            "Subcategory",
            "Difficulty",
            "MCAT_Scaled_Score",
            "AAMC_Skill",
            "Content_Domain",
            "Question_Type",
            "Interaction_Type",
            "Primary_Trap",
            "Passage_Required",
            "Visual_Type",
            "Image_URL",
            "Image_Description",
            "Stimulus",
            "Question Stem",
            "Option A",
            "Option B",
            "Option C",
            "Option D",
            "Correct Answer",
            "Explanation",
            "Final Score",
            "Cycles",
            "Created At",
        ]
    )
    for q in questions:
        opts = {opt.id: opt.text for opt in q.options}
        if q.image_url:
            if q.image_url.startswith("data:"):
                img_val = f"/api/questions/{q.id}/image"
            else:
                img_val = q.image_url
        elif q.image_svg:
            img_val = f"/api/questions/{q.id}/image"
        else:
            img_val = ""
        writer.writerow(
            [
                q.id,
                q.run_id or "",
                q.batch_id or "",
                q.combination_id or "",
                q.section_label,
                q.subtopic,
                q.difficulty,
                q.mcat_scaled_score or "",
                q.aamc_skill or "",
                q.content_domain or "",
                q.question_type or "",
                q.interaction_type or "single_choice",
                q.primary_trap or "",
                q.passage_required or "",
                q.visual_type or "None",
                img_val,
                q.image_description or "",
                q.stimulus_text or "",
                q.question_stem,
                opts.get("A", ""),
                opts.get("B", ""),
                opts.get("C", ""),
                opts.get("D", ""),
                q.correct_answer_id,
                q.explanation,
                q.final_score,
                q.iteration_count,
                q.created_at,
            ]
        )
    csv_data = output.getvalue()
    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=mcat_question_bank.csv"},
    )
