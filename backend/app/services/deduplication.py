"""
deduplication.py - Multi-metric question similarity and collision detection engine.

Evaluates lexical token overlap (Jaccard, n-grams, character edit distance) and
concept overlap between candidate MCAT questions and existing items in the Question Bank
or active batch siblings to prevent repetitive questions.
"""

from __future__ import annotations

import logging
from typing import Any

from app.core.config import config
from app.schemas import extract_field as _field
from app.services.dedup_clustering import cluster_questions
from app.services.dedup_metrics import (
    _MAX_STEM_CACHE_SIZE,
    _STEM_TOKEN_CACHE,
    STOP_WORDS,
    DuplicateCheckResult,
    DuplicateCluster,
    DuplicateMember,
    compute_options_overlap,
    compute_question_similarity,
    compute_sequence_ratio,
    compute_stem_similarity,
    extract_content_tokens,
    extract_normalized_stem_set,
    get_or_create_stem_tokens,
    normalize_text,
    normalize_token_stem,
)

logger = logging.getLogger(__name__)

__all__ = [
    "STOP_WORDS",
    "_MAX_STEM_CACHE_SIZE",
    "_STEM_TOKEN_CACHE",
    "DuplicateCheckResult",
    "DuplicateCluster",
    "DuplicateMember",
    "cluster_questions",
    "compute_options_overlap",
    "compute_question_similarity",
    "compute_sequence_ratio",
    "compute_stem_similarity",
    "evaluate_duplicate",
    "evaluate_duplicate_rag",
    "extract_content_tokens",
    "extract_normalized_stem_set",
    "get_or_create_stem_tokens",
    "judge_semantic_duplicate",
    "normalize_text",
    "normalize_token_stem",
]


def evaluate_duplicate(
    candidate: dict[str, Any] | Any,
    reference_pool: list[dict[str, Any] | Any],
    threshold: float | None = None,
    soft_threshold: float | None = None,
) -> DuplicateCheckResult:
    """
    Evaluates a candidate question against a pool of reference questions (from DB or batch siblings).
    Returns DuplicateCheckResult with details of the highest similarity match.
    Uses two-tier thresholding:
    - is_duplicate: True if similarity >= threshold (default 0.75)
    - is_soft_warning: True if soft_threshold <= similarity < threshold (default 0.60)
    """
    threshold = config.DUPLICATE_HARD_THRESHOLD if threshold is None else threshold
    soft_threshold = config.DUPLICATE_SOFT_THRESHOLD if soft_threshold is None else soft_threshold
    candidate_id = _field(candidate, "id")
    cand_stem = (
        candidate.get("question_stem")
        if isinstance(candidate, dict)
        else getattr(candidate, "question_stem", "")
    )
    if cand_stem:
        get_or_create_stem_tokens(cand_stem)

    highest_score = 0.0
    matched_ref: dict[str, Any] | Any | None = None
    best_reason = ""

    for ref in reference_pool:
        ref_id = _field(ref, "id")
        # Skip self-comparison
        if candidate_id and ref_id and str(candidate_id) == str(ref_id):
            continue

        score, reason = compute_question_similarity(candidate, ref, prune=True)
        if score > highest_score:
            highest_score = score
            matched_ref = ref
            best_reason = reason

    is_duplicate = highest_score >= threshold
    is_soft = (highest_score >= soft_threshold) and not is_duplicate

    if matched_ref is not None:
        matched_id = (
            matched_ref.get("id")
            if isinstance(matched_ref, dict)
            else getattr(matched_ref, "id", None)
        )
        matched_stem = (
            matched_ref.get("question_stem")
            if isinstance(matched_ref, dict)
            else getattr(matched_ref, "question_stem", None)
        )
        matched_expl = (
            matched_ref.get("explanation")
            if isinstance(matched_ref, dict)
            else getattr(matched_ref, "explanation", None)
        )
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
            is_duplicate=is_duplicate,
            is_soft_warning=is_soft,
            similarity_score=highest_score,
            matched_question_id=str(matched_id) if matched_id else None,
            matched_question_stem=matched_stem,
            matched_options=formatted_opts,
            matched_explanation=matched_expl,
            match_reason=best_reason if (is_duplicate or is_soft) else None,
        )

    return DuplicateCheckResult(
        is_duplicate=False,
        is_soft_warning=False,
        similarity_score=0.0,
    )


