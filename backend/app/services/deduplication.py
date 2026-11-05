"""
deduplication.py - Multi-metric question similarity and collision detection engine.

Evaluates lexical token overlap (Jaccard, n-grams, character edit distance) and
concept overlap between candidate MCAT questions and existing items in the Question Bank
or active batch siblings to prevent repetitive questions.
"""

from __future__ import annotations

import difflib
import logging
import re
from collections import OrderedDict
from typing import Any

from pydantic import BaseModel

logger = logging.getLogger(__name__)

# Common English stop words to exclude during token normalization
STOP_WORDS = frozenset(
    {
        "a",
        "an",
        "the",
        "and",
        "or",
        "but",
        "in",
        "on",
        "at",
        "to",
        "for",
        "of",
        "with",
        "by",
        "from",
        "up",
        "about",
        "into",
        "over",
        "after",
        "is",
        "are",
        "was",
        "were",
        "be",
        "been",
        "being",
        "have",
        "has",
        "had",
        "do",
        "does",
        "did",
        "shall",
        "will",
        "should",
        "would",
        "may",
        "might",
        "must",
        "can",
        "could",
        "which",
        "what",
        "who",
        "whom",
        "this",
        "that",
        "these",
        "those",
        "it",
        "its",
        "as",
        "if",
        "than",
        "then",
        "so",
    }
)


class DuplicateCheckResult(BaseModel):
    """Encapsulates the evaluation outcome of duplicate collision checks."""

    is_duplicate: bool = False
    is_soft_warning: bool = False
    similarity_score: float = 0.0
    matched_question_id: str | None = None
    matched_question_stem: str | None = None
    matched_options: list[dict[str, Any]] | None = None
    matched_explanation: str | None = None
    match_reason: str | None = None


def normalize_text(text: str | None) -> str:
    """
    Normalizes text for linguistic comparison:
    - Strips LaTeX delimiters and HTML/XML tags
    - Replaces punctuation and special symbols with spaces
    - Lowercases and collapses multiple whitespace characters
    """
    if not text:
        return ""
    # Strip HTML tags
    clean = re.sub(r"<[^>]+>", " ", text)
    # Strip LaTeX delimiters: $, $$, \(, \), \[, \]
    clean = re.sub(r"(\$\$?|\\\(|\\\)|\\\[|\\\])", " ", clean)
    # Remove LaTeX commands like \frac, \text, \times, etc.
    clean = re.sub(r"\\[a-zA-Z]+", " ", clean)
    # Replace non-alphanumeric characters with spaces (preserve digits and letters)
    clean = re.sub(r"[^a-zA-Z0-9\s]", " ", clean)
    # Lowercase and normalize whitespace
    tokens = clean.lower().split()
    return " ".join(tokens)


def extract_content_tokens(text: str | None) -> list[str]:
    """Returns filtered content tokens with stop words removed."""
    normalized = normalize_text(text)
    if not normalized:
        return []
    return [t for t in normalized.split() if t not in STOP_WORDS and len(t) > 1]


# In-memory LRU token cache keyed by the normalized stem text itself. Keying by question id (as
# before) served stale tokens after an edit and never cached the candidate; the text is the
# truth, so equal stems share one entry whoever owns them.
_StemTokens = tuple[str, list[str], set[str], set[tuple[str, str]]]
_STEM_TOKEN_CACHE: OrderedDict[str, _StemTokens] = OrderedDict()
_MAX_STEM_CACHE_SIZE = 2000


def get_or_create_stem_tokens(stem: str | None, ref_id: str | None = None) -> _StemTokens:
    """
    Returns normalized text, filtered tokens list, tokens set, and bigrams set for a stem.

    ``ref_id`` is accepted for backward compatibility and ignored: entries are keyed by content.
    Least-recently-used entries are evicted one at a time instead of flushing the whole cache.
    """
    norm = normalize_text(stem)
    cached = _STEM_TOKEN_CACHE.get(norm)
    if cached is not None:
        _STEM_TOKEN_CACHE.move_to_end(norm)
        return cached

    tokens = [t for t in norm.split() if t not in STOP_WORDS and len(t) > 1] if norm else []
    token_set = set(tokens)
    bigrams = (
        {tuple(tokens[i : i + 2]) for i in range(len(tokens) - 1)} if len(tokens) >= 2 else set()
    )
    item: _StemTokens = (norm, tokens, token_set, bigrams)

    _STEM_TOKEN_CACHE[norm] = item
    while len(_STEM_TOKEN_CACHE) > _MAX_STEM_CACHE_SIZE:
        _STEM_TOKEN_CACHE.popitem(last=False)
    return item


def compute_sequence_ratio(text1: str, text2: str) -> float:
    """Calculates string gestalt pattern matching ratio via difflib.SequenceMatcher."""
    n1 = normalize_text(text1)
    n2 = normalize_text(text2)
    if not n1 or not n2:
        return 0.0
    if n1 == n2:
        return 1.0
    matcher = difflib.SequenceMatcher(None, n1, n2)
    return round(matcher.ratio(), 4)


