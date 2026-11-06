from __future__ import annotations

import logging
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.security import limit_active_batches, limit_generation_requests
from app.core.config import config
from app.repositories import (
    batch_update_question_status,
    delete_batch,
    get_batch_by_id,
    get_batches,
    get_jobs_by_batch_id,
    get_questions,
    hard_delete_questions_batch,
    refresh_batch_aggregates,
    save_batch,
)
from app.schemas import (
    BATCH_STATUSES,
    BatchStatus,
    GenerationBatch,
    GenerationRequest,
    ResolveDuplicatesRequest,
    is_question_active,
)
from app.services import (
    cancel_all_background_batches,
    cluster_questions,
    get_active_batch_metrics,
    is_batch_running,
    launch_background_batch,
    refill_batch_deficit,
    retry_incomplete_jobs_for_batch,
    stop_background_batch,
)
from app.services.batch_concurrency import forget_batch_request

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Generation Batches"])


def _or_404(value: Any, detail: str) -> Any:
    """Answers 404 when a lookup or a targeted mutation found nothing."""
    if not value:
        raise HTTPException(status_code=404, detail=detail)
    return value


async def _require_batch(batch_id: str) -> GenerationBatch:
    """Loads a batch or answers 404 (the repeated get-or-404 of this module)."""
    return _or_404(await get_batch_by_id(batch_id), "Batch not found")


@router.post(
    "/batches/start",
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[Depends(limit_generation_requests), Depends(limit_active_batches)],
)
async def start_batch_generation(req: GenerationRequest) -> dict[str, Any]:
    """
    Launches an asynchronous background batch generation.
    Creates 1 batch record and constituent job records (1 job producing 5 questions for a mini-batch,
    or 10 jobs producing 5 questions each for a 50-question full mock section).
    Returns immediately with batch and job details while generation runs in the background.
    """
    try:
        batch, jobs = await launch_background_batch(req)
        return {
            "success": True,
            "message": f"Background batch {batch.id} launched with {len(jobs)} {'job' if len(jobs) == 1 else 'jobs'} ({batch.target_count} questions total).",
            "batch": batch.model_dump(),
            "jobs": [j.model_dump() for j in jobs],
        }
    except Exception as e:
        logger.error("Failed to start background batch: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to initialize background batch.") from e


