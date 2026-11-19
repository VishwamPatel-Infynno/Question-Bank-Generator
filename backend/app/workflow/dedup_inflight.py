"""Duplicate detection against the database, staged siblings and in-flight sibling drafts."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from typing import Any

from app.core.config import config
from app.schemas import ALT_TRAP_ROTATION, GenerationRequest, Question, WorkflowEvent
from app.services.deduplication import DuplicateCheckResult, evaluate_duplicate
from app.workflow.nodes import fused_generator_node
from app.workflow.review_loop import llm_budget_exhausted
from app.workflow.state import AgentWorkflowState

logger = logging.getLogger(__name__)


# Regeneration attempts after a hard duplicate is found, before the draft goes on regardless
DEDUP_REGEN_MAX_RETRIES = 1


# Pools at least this large are scored in a worker thread so the event loop (SSE, polling, other
# slots) is not blocked by pure-CPU string matching.
_DEDUP_THREAD_POOL_MIN = 150


async def _evaluate_duplicate_async(
    draft: dict[str, Any], ref_pool: list[Any], *, threshold: float, soft_threshold: float
) -> DuplicateCheckResult:
    """Asynchronously evaluates duplicate similarity against a reference pool, offloading large pools to a thread."""
    if len(ref_pool) >= _DEDUP_THREAD_POOL_MIN:
        result = await asyncio.to_thread(
            evaluate_duplicate, draft, ref_pool, threshold=threshold, soft_threshold=soft_threshold
        )
    else:
        result = evaluate_duplicate(
            draft, ref_pool, threshold=threshold, soft_threshold=soft_threshold
        )

    # Hybrid Semantic Cosine Check: catch semantic duplicates with different vocabulary
    if config.ENABLE_PGVECTOR_RAG and not result.is_duplicate:
        cand_stem = draft.get("question_stem") or ""
        cand_vec = draft.get("embedding")
        if not cand_vec and cand_stem:
            try:
                from app.services.embeddings import embed_text

                cand_vec = await embed_text(cand_stem)
                draft["embedding"] = cand_vec
            except Exception as exc:
                logger.debug("In-flight embedding generation skipped (%s)", exc)

        if cand_vec:
            from app.schemas import extract_field as _field
            from app.services.embeddings import cosine_similarity

            highest_sim = 0.0
            matched_ref = None
            semantic_threshold = min(config.RAG_SEMANTIC_DEDUP_THRESHOLD, 0.80)

            for ref in ref_pool:
                ref_id = _field(ref, "id")
                cand_id = _field(draft, "id")
                if cand_id and ref_id and str(cand_id) == str(ref_id):
                    continue

                ref_vec = (
                    ref.get("embedding")
                    if isinstance(ref, dict)
                    else getattr(ref, "embedding", None)
                )
                if not ref_vec:
                    ref_stem = (
                        ref.get("question_stem")
                        if isinstance(ref, dict)
                        else getattr(ref, "question_stem", "")
                    )
                    if ref_stem:
                        try:
                            from app.services.embeddings import embed_text

                            ref_vec = await embed_text(ref_stem)
                            if isinstance(ref, dict):
                                ref["embedding"] = ref_vec
                        except Exception:
                            pass

                if ref_vec and len(ref_vec) == len(cand_vec):
                    sim = cosine_similarity(cand_vec, ref_vec)
                    if sim > highest_sim:
                        highest_sim = sim
                        matched_ref = ref

            if highest_sim >= semantic_threshold and matched_ref is not None:
                matched_id = _field(matched_ref, "id")
                matched_stem = _field(matched_ref, "question_stem")
                matched_expl = _field(matched_ref, "explanation")
                raw_opts = (
                    matched_ref.get("options")
                    if isinstance(matched_ref, dict)
                    else getattr(matched_ref, "options", [])
                )
                formatted_opts = [
                    o
                    if isinstance(o, dict)
                    else {"id": getattr(o, "id", "A"), "text": getattr(o, "text", "")}
                    for o in (raw_opts or [])
                ]
                return DuplicateCheckResult(
                    is_duplicate=True,
                    is_soft_warning=False,
                    similarity_score=highest_sim,
                    matched_question_id=str(matched_id) if matched_id else None,
                    matched_question_stem=matched_stem,
                    matched_options=formatted_opts,
                    matched_explanation=matched_expl,
                    match_reason=(
                        f"pgvector Semantic In-Flight Sibling Collision ({int(highest_sim * 100)}% cosine match): "
                        f"tests identical cognitive concept"
                    ),
                )
            if (
                highest_sim >= config.DUPLICATE_SOFT_THRESHOLD
                and matched_ref is not None
                and not result.is_soft_warning
            ):
                result.is_soft_warning = True
                result.similarity_score = max(result.similarity_score, highest_sim)
                result.match_reason = (
                    f"pgvector Semantic Sibling Proximity ({int(highest_sim * 100)}% cosine match)"
                )

    return result


_IN_FLIGHT_BATCH_STEMS: dict[str, list[dict[str, Any]]] = {}


_IN_FLIGHT_LOCK = asyncio.Lock()


def _slot(job_id: str | None, worker_idx: int) -> tuple[str | None, int]:
    """One question slot: the job it belongs to and its worker index within that job."""
    return (job_id, worker_idx)


async def register_in_flight_draft(
    batch_id: str | None,
    draft: dict[str, Any],
    worker_idx: int,
    job_id: str | None = None,
    passage_id: str | None = None,
    stimulus_text: str | None = None,
) -> None:
    """Registers a freshly drafted stem in the batch pool so concurrent siblings (same job or
    another job of the batch) can detect it before it is persisted."""
    if not batch_id:
        return
    slot = _slot(job_id, worker_idx)
    async with _IN_FLIGHT_LOCK:
        pool = _IN_FLIGHT_BATCH_STEMS.setdefault(batch_id, [])
        pool[:] = [item for item in pool if item.get("_slot") != slot]
        item = dict(draft)
        item["_slot"] = slot
        # Synthetic id so a collision with an in-flight sibling is recognisable as such.
        item["id"] = f"in_flight_{job_id or 'live'}_{worker_idx}"
        if passage_id or draft.get("passage_id"):
            item["passage_id"] = draft.get("passage_id") or passage_id
        if stimulus_text or draft.get("stimulus_text"):
            item["stimulus_text"] = draft.get("stimulus_text") or stimulus_text
        if batch_id or draft.get("batch_id"):
            item["batch_id"] = draft.get("batch_id") or batch_id
        if draft.get("embedding"):
            item["embedding"] = draft["embedding"]
        elif config.ENABLE_PGVECTOR_RAG:
            stem = draft.get("question_stem") or ""
            if stem:
                try:
                    from app.services.embeddings import embed_text

                    vec = await embed_text(stem)
                    item["embedding"] = vec
                    draft["embedding"] = vec
                except Exception as exc:
                    logger.debug("In-flight draft embedding generation skipped (%s)", exc)
        pool.append(item)


async def get_in_flight_drafts(
    batch_id: str | None, current_worker_idx: int, job_id: str | None = None
) -> list[dict[str, Any]]:
    """Every in-flight draft of the batch except the asking slot's own."""
    if not batch_id:
        return []
    slot = _slot(job_id, current_worker_idx)
    async with _IN_FLIGHT_LOCK:
        pool = _IN_FLIGHT_BATCH_STEMS.get(batch_id, [])
        return [item for item in pool if item.get("_slot") != slot]