def compute_stem_similarity(stem1: str, stem2: str, ref_id: str | None = None) -> float:
    """
    Hybrid stem similarity combining token containment, 1-gram Jaccard, 2-gram Jaccard,
    and character sequence ratio.
    """
    norm1, tokens1, s1, b1 = get_or_create_stem_tokens(stem1)
    norm2, tokens2, s2, b2 = get_or_create_stem_tokens(stem2, ref_id)
    if not tokens1 or not tokens2:
        return 0.0

    min_len = min(len(s1), len(s2))
    containment = len(s1 & s2) / min_len if min_len > 0 else 0.0

    u1 = len(s1 | s2)
    jaccard_1 = len(s1 & s2) / u1 if u1 > 0 else 0.0

    u2 = len(b1 | b2)
    jaccard_2 = len(b1 & b2) / u2 if u2 > 0 else 0.0

    seq_ratio = difflib.SequenceMatcher(None, norm1, norm2).ratio() if norm1 and norm2 else 0.0

    # Weighted blend: 35% containment, 25% 1-gram Jaccard, 20% 2-gram Jaccard, 20% SequenceMatcher
    score = (0.35 * containment) + (0.25 * jaccard_1) + (0.20 * jaccard_2) + (0.20 * seq_ratio)
    return round(score, 4)


def compute_options_overlap(
    opts1: list[dict[str, Any] | Any],
    opts2: list[dict[str, Any] | Any],
) -> float:
    """
    Computes overlap between answer options based on normalized text matching with fast checks.
    """
    texts1 = [
        normalize_text(o.get("text", "") if isinstance(o, dict) else getattr(o, "text", str(o)))
        for o in (opts1 or [])
    ]
    texts2 = [
        normalize_text(o.get("text", "") if isinstance(o, dict) else getattr(o, "text", str(o)))
        for o in (opts2 or [])
    ]
    texts1 = [t for t in texts1 if t]
    texts2 = [t for t in texts2 if t]

    if not texts1 or not texts2:
        return 0.0

    matches = 0
    for t1 in texts1:
        # Check if t1 has high similarity with any option in texts2
        for t2 in texts2:
            # Fast check: exact text match
            if t1 == t2:
                matches += 1
                break
            # Length ratio heuristic before SequenceMatcher: if ratio < 0.6, sequence ratio cannot exceed 0.85
            l1, l2 = len(t1), len(t2)
            if max(l1, l2) > 0 and (min(l1, l2) / max(l1, l2)) < 0.60:
                continue
            if compute_sequence_ratio(t1, t2) > 0.85:
                matches += 1
                break

    return round(matches / max(len(texts1), len(texts2)), 4)


def compute_question_similarity(
    candidate: dict[str, Any] | Any,
    reference: dict[str, Any] | Any,
) -> tuple[float, str]:
    """
    Computes comprehensive similarity between two questions.
    Returns (similarity_score, reason).
    """
    stem1 = (
        candidate.get("question_stem")
        if isinstance(candidate, dict)
        else getattr(candidate, "question_stem", "")
    )
    stem2 = (
        reference.get("question_stem")
        if isinstance(reference, dict)
        else getattr(reference, "question_stem", "")
    )
    ref_id = reference.get("id") if isinstance(reference, dict) else getattr(reference, "id", None)

    stem_sim = compute_stem_similarity(stem1, stem2, ref_id=str(ref_id) if ref_id else None)

    # Early-exit prune: if stem similarity is below 0.40, composite similarity can NEVER reach 0.80
    if stem_sim < 0.40:
        overall = round(0.70 * stem_sim, 4)
        return overall, f"Distinct question stem ({int(stem_sim * 100)}%)"

    opts1 = (
        candidate.get("options")
        if isinstance(candidate, dict)
        else getattr(candidate, "options", [])
    )
    opts2 = (
        reference.get("options")
        if isinstance(reference, dict)
        else getattr(reference, "options", [])
    )

    opts_sim = compute_options_overlap(opts1, opts2)

    # If stems are nearly identical (>0.80), that alone drives the collision
    if stem_sim >= 0.80:
        overall = stem_sim
        reason = f"High question stem textual overlap ({int(stem_sim * 100)}%)"
    # If options are identical or near-identical (>= 0.75) and stem has moderate-to-high overlap
    elif opts_sim >= 0.75 and stem_sim >= 0.50:
        overall = round((0.50 * stem_sim) + (0.50 * opts_sim), 4)
        reason = f"Identical answer choices ({int(opts_sim * 100)}%) and conceptual stem match ({int(stem_sim * 100)}%)"
    # If both stem and options have substantial overlap
    elif stem_sim >= 0.60 and opts_sim >= 0.50:
        overall = round((0.60 * stem_sim) + (0.40 * opts_sim), 4)
        reason = f"Question stem ({int(stem_sim * 100)}%) and answer choice ({int(opts_sim * 100)}%) collision"
    else:
        overall = round((0.70 * stem_sim) + (0.30 * opts_sim), 4)
        reason = f"Overall conceptual similarity ({int(overall * 100)}%)"

    return overall, reason


