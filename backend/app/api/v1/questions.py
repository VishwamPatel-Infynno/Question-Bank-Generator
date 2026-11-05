from __future__ import annotations

import base64
import csv
import io
import logging
from typing import Annotated, Any

from fastapi import APIRouter, HTTPException, Query, Response
from fastapi.responses import JSONResponse, RedirectResponse

from app.core.config import config
from app.repositories import (
    batch_update_question_status,
    count_questions,
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
    BatchDeleteRequest,
    DuplicateCheckRequest,
    Question,
    QuestionStatus,
    SingleStatusUpdateRequest,
    StatusUpdateRequest,
)
from app.services import evaluate_duplicate

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
    sort_by: Annotated[str | None, Query()] = "newest",
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
        sort_by=sort_by,
        limit=limit,
        offset=offset,
        slim=slim,
    )
    matching_count = await count_questions(
        section=section,
        difficulty=difficulty,
        search=search,
        combination_id=combination_id,
        run_id=run_id,
        batch_id=batch_id,
        passage_id=passage_id,
        status=effective_status,
    )
    dumped = [q.model_dump() for q in questions]

    metrics = await get_repository_metrics(status=effective_status)

    return {
        "questions": dumped,
        "total_count": matching_count,
        "bank_total_count": metrics["total_count"],
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


_ALLOWED_IMAGE_TYPES = frozenset({"image/png", "image/jpeg", "image/webp", "image/gif"})
_IMAGE_SAFETY_HEADERS = {
    # nosniff already comes from the global security-headers middleware
    "Content-Security-Policy": "sandbox; default-src 'none'; style-src 'unsafe-inline'",
}


@router.get("/questions/{question_id}/image")
async def get_question_image(question_id: str):
    """Serves the visual stimulus image (AI FLUX image or Vector SVG diagram) for a question."""
    q = await get_question_by_id(question_id)
    if not q:
        raise HTTPException(status_code=404, detail="Question not found")

    img_url = q.image_url
    if not img_url and q.image_svg:
        # Sandboxed so an SVG opened directly can never run script on the API origin
        return Response(
            content=q.image_svg,
            media_type="image/svg+xml",
            headers=_IMAGE_SAFETY_HEADERS,
        )

    if not img_url:
        raise HTTPException(
            status_code=404, detail="No visual stimulus image found for this question"
        )

    if img_url.startswith("data:"):
        try:
            header, encoded = img_url.split(",", 1)
            media_type = header.split(";")[0].replace("data:", "") or "image/jpeg"
            if media_type not in _ALLOWED_IMAGE_TYPES:
                raise HTTPException(status_code=415, detail="Unsupported image type")
            image_bytes = base64.b64decode(encoded)
            return Response(
                content=image_bytes, media_type=media_type, headers=_IMAGE_SAFETY_HEADERS
            )
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to decode base64 image: {e}")
            raise HTTPException(status_code=500, detail="Invalid base64 image encoding") from e

    if not img_url.startswith(("https://", "http://")):
        raise HTTPException(status_code=415, detail="Unsupported image location")
    return RedirectResponse(url=img_url)


MAX_BULK_QUESTIONS = 500
_VALID_QUESTION_STATUSES = frozenset(s.value for s in QuestionStatus)


def _require_valid_status(question: Question) -> None:
    """Rejects statuses the database CHECK constraint would refuse (otherwise a 500)."""
    if question.status not in _VALID_QUESTION_STATUSES:
        raise HTTPException(status_code=422, detail=f"Invalid question status: {question.status!r}")


@router.post("/questions")
async def approve_and_save_question(question: Question):
    """
    Admin approval endpoint: persists an approved candidate question into the Question Bank repository.
    """
    _require_valid_status(question)
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
    if len(questions) > MAX_BULK_QUESTIONS:
        raise HTTPException(
            status_code=413, detail=f"At most {MAX_BULK_QUESTIONS} questions per request"
        )
    for q in questions:
        _require_valid_status(q)
    saved_list = await save_questions_batch(questions)
    logger.info(f"Atomic batch approved {len(saved_list)} questions into Question Bank.")
    return {"success": True, "saved_count": len(saved_list), "ids": saved_list}


@router.delete("/questions/{question_id}")
async def remove_question(question_id: str):
    """Deletes a question by primary key ID."""
    success = await delete_question(question_id)
    if not success:
        raise HTTPException(status_code=404, detail="Question not found")
    return {"success": True}


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
    updated_count = await batch_update_question_status(payload.ids, status_val)
    logger.info(f"Bulk updated {updated_count} questions to status '{status_val}'.")
    return {"success": True, "updated_count": updated_count, "status": status_val}


@router.patch("/questions/{question_id}/status")
async def update_single_status(question_id: str, payload: SingleStatusUpdateRequest):
    """Update single question lifecycle status."""
    new_status = payload.status.value if hasattr(payload.status, "value") else str(payload.status)
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
async def check_question_duplicate_endpoint(payload: DuplicateCheckRequest):
    """
    On-demand deduplication check: evaluates a candidate question draft against existing bank items.
    """
    section = payload.section or ""
    subtopic = payload.subtopic or ""
    ref_pool = await get_subtopic_reference_questions(section=section, subtopic=subtopic, limit=50)
    dup_res = evaluate_duplicate(
        payload.model_dump(), ref_pool, threshold=config.DUPLICATE_API_THRESHOLD
    )
    return {"success": True, "duplicate_check": dup_res.model_dump()}


def _build_csv_headers() -> list[str]:
    """Returns column header labels for Question Bank CSV export."""
    return [
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


def _build_csv_row(q: Question) -> list[Any]:
    """Constructs a single CSV export row for a Question schema record."""
    opts = {opt.id: opt.text for opt in q.options}
    if q.image_url:
        img_val = f"/api/questions/{q.id}/image" if q.image_url.startswith("data:") else q.image_url
    elif q.image_svg:
        img_val = f"/api/questions/{q.id}/image"
    else:
        img_val = ""

    return [
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


@router.get("/export")
async def export_questions(
    export_format: Annotated[str, Query(alias="format", pattern="^(json|csv)$")] = "json",
):
    """Exports Question Bank in JSON or CSV format including manager matrix fields and UUIDs."""
    questions = await get_questions(status="in_bank")

    if export_format == "json":
        data = [q.model_dump() for q in questions]
        return JSONResponse(
            content=data,
            headers={"Content-Disposition": "attachment; filename=mcat_question_bank.json"},
        )

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(_build_csv_headers())
    for q in questions:
        writer.writerow(_build_csv_row(q))
    csv_data = output.getvalue()
    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=mcat_question_bank.csv"},
    )