async def remove_in_flight_draft(
    batch_id: str | None, worker_idx: int, job_id: str | None = None
) -> None:
    """Removes one slot's draft from the pool when it is finalized or cancelled."""
    if not batch_id:
        return
    slot = _slot(job_id, worker_idx)
    async with _IN_FLIGHT_LOCK:
        pool = _IN_FLIGHT_BATCH_STEMS.get(batch_id, [])
        pool[:] = [item for item in pool if item.get("_slot") != slot]
        if not pool:
            _IN_FLIGHT_BATCH_STEMS.pop(batch_id, None)


async def clear_in_flight_batch(batch_id: str | None, job_id: str | None = None) -> None:
    """Forgets a job's in-flight drafts at the end of its run (every job's, when job_id is None).

    Jobs of one batch run concurrently, so a finishing job must not wipe its siblings' entries.
    """
    if not batch_id:
        return
    async with _IN_FLIGHT_LOCK:
        if job_id is None:
            _IN_FLIGHT_BATCH_STEMS.pop(batch_id, None)
            return
        pool = _IN_FLIGHT_BATCH_STEMS.get(batch_id, [])
        pool[:] = [item for item in pool if item.get("_slot", (None,))[0] != job_id]
        if not pool:
            _IN_FLIGHT_BATCH_STEMS.pop(batch_id, None)


