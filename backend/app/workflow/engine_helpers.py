"""
engine_helpers.py - Compatibility hub for the workflow engine's helper modules.

The helpers now live in one module per concern; this module re-exports them so existing
imports keep working:

- ``review_loop``      quality review, blind-solver validation and remediation of one draft
- ``passage_prep``     per-item requests, diagram requirement, shared passage and visual drafting
- ``live_job_store``   question and job/batch persistence for standalone live runs
- ``dedup_inflight``   duplicate detection against the DB, staged siblings and in-flight drafts
"""

from app.workflow.dedup_inflight import (
    _DEDUP_THREAD_POOL_MIN,
    _IN_FLIGHT_BATCH_STEMS,
    _IN_FLIGHT_LOCK,
    DEDUP_REGEN_MAX_RETRIES,
    _evaluate_duplicate_async,
    _refresh_duplicate_info_after_review,
    _run_deduplication_anti_collision_loop,
    clear_in_flight_batch,
    get_in_flight_drafts,
    register_in_flight_draft,
    remove_in_flight_draft,
)
from app.workflow.live_job_store import (
    _finalize_live_job_progress,
    _handle_live_job_cancellation,
    _handle_live_job_failure,
    _persist_live_question,
)
from app.workflow.passage_prep import (
    SharedPassageState,
    _build_batch_worker_request,
    _determine_item_diagram_requirement,
    _prepare_shared_passage_and_visual,
)
from app.workflow.review_loop import (
    _apply_deterministic_gate,
    _duplicate_blockers,
    _emit_rejection,
    _regenerate,
    _regenerate_with_events,
    _run_question_review_loop,
    _validator_review,
    count_llm_calls,
    llm_budget_exhausted,
)

__all__ = [
    "DEDUP_REGEN_MAX_RETRIES",
    "_DEDUP_THREAD_POOL_MIN",
    "_IN_FLIGHT_BATCH_STEMS",
    "_IN_FLIGHT_LOCK",
    "SharedPassageState",
    "_apply_deterministic_gate",
    "_build_batch_worker_request",
    "_determine_item_diagram_requirement",
    "_duplicate_blockers",
    "_emit_rejection",
    "_evaluate_duplicate_async",
    "_finalize_live_job_progress",
    "_handle_live_job_cancellation",
    "_handle_live_job_failure",
    "_persist_live_question",
    "_prepare_shared_passage_and_visual",
    "_refresh_duplicate_info_after_review",
    "_regenerate",
    "_regenerate_with_events",
    "_run_deduplication_anti_collision_loop",
    "_run_question_review_loop",
    "_validator_review",
    "clear_in_flight_batch",
    "count_llm_calls",
    "get_in_flight_drafts",
    "llm_budget_exhausted",
    "register_in_flight_draft",
    "remove_in_flight_draft",
]