async def evaluate_duplicate_rag(
    candidate: dict[str, Any] | Any,
    reference_pool: list[dict[str, Any] | Any] | None = None,
    threshold: float | None = None,
    soft_threshold: float | None = None,
) -> DuplicateCheckResult:
    """
    Evaluates a candidate question using hybrid pgvector semantic search AND in-memory reference pool.
    1. First checks pgvector for existing semantic neighbors in the Question Bank.
    2. Then evaluates against in-flight sibling references.
    3. Combines both to return the highest similarity match with vector + lexical explanations.
    """
    threshold = config.DUPLICATE_HARD_THRESHOLD if threshold is None else threshold
    soft_threshold = config.DUPLICATE_SOFT_THRESHOLD if soft_threshold is None else soft_threshold
    ref_pool = list(reference_pool or [])

    # If pgvector is enabled, retrieve top semantic neighbors from the database
    if config.ENABLE_PGVECTOR_RAG:
        try:
            from app.services.rag import find_similar_questions

            cand_stem = _field(candidate, "question_stem") or ""
            cand_id = _field(candidate, "id")
            if cand_stem:
                db_matches = await find_similar_questions(
                    cand_stem,
                    limit=5,
                    min_similarity=soft_threshold,
                    exclude_ids=[str(cand_id)] if cand_id else None,
                )
                ref_pool.extend(
                    {
                        "id": m.id,
                        "question_stem": m.question_stem,
                        "explanation": m.explanation,
                        "options": [],
                        "_vector_similarity": m.similarity,
                    }
                    for m in db_matches
                )
        except Exception as exc:
            logger.debug("pgvector neighbor retrieval for dedup skipped (%s).", exc)

    return evaluate_duplicate(
        candidate, ref_pool, threshold=threshold, soft_threshold=soft_threshold
    )


async def judge_semantic_duplicate(
    cand: dict[str, Any] | Any,
    ref: dict[str, Any] | Any,
) -> tuple[bool, float, str]:
    """
    Evaluates whether candidate and reference questions are semantic duplicates.
    For borderline lexical matches (0.60 <= score < 0.75), leverages LLM disambiguation
    in live mode, with fast deterministic score evaluation in offline mode.
    """
    score, reason = compute_question_similarity(cand, ref)

    # Fast vector cosine similarity check if embeddings are present
    cand_vec = cand.get("embedding") if isinstance(cand, dict) else getattr(cand, "embedding", None)
    ref_vec = ref.get("embedding") if isinstance(ref, dict) else getattr(ref, "embedding", None)
    if cand_vec and ref_vec and len(cand_vec) == len(ref_vec):
        from app.services.embeddings import cosine_similarity

        v_sim = cosine_similarity(cand_vec, ref_vec)
        if v_sim >= config.RAG_SEMANTIC_DEDUP_THRESHOLD:
            return (
                True,
                v_sim,
                f"pgvector Semantic Duplicate ({int(v_sim * 100)}% cosine similarity): tests identical cognitive concept",
            )
    if score >= config.DUPLICATE_HARD_THRESHOLD:
        return True, score, f"Deterministic duplicate ({int(score * 100)}%): {reason}"
    if score < config.DUPLICATE_SOFT_THRESHOLD:
        return False, score, f"Distinct ({int(score * 100)}%): {reason}"

    # Borderline zone: 0.60 <= score < 0.75
    if config.OFFLINE_MODE:
        is_dup = score >= 0.70
        return is_dup, score, f"Borderline offline evaluation ({int(score * 100)}%): {reason}"

    cand_stem = _field(cand, "question_stem") or ""
    ref_stem = _field(ref, "question_stem") or ""
    cand_expl = _field(cand, "explanation") or ""
    ref_expl = _field(ref, "explanation") or ""

    system_prompt = (
        "You are an expert MCAT psychometrician judging whether two candidate questions "
        "test the exact same concept (duplicate) or distinct concepts. Return ONLY a JSON object."
    )
    user_prompt = (
        f"Question A:\nStem: {cand_stem}\nExplanation: {cand_expl}\n\n"
        f"Question B:\nStem: {ref_stem}\nExplanation: {ref_expl}\n\n"
        "Do these two questions test the exact same scientific principle or pedagogical relationship? "
        'Return JSON: {"is_duplicate": bool, "confidence": float, "reason": string}'
    )

    try:
        from app.agents.base import call_llm, safe_json_loads

        raw, _ = await call_llm(
            prompt=user_prompt,
            system_prompt=system_prompt,
            model=config.DEFAULT_TEXT_MODEL,
            temperature=0.1,
            max_tokens=600,
        )
        data = safe_json_loads(raw)
        if isinstance(data, dict) and "is_duplicate" in data:
            is_dup = bool(data["is_duplicate"])
            adj_score = max(score, 0.85) if is_dup else min(score, 0.55)
            return is_dup, adj_score, f"AI Semantic Verdict: {data.get('reason', reason)}"
    except Exception as exc:
        logger.warning("Semantic duplicate judgment failed (%s); using score.", exc)

    return score >= 0.70, score, reason