async def _refresh_duplicate_info_after_review(
    state: AgentWorkflowState,
    idx: int,
    req: GenerationRequest,
    db_reference_pool: list[Question],
    outcomes_questions: list[dict[str, Any] | None],
    threshold: float | None = None,
    soft_threshold: float | None = None,
    batch_key: str | None = None,
    job_id: str | None = None,
) -> None:
    """Re-checks duplicates for a draft that the review loop rewrote.

    The first dedup pass ran on the original draft; regeneration can change the stem, so the
    stored duplicate verdict would otherwise describe a question that no longer exists.
    """
    threshold = config.DUPLICATE_HARD_THRESHOLD if threshold is None else threshold
    soft_threshold = config.DUPLICATE_SOFT_THRESHOLD if soft_threshold is None else soft_threshold
    if state.get("iteration_count", 1) <= 1:
        return
    cur_draft = state.get("current_draft") or {}
    passage_id = req.passage_id or (
        state.get("request", {}).get("passage_id")
        if isinstance(state.get("request"), dict)
        else None
    )
    stimulus_text = req.shared_stimulus or (
        state.get("request", {}).get("shared_stimulus")
        if isinstance(state.get("request"), dict)
        else None
    )
    if passage_id and not cur_draft.get("passage_id"):
        cur_draft["passage_id"] = passage_id
    if stimulus_text and not cur_draft.get("stimulus_text"):
        cur_draft["stimulus_text"] = stimulus_text
    if batch_key and not cur_draft.get("batch_id"):
        cur_draft["batch_id"] = batch_key

    batch_key = batch_key or req.batch_id or req.run_id
    await register_in_flight_draft(
        batch_key,
        cur_draft,
        idx,
        job_id=job_id,
        passage_id=passage_id,
        stimulus_text=stimulus_text,
    )
    in_flight = await get_in_flight_drafts(batch_key, idx, job_id=job_id)
    ref_pool = (
        list(db_reference_pool) + [q for q in outcomes_questions if q is not None] + in_flight
    )
    result = await _evaluate_duplicate_async(
        cur_draft, ref_pool, threshold=threshold, soft_threshold=soft_threshold
    )
    state["duplicate_info"] = result.model_dump()
    state.setdefault("stage_outcomes", {})["duplicate_check"] = result.model_dump()