@router.get("/batches")
async def list_batches(
    section: Annotated[str | None, Query()] = None,
    status_filter: Annotated[str | None, Query(alias="status")] = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> dict[str, Any]:
    """Lists generation batches (newest first, paginated) with progress counts and concurrency metrics.

    Rows omit ``request_payload``; fetch a single batch to read it.
    """
    batches = await get_batches(section=section, status=status_filter, limit=limit, offset=offset)
    # Count running batches over the whole table so pagination never hides them from the monitor
    active_count = len(await get_batches(section=section, status=BatchStatus.IN_PROGRESS))
    metrics = get_active_batch_metrics()
    return {
        "batches": [b.model_dump() for b in batches],
        "active_running_batches": active_count,
        "concurrency_metrics": metrics,
    }


@router.get("/batches/{batch_id}")
async def get_single_batch(batch_id: str) -> dict[str, Any]:
    """
    Retrieves a single generation batch along with its 10 jobs and all generated questions.
    Questions are organized so the client can easily view questions per job.
    """
    b = await _require_batch(batch_id)

    jobs = await get_jobs_by_batch_id(batch_id)
    linked_questions = await get_questions(batch_id=batch_id, include_deleted=True)
    # Discarded duplicate questions must not be attached to jobs or displayed as active/deleted bank questions
    visible_questions = [q for q in linked_questions if q.status != "discarded"]

    # Group questions by job_id or run_id
    # Serialize each question once; the grouped and flat views share the same dicts.
    questions_by_job: dict[str, list[dict]] = {}
    visible_dumps: list[dict] = []
    for q in visible_questions:
        q_dump = q.model_dump()
        visible_dumps.append(q_dump)
        j_key = q.job_id or q.run_id or "unassigned"
        questions_by_job.setdefault(j_key, []).append(q_dump)

    # Augment jobs with their questions
    jobs_with_questions = []
    for j in jobs:
        j_dump = j.model_dump()
        j_dump["questions"] = questions_by_job.get(j.id, [])
        jobs_with_questions.append(j_dump)

    return {
        "batch": b.model_dump(),
        "jobs": jobs_with_questions,
        "questions": visible_dumps,
        "total_questions_count": len(visible_dumps),
    }


@router.post("/batches/{batch_id}/stop")
async def stop_single_batch(batch_id: str) -> dict[str, Any]:
    """Gracefully halts active background jobs for a batch without deleting saved questions."""
    await _require_batch(batch_id)
    await stop_background_batch(batch_id)
    refreshed = await get_batch_by_id(batch_id)
    return {
        "success": True,
        "message": f"Batch {batch_id} execution stopped.",
        "batch": refreshed.model_dump() if refreshed else None,
    }


@router.post(
    "/batches/{batch_id}/retry",
    dependencies=[Depends(limit_generation_requests), Depends(limit_active_batches)],
)
async def retry_single_batch(batch_id: str, req: GenerationRequest | None = None) -> dict[str, Any]:
    """Re-launches failed or cancelled jobs for a batch into the global worker pool."""
    await _require_batch(batch_id)
    batch, jobs = await retry_incomplete_jobs_for_batch(batch_id, req)
    if not jobs:
        raise HTTPException(
            status_code=400,
            detail=(
                f"All incomplete sets in batch {batch_id} have already reached the maximum 3-trial limit "
                "or have already completed, and cannot be retried."
            ),
        )
    return {
        "success": True,
        "message": f"Resuming incomplete jobs for batch {batch_id}.",
        "batch": batch.model_dump() if batch else None,
        "jobs": [j.model_dump() for j in jobs],
    }


@router.post("/batches/cancel-all")
async def cancel_all_batches() -> dict[str, Any]:
    """Gracefully halts all active background batches."""
    stopped_count = await cancel_all_background_batches()
    return {
        "success": True,
        "message": f"Successfully stopped {stopped_count} running batches.",
        "stopped_count": stopped_count,
    }


@router.delete("/batches/{batch_id}")
async def delete_single_batch(batch_id: str) -> dict[str, Any]:
    """Deletes a generation batch and cascades delete to jobs and questions."""
    await stop_background_batch(batch_id)
    forget_batch_request(batch_id)
    _or_404(await delete_batch(batch_id), "Batch not found")
    return {"success": True, "message": f"Batch {batch_id} deleted successfully."}


@router.post("/batches")
async def create_or_update_batch(batch: GenerationBatch) -> dict[str, Any]:
    """Admin endpoint to create or update a generation batch record."""
    if batch.status not in BATCH_STATUSES:
        raise HTTPException(status_code=422, detail=f"Invalid batch status: {batch.status!r}")
    saved = await save_batch(batch)
    return {"success": True, "batch": saved.model_dump()}


@router.get("/batches/{batch_id}/duplicate-clusters")
async def get_batch_duplicate_clusters(
    batch_id: str,
    threshold: Annotated[float | None, Query(ge=0.5, le=1.0)] = None,
) -> dict[str, Any]:
    """
    Performs pairwise similarity clustering on questions within a batch.
    Returns grouped clusters with designated leader questions and redundant duplicate siblings.
    """
    threshold = config.DUPLICATE_HARD_THRESHOLD if threshold is None else threshold
    await _require_batch(batch_id)

    linked_questions = await get_questions(batch_id=batch_id)
    # Only evaluate active questions (ignore previously discarded questions)
    active_questions = [q for q in linked_questions if is_question_active(q.status)]
    q_dumps = [q.model_dump() for q in active_questions]

    clusters = cluster_questions(q_dumps, threshold=threshold)
    total_duplicates = sum(len(c["duplicates"]) for c in clusters)
    unique_count = len(active_questions) - total_duplicates
    archived_questions = [q for q in linked_questions if q.status == "discarded"]

    return {
        "batch_id": batch_id,
        "total_active_questions": len(active_questions),
        "unique_questions_count": unique_count,
        "duplicate_clusters_count": len(clusters),
        "total_duplicate_questions": total_duplicates,
        "archived_duplicates_count": len(archived_questions),
        "auto_resolved": len(clusters) == 0 and len(archived_questions) > 0,
        "clusters": clusters,
    }


@router.post("/batches/{batch_id}/resolve-duplicates")
async def resolve_batch_duplicates(
    batch_id: str,
    payload: ResolveDuplicatesRequest | None = None,
) -> dict[str, Any]:
    """
    Resolves duplicate clusters in a batch by preserving the designated leader question
    and archiving or deleting the redundant duplicate questions.
    """
    req_data = payload or ResolveDuplicatesRequest()
    await _require_batch(batch_id)

    linked_questions = await get_questions(batch_id=batch_id)
    active_questions = [q for q in linked_questions if is_question_active(q.status)]
    q_dumps = [q.model_dump() for q in active_questions]

    clusters = cluster_questions(q_dumps, threshold=config.DUPLICATE_HARD_THRESHOLD)
    if not clusters:
        return {
            "success": True,
            "message": "No duplicate clusters found in this batch.",
            "resolved_clusters": 0,
            "archived_count": 0,
            "remaining_active": len(active_questions),
        }

    target_clusters = clusters
    if req_data.cluster_ids:
        target_clusters = [c for c in clusters if c["cluster_id"] in req_data.cluster_ids]

    custom_leaders = set(req_data.custom_leader_ids or [])
    duplicate_ids_to_purge: list[str] = []

    for c in target_clusters:
        leader_id = c["leader_question"]["id"]
        # If user picked a custom leader from within this cluster
        member_ids = [leader_id] + [d["question"]["id"] for d in c["duplicates"]]
        picked_custom = next((cid for cid in member_ids if cid in custom_leaders), None)
        effective_leader_id = picked_custom or leader_id

        for m_id in member_ids:
            if m_id != effective_leader_id:
                duplicate_ids_to_purge.append(m_id)

    modified_count = 0
    if duplicate_ids_to_purge:
        if req_data.action == "delete":
            modified_count = await hard_delete_questions_batch(duplicate_ids_to_purge)
        else:
            # Default: Archive (mark status='discarded')
            modified_count = await batch_update_question_status(
                duplicate_ids_to_purge, status="discarded"
            )

    action_word = "deleted" if req_data.action == "delete" else "archived"
    await refresh_batch_aggregates(batch_id)
    refreshed_b = await get_batch_by_id(batch_id)
    refreshed_questions = await get_questions(batch_id=batch_id)
    remaining_active = sum(1 for q in refreshed_questions if is_question_active(q.status))

    return {
        "success": True,
        "message": f"Successfully resolved {len(target_clusters)} cluster(s). {modified_count} duplicate question(s) {action_word}.",
        "action": req_data.action,
        "resolved_clusters_count": len(target_clusters),
        "archived_count": modified_count,
        "remaining_active_questions": remaining_active,
        "target_count": refreshed_b.target_count if refreshed_b else 50,
        "deficit": (refreshed_b.target_count if refreshed_b else 50) - remaining_active,
    }


@router.post(
    "/batches/{batch_id}/refill",
    dependencies=[Depends(limit_generation_requests), Depends(limit_active_batches)],
)
async def refill_batch_questions(batch_id: str) -> dict[str, Any]:
    """
    Replenishes a batch up to its target_count by launching targeted jobs for
    archived or missing questions with diverse pedagogical thematic angles.
    """
    b = await _require_batch(batch_id)
    if is_batch_running(batch_id):
        # A second runner would double the LLM spend and replace the stoppable task handle
        raise HTTPException(status_code=409, detail="This batch is still running.")

    linked_questions = await get_questions(batch_id=batch_id)
    active_count = sum(1 for q in linked_questions if is_question_active(q.status))
    deficit = max(0, b.target_count - active_count)

    if deficit <= 0:
        return {
            "success": True,
            "message": f"Batch already has {active_count} active questions (target: {b.target_count}). No refill needed.",
            "deficit": 0,
            "active_count": active_count,
        }

    updated_batch, new_jobs = await refill_batch_deficit(batch_id, deficit)

    return {
        "success": True,
        "message": f"Launched refill generation for {deficit} replacement questions across {len(new_jobs)} job(s).",
        "deficit": deficit,
        "jobs_launched": len(new_jobs),
        "jobs": [j.model_dump() for j in new_jobs],
        "batch": updated_batch.model_dump() if updated_batch else None,
    }
