from __future__ import annotations

import asyncio
import base64
import logging
from typing import Annotated, Any

from fastapi import APIRouter, HTTPException, Query, Response
from fastapi.responses import JSONResponse, RedirectResponse

from app.api.utils import or_404
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
    BackfillEmbeddingsRequest,
    BatchDeleteRequest,
    DuplicateCheckRequest,
    GenerationRequest,
    Question,
    QuestionStatus,
    RAGContextRequest,
    SemanticSearchRequest,
    SingleStatusUpdateRequest,
    StatusUpdateRequest,
)
from app.services import (
    backfill_question_embeddings,
    build_csv_headers,
    build_csv_row,
    evaluate_duplicate,
    evaluate_duplicate_rag,
    find_similar_questions,
    generate_questions_csv,
    hybrid_search_questions,
    retrieve_rag_exemplar_context,
)

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
) -> dict[str, Any]:
    """Lists saved questions from the Question Bank repository along with aggregated metrics."""
    effective_status = None if status == "all" else (status or "in_bank")
    questions, matching_count, metrics = await asyncio.gather(
        get_questions(
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
        ),
        count_questions(
            section=section,
            difficulty=difficulty,
            search=search,
            combination_id=combination_id,
            run_id=run_id,
            batch_id=batch_id,
            passage_id=passage_id,
            status=effective_status,
        ),
        get_repository_metrics(status=effective_status),
    )
    dumped = [q.model_dump() for q in questions]

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


async def _require_question(question_id: str) -> Question:
    """Loads a question or answers 404 (the repeated get-or-404 of this module)."""
    return or_404(await get_question_by_id(question_id), "Question not found")


@router.get("/questions/{question_id}")
async def get_single_question(question_id: str) -> dict[str, Any]:
    """Retrieves a single question by UUID4 primary key."""
    return (await _require_question(question_id)).model_dump()


_ALLOWED_IMAGE_TYPES = frozenset({"image/png", "image/jpeg", "image/webp", "image/gif"})
_IMAGE_SAFETY_HEADERS = {
    # nosniff already comes from the global security-headers middleware
    "Content-Security-Policy": "sandbox; default-src 'none'; style-src 'unsafe-inline'",
}


@router.get("/questions/{question_id}/image")
async def get_question_image(question_id: str):
    """Serves the visual stimulus image (AI FLUX image or Vector SVG diagram) for a question."""
    q = await _require_question(question_id)

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
            logger.error("Failed to decode base64 image: %s", e)
            raise HTTPException(status_code=500, detail="Invalid base64 image encoding") from e

    if not img_url.startswith(("https://", "http://")):
        raise HTTPException(status_code=415, detail="Unsupported image location")
    return RedirectResponse(url=img_url)


MAX_BULK_QUESTIONS: int = 500  # Must equal the le= guard on the GET /questions limit param
_VALID_QUESTION_STATUSES = frozenset(s.value for s in QuestionStatus)


def _require_valid_status(question: Question) -> None:
    """Rejects statuses the database CHECK constraint would refuse (otherwise a 500)."""
    if question.status not in _VALID_QUESTION_STATUSES:
        raise HTTPException(status_code=422, detail=f"Invalid question status: {question.status!r}")


@router.post("/questions")
async def approve_and_save_question(question: Question) -> dict[str, Any]:
    """
    Admin approval endpoint: persists an approved candidate question into the Question Bank repository.
    """
    _require_valid_status(question)
    saved = await save_question(question)
    logger.info(
        "Question approved by Admin and saved to Question Bank: %s (%s)",
        saved.id,
        saved.section_label,
    )
    return {"success": True, "question": saved.model_dump()}


@router.post("/questions/batch")
async def batch_approve_and_save_questions(questions: list[Question]) -> dict[str, Any]:
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
    logger.info("Atomic batch approved %s questions into Question Bank.", len(saved_list))
    return {"success": True, "saved_count": len(saved_list), "ids": saved_list}


@router.delete("/questions/{question_id}")
async def remove_question(question_id: str) -> dict[str, Any]:
    """Deletes a question by primary key ID."""
    or_404(await delete_question(question_id), "Question not found")
    return {"success": True}


@router.post("/questions/delete-batch")
async def remove_questions_batch(payload: BatchDeleteRequest) -> dict[str, Any]:
    """Bulk Admin deletion endpoint: removes multiple questions in a single atomic SQL transaction."""
    deleted_count = await delete_questions_batch(payload.ids)
    logger.info("Bulk deleted %s questions from Question Bank.", deleted_count)
    return {"success": True, "deleted_count": deleted_count}


@router.delete("/questions/{question_id}/permanent")
async def purge_single_question(question_id: str) -> dict[str, Any]:
    """Permanently deletes a single question by ID from the database."""
    or_404(await hard_delete_question(question_id), "Question not found")
    logger.info("Permanently purged question %s from database.", question_id)
    return {"success": True}