async def _run_deduplication_anti_collision_loop(
    state: AgentWorkflowState,
    idx: int,
    total_qty: int,
    item_run_id: str,
    req: GenerationRequest,
    db_reference_pool: list[Question],
    outcomes_questions: list[dict[str, Any] | None],
    event_queue: asyncio.Queue[WorkflowEvent | None],
    make_event: Callable[..., WorkflowEvent],
    max_retries: int = DEDUP_REGEN_MAX_RETRIES,
    threshold: float | None = None,
    soft_threshold: float | None = None,
    batch_key: str | None = None,
    job_id: str | None = None,
) -> None:
    """
    Evaluates candidate draft against database reference pool, sibling batch questions,
    and active in-flight drafted stems. Uses a two-tier threshold:
    - If similarity >= 0.75 (Hard Duplicate): automatically re-prompts the fused generator with
      anti-collision instructions and alternate trap re-seeding up to max_retries.
    - If 0.60 <= similarity < 0.75 (Soft Warning): emits a variety warning and logs collision rationale.
    """
    threshold = config.DUPLICATE_HARD_THRESHOLD if threshold is None else threshold
    soft_threshold = config.DUPLICATE_SOFT_THRESHOLD if soft_threshold is None else soft_threshold
    cur_draft = state.get("current_draft") or {}
    passage_id = req.passage_id or (
        state.get("request", {}).get("passage_id")
        if isinstance(state.get("request"), dict)
        else None
    )
    stimulus_text = req.shared_stimulus or (
        state.get("request", {}).get("shared_stimulus")
        if isinstance(state.get("request"), dict)
        else None
    )
    if passage_id and not cur_draft.get("passage_id"):
        cur_draft["passage_id"] = passage_id
    if stimulus_text and not cur_draft.get("stimulus_text"):
        cur_draft["stimulus_text"] = stimulus_text
    if batch_key and not cur_draft.get("batch_id"):
        cur_draft["batch_id"] = batch_key

    # Must match the key the engine uses to remove drafts, or every run leaks its registry entry.
    batch_key = batch_key or req.batch_id or req.run_id

    # Immediately register candidate draft so concurrent siblings detect this stem in flight
    await register_in_flight_draft(
        batch_key,
        cur_draft,
        idx,
        job_id=job_id,
        passage_id=passage_id,
        stimulus_text=stimulus_text,
    )

    in_flight = await get_in_flight_drafts(batch_key, idx, job_id=job_id)
    active_siblings = [q for q in outcomes_questions if q is not None]
    ref_pool = list(db_reference_pool) + active_siblings + in_flight

    dup_result = await _evaluate_duplicate_async(
        cur_draft, ref_pool, threshold=threshold, soft_threshold=soft_threshold
    )

    dedup_retry = 0
    while dup_result.is_duplicate and dedup_retry < max_retries and not llm_budget_exhausted(state):
        dedup_retry += 1
        alt_trap = ALT_TRAP_ROTATION[(idx + dedup_retry) % len(ALT_TRAP_ROTATION)]
        logger.warning(
            "Worker %s generated duplicate question (%s%% match). Triggering anti-collision regeneration with trap '%s' (attempt %s/%s)...",
            idx + 1,
            int(dup_result.similarity_score * 100),
            alt_trap,
            dedup_retry,
            max_retries,
        )
        dup_evt = make_event(
            event_type="agent_action",
            agent_name="Question Writer & Reviewer",
            message=f"Duplicate question detected ({int(dup_result.similarity_score * 100)}% match with {dup_result.matched_question_id or 'existing'}). Regenerating with alternate trap '{alt_trap}'...",
            data={
                "index": idx + 1,
                "total": total_qty,
                "stage": "anti_collision_regeneration",
                "similarity_score": dup_result.similarity_score,
                "matched_question_stem": dup_result.matched_question_stem,
                "reason": dup_result.match_reason,
                "assigned_trap": alt_trap,
            },
            run_id=item_run_id,
        )
        await event_queue.put(dup_evt)

        if req.shared_stimulus:
            collision_hint = (
                f"CRITICAL ANTI-COLLISION REQUIREMENT: Your previous draft had high similarity ({int(dup_result.similarity_score * 100)}%) "
                f"with existing question: '{dup_result.matched_question_stem}'. "
                f"Reason: {dup_result.match_reason or 'Conceptual collision'}. "
                f"You MUST NOT write a question testing this same claim, paragraph, or answer rationale. "
                f"Formulate a completely distinct question testing a different aspect of the passage with cognitive trap {alt_trap}."
            )
        else:
            collision_hint = (
                f"CRITICAL ANTI-COLLISION REQUIREMENT: Your previous draft had high similarity ({int(dup_result.similarity_score * 100)}%) "
                f"with existing question: '{dup_result.matched_question_stem}'. "
                f"Reason: {dup_result.match_reason or 'Conceptual collision'}. "
                f"You MUST NOT write a question testing this same calculation or scenario. "
                f"Formulate a completely distinct scientific scenario testing cognitive trap {alt_trap} for {req.subtopic or 'this topic'}."
            )
        state["diversity_context"] = (
            f"{state.get('diversity_context') or ''} {collision_hint}".strip()
        )
        if "request" in state and isinstance(state["request"], dict):
            curr_angle = state["request"].get("thematic_angle") or ""
            matched_stem_snip = (dup_result.matched_question_stem or "")[:60]
            anti_collision_directive = (
                f"(Anti-Collision Regeneration Attempt {dedup_retry}, Alternate Trap {alt_trap}: "
                f"You MUST formulate a completely distinct question testing a separate paragraph, claim, "
                f"or variable than collided sibling '{matched_stem_snip}...')"
            )
            state["request"]["thematic_angle"] = (
                f"{curr_angle} • {anti_collision_directive}"
                if curr_angle
                else anti_collision_directive
            )
            state["request"]["primary_trap"] = alt_trap

        regen_res = await fused_generator_node(state)
        state.update(regen_res)
        cur_draft = state.get("current_draft") or {}
        if passage_id and not cur_draft.get("passage_id"):
            cur_draft["passage_id"] = passage_id
        if stimulus_text and not cur_draft.get("stimulus_text"):
            cur_draft["stimulus_text"] = stimulus_text
        if batch_key and not cur_draft.get("batch_id"):
            cur_draft["batch_id"] = batch_key

        # Update in-flight registration with new draft
        await register_in_flight_draft(
            batch_key,
            cur_draft,
            idx,
            job_id=job_id,
            passage_id=passage_id,
            stimulus_text=stimulus_text,
        )
        in_flight = await get_in_flight_drafts(batch_key, idx, job_id=job_id)
        ref_pool = list(db_reference_pool) + active_siblings + in_flight
        dup_result = await _evaluate_duplicate_async(
            cur_draft, ref_pool, threshold=threshold, soft_threshold=soft_threshold
        )

    if dup_result.is_soft_warning and not dup_result.is_duplicate:
        soft_evt = make_event(
            event_type="agent_action",
            agent_name="Question Writer & Reviewer",
            message=f"Soft conceptual overlap detected ({int(dup_result.similarity_score * 100)}% match with '{dup_result.matched_question_stem}'). Retaining as valid variation.",
            data={
                "index": idx + 1,
                "total": total_qty,
                "stage": "soft_collision_warning",
                "similarity_score": dup_result.similarity_score,
                "matched_question_stem": dup_result.matched_question_stem,
                "reason": dup_result.match_reason,
            },
            run_id=item_run_id,
        )
        await event_queue.put(soft_evt)

    state["duplicate_info"] = dup_result.model_dump()
    stage_outcomes = state.setdefault("stage_outcomes", {})
    stage_outcomes["duplicate_check"] = dup_result.model_dump()