def evaluate_duplicate(
    candidate: dict[str, Any] | Any,
    reference_pool: list[dict[str, Any] | Any],
    threshold: float = 0.75,
    soft_threshold: float = 0.60,
) -> DuplicateCheckResult:
    """
    Evaluates a candidate question against a pool of reference questions (from DB or batch siblings).
    Returns DuplicateCheckResult with details of the highest similarity match.
    Uses two-tier thresholding:
    - is_duplicate: True if similarity >= threshold (default 0.75)
    - is_soft_warning: True if soft_threshold <= similarity < threshold (default 0.60)
    """
    candidate_id = (
        candidate.get("id") if isinstance(candidate, dict) else getattr(candidate, "id", None)
    )
    cand_stem = (
        candidate.get("question_stem")
        if isinstance(candidate, dict)
        else getattr(candidate, "question_stem", "")
    )
    if cand_stem:
        get_or_create_stem_tokens(cand_stem, str(candidate_id) if candidate_id else None)

    highest_score = 0.0
    matched_ref: dict[str, Any] | Any | None = None
    best_reason = ""

    for ref in reference_pool:
        ref_id = ref.get("id") if isinstance(ref, dict) else getattr(ref, "id", None)
        # Skip self-comparison
        if candidate_id and ref_id and str(candidate_id) == str(ref_id):
            continue

        score, reason = compute_question_similarity(candidate, ref)
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

        # Format options as dicts for serialization
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


def cluster_questions(
    questions: list[dict[str, Any] | Any],
    threshold: float = 0.75,
) -> list[dict[str, Any]]:
    """
    Groups questions into duplicate clusters using graph connected components.
    For each cluster with >= 2 items, identifies the leader question (highest final_score)
    and list of redundant sibling duplicates with similarity metrics.
    """
    n = len(questions)
    if n < 2:
        return []

    parent = list(range(n))

    def find(i: int) -> int:
        path = []
        curr = i
        while parent[curr] != curr:
            path.append(curr)
            curr = parent[curr]
        for node in path:
            parent[node] = curr
        return curr

    def union(i: int, j: int) -> None:
        root_i = find(i)
        root_j = find(j)
        if root_i != root_j:
            parent[root_i] = root_j

    pairwise_sims: dict[tuple[int, int], tuple[float, str]] = {}

    for i in range(n):
        for j in range(i + 1, n):
            score, reason = compute_question_similarity(questions[i], questions[j])
            stem_sim = compute_stem_similarity(
                questions[i].get("question_stem")
                if isinstance(questions[i], dict)
                else getattr(questions[i], "question_stem", ""),
                questions[j].get("question_stem")
                if isinstance(questions[j], dict)
                else getattr(questions[j], "question_stem", ""),
            )
            effective_sim = max(score, stem_sim)
            if effective_sim >= threshold:
                union(i, j)
                pairwise_sims[(min(i, j), max(i, j))] = (round(effective_sim, 4), reason)

    # Collect grouped indices
    groups: dict[int, list[int]] = {}
    for idx in range(n):
        root = find(idx)
        groups.setdefault(root, []).append(idx)

    clusters: list[dict[str, Any]] = []
    cluster_num = 1

    for _root, members in groups.items():
        if len(members) < 2:
            continue

        # Sort members by final_score descending (best first)
        def _get_score(q_idx: int) -> float:
            q = questions[q_idx]
            s = q.get("final_score") if isinstance(q, dict) else getattr(q, "final_score", 0)
            return float(s) if s is not None else 0.0

        sorted_members = sorted(members, key=_get_score, reverse=True)
        leader_idx = sorted_members[0]
        leader_q = questions[leader_idx]
        leader_dict = leader_q if isinstance(leader_q, dict) else leader_q.model_dump()

        duplicates = []
        for dup_idx in sorted_members[1:]:
            dup_q = questions[dup_idx]
            dup_dict = dup_q if isinstance(dup_q, dict) else dup_q.model_dump()
            pair_key = (min(leader_idx, dup_idx), max(leader_idx, dup_idx))
            sim_score, sim_reason = pairwise_sims.get(pair_key, (0.0, "Cluster collision"))
            if sim_score == 0.0:
                # Calculate directly against leader if not directly paired
                sim_score, sim_reason = compute_question_similarity(leader_q, dup_q)
            duplicates.append(
                {
                    "question": dup_dict,
                    "similarity_score": round(sim_score, 4),
                    "reason": sim_reason,
                }
            )

        clusters.append(
            {
                "cluster_id": f"cluster-{cluster_num}",
                "size": len(members),
                "leader_question": leader_dict,
                "duplicates": duplicates,
                "highest_similarity": max(d["similarity_score"] for d in duplicates)
                if duplicates
                else 1.0,
            }
        )
        cluster_num += 1

    # Sort clusters by size descending, then highest_similarity descending
    clusters.sort(key=lambda c: (c["size"], c["highest_similarity"]), reverse=True)
    return clusters