@router.post("/questions/purge-batch")
async def purge_questions_batch_endpoint(payload: BatchDeleteRequest) -> dict[str, Any]:
    """Permanently deletes multiple questions from database."""
    purged_count = await hard_delete_questions_batch(payload.ids)
    logger.info("Permanently purged %s questions from database.", purged_count)
    return {"success": True, "purged_count": purged_count}


@router.post("/questions/{question_id}/restore")
async def restore_single_question(question_id: str) -> dict[str, Any]:
    """Restores a soft-deleted question and its associated passage back to active status."""
    restored = or_404(await restore_question(question_id), "Question not found")
    logger.info("Restored question %s to active status.", question_id)
    return {"success": True, "question": restored.model_dump()}


@router.post("/questions/update-status")
async def batch_update_status(payload: StatusUpdateRequest) -> dict[str, Any]:
    """Bulk update question lifecycle status."""
    status_val = payload.status
    updated_count = await batch_update_question_status(payload.ids, status_val)
    logger.info("Bulk updated %s questions to status '%s'.", updated_count, status_val)
    return {"success": True, "updated_count": updated_count, "status": status_val}


@router.patch("/questions/{question_id}/status")
async def update_single_status(
    question_id: str, payload: SingleStatusUpdateRequest
) -> dict[str, Any]:
    """Update single question lifecycle status."""
    new_status = payload.status
    or_404(await update_question_status(question_id, new_status), "Question not found")
    return {"success": True, "question_id": question_id, "status": new_status}


@router.post("/questions/{question_id}/override-duplicate")
async def override_question_duplicate_endpoint(question_id: str) -> dict[str, Any]:
    """
    Admin/Reviewer override endpoint: marks a question's duplicate alert as manually overridden
    and updates its status to 'in_bank'.
    """
    updated_q = or_404(await override_question_duplicate(question_id), "Question not found")
    logger.info("Duplicate alert manually overridden for Question %s by reviewer.", question_id)
    return {"success": True, "question": updated_q.model_dump()}


@router.post("/questions/check-duplicate")
async def check_question_duplicate_endpoint(payload: DuplicateCheckRequest) -> dict[str, Any]:
    """
    On-demand deduplication check: evaluates a candidate question draft against existing bank items.
    Leverages pgvector RAG semantic search and in-flight references when enabled.
    """
    section = payload.section or ""
    subtopic = payload.subtopic or ""
    ref_pool = await get_subtopic_reference_questions(section=section, subtopic=subtopic, limit=50)
    if config.ENABLE_PGVECTOR_RAG:
        dup_res = await evaluate_duplicate_rag(
            payload.model_dump(), ref_pool, threshold=config.DUPLICATE_API_THRESHOLD
        )
    else:
        dup_res = evaluate_duplicate(
            payload.model_dump(), ref_pool, threshold=config.DUPLICATE_API_THRESHOLD
        )
    return {"success": True, "duplicate_check": dup_res.model_dump()}


@router.post("/questions/semantic-search")
async def semantic_search_questions_endpoint(payload: SemanticSearchRequest) -> dict[str, Any]:
    """
    Finds semantically similar questions using pgvector cosine similarity or hybrid (vector + FTS) search.
    """
    if payload.hybrid:
        matches = await hybrid_search_questions(
            payload.query,
            section=payload.section,
            subtopic=payload.subtopic,
            limit=payload.limit,
        )
    else:
        matches = await find_similar_questions(
            payload.query,
            section=payload.section,
            subtopic=payload.subtopic,
            limit=payload.limit,
            min_similarity=payload.min_similarity,
        )
    return {
        "success": True,
        "count": len(matches),
        "query": payload.query,
        "results": [m.to_dict() for m in matches],
    }


@router.post("/questions/rag-context")
async def get_rag_context_endpoint(payload: RAGContextRequest) -> dict[str, Any]:
    """
    Retrieves high-scoring few-shot exemplars and anti-collision neighbor avoidance stems
    to ground question generation workflows.
    """
    gen_req = GenerationRequest(
        section=payload.section,
        subtopic=payload.subtopic or None,
        thematic_angle=payload.thematic_angle or None,
    )
    rag_ctx = await retrieve_rag_exemplar_context(gen_req, limit=payload.limit)
    return {"success": True, "rag_context": rag_ctx.to_dict()}


@router.post("/questions/backfill-embeddings")
async def backfill_embeddings_endpoint(payload: BackfillEmbeddingsRequest) -> dict[str, Any]:
    """
    Triggers batch backfilling of 1536-dimensional vector embeddings for questions lacking vectors.
    """
    result = await backfill_question_embeddings(batch_size=payload.batch_size)
    return {"success": True, **result}


# Backward-compatible aliases for CSV export builders
_build_csv_headers = build_csv_headers
_build_csv_row = build_csv_row


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

    csv_data = generate_questions_csv(questions)
    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=mcat_question_bank.csv"},
    )
