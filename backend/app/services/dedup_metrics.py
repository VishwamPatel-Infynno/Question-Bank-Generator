"""
dedup_metrics.py - Tokenization, text normalization, and similarity scoring metrics.
"""

from __future__ import annotations

import contextlib
import difflib
import logging
import re
from collections import OrderedDict
from typing import Any, TypedDict

from pydantic import BaseModel

from app.schemas.extractors import extract_correct_answer_text
from app.schemas.extractors import extract_field as _field

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


class DuplicateMember(TypedDict, total=False):
    """Represents a redundant duplicate question within a duplicate cluster, along with similarity metrics."""

    question: dict[str, Any]
    similarity_score: float
    reason: str


class DuplicateCluster(TypedDict, total=False):
    """
    Represents an equivalence class of semantically identical or near-identical questions.

    Identifies the elected leader question (retained in the bank based on psychometric score or custom override)
    and the list of redundant duplicate members earmarked for purging or remediation.
    """

    cluster_id: str
    size: int
    leader_question: dict[str, Any]
    duplicates: list[DuplicateMember]
    highest_similarity: float


def normalize_text(text: str | None) -> str:
    """
    Normalizes text for linguistic comparison:
    - Strips LaTeX delimiters and HTML/XML tags
    - Replaces punctuation and special symbols with spaces
    - Lowercases and collapses multiple whitespace characters
    """
    if not text:
        return ""
    clean = re.sub(r"<[^>]+>", " ", text)
    clean = re.sub(r"(\$\$?|\\\(|\\\)|\\\[|\\\])", " ", clean)
    clean = re.sub(r"\\[a-zA-Z]+", " ", clean)
    clean = re.sub(r"[^a-zA-Z0-9\s]", " ", clean)
    tokens = clean.lower().split()
    return " ".join(tokens)


def extract_content_tokens(text: str | None) -> list[str]:
    """Returns filtered content tokens with stop words removed."""
    normalized = normalize_text(text)
    if not normalized:
        return []
    return [t for t in normalized.split() if t not in STOP_WORDS and len(t) > 1]


def normalize_token_stem(token: str) -> str:
    """Reduces common English plurals and inflectional suffixes for robust token comparison."""
    if len(token) <= 3:
        return token
    if token.endswith("ies") and len(token) > 4:
        return token[:-3] + "y"
    if token.endswith("es") and len(token) > 3:
        if token.endswith(("sses", "shes", "ches", "xes", "zes")):
            return token[:-2]
        return token[:-1]
    if token.endswith("s") and not token.endswith("ss"):
        return token[:-1]
    if token.endswith("ing") and len(token) > 5:
        return token[:-3]
    if token.endswith("ed") and len(token) > 4:
        return token[:-2]
    return token


def extract_normalized_stem_set(stem: str | None) -> set[str]:
    """Returns a set of suffix-normalized content tokens from text."""
    _, _, token_set, _ = get_or_create_stem_tokens(stem)
    return {normalize_token_stem(t) for t in token_set}


# In-memory LRU token cache keyed by normalized stem text
_StemTokens = tuple[str, list[str], set[str], set[tuple[str, str]]]
_STEM_TOKEN_CACHE: OrderedDict[str, _StemTokens] = OrderedDict()
_MAX_STEM_CACHE_SIZE = 2000


def get_or_create_stem_tokens(stem: str | None) -> _StemTokens:
    """
    Returns normalized text, filtered tokens list, tokens set, and bigrams set for a stem.

    Entries are keyed by the normalized stem text, so equal stems share one cache entry.
    Least-recently-used entries are evicted one at a time instead of flushing the whole cache.
    """
    norm = normalize_text(stem)
    cached = _STEM_TOKEN_CACHE.get(norm)
    if cached is not None:
        with contextlib.suppress(KeyError):
            _STEM_TOKEN_CACHE.move_to_end(norm)
        return cached

    tokens = [t for t in norm.split() if t not in STOP_WORDS and len(t) > 1] if norm else []
    token_set = set(tokens)
    bigrams = (
        {tuple(tokens[i : i + 2]) for i in range(len(tokens) - 1)} if len(tokens) >= 2 else set()
    )
    item: _StemTokens = (norm, tokens, token_set, bigrams)

    _STEM_TOKEN_CACHE[norm] = item
    import sys

    max_size = getattr(
        sys.modules.get("app.services.deduplication"), "_MAX_STEM_CACHE_SIZE", _MAX_STEM_CACHE_SIZE
    )
    with contextlib.suppress(KeyError):
        while len(_STEM_TOKEN_CACHE) > max_size:
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


_STEM_PRUNE_BELOW = 0.35
_OPTION_MATCH_RATIO = 0.70
_OPTION_LENGTH_RATIO_FLOOR = 0.55

_STEM_NEAR_DUPLICATE = 0.70
_STEM_SUBSTANTIAL = 0.50
_STEM_MODERATE = 0.40
_OPTIONS_NEAR_IDENTICAL = 0.75
_OPTIONS_SUBSTANTIAL = 0.50


def compute_stem_similarity(stem1: str, stem2: str, *, prune: bool = False) -> float:
    """
    Hybrid stem similarity combining token containment, 1-gram Jaccard, 2-gram Jaccard,
    and character sequence ratio.
    """
    norm1, tokens1, s1, b1 = get_or_create_stem_tokens(stem1)
    norm2, tokens2, s2, b2 = get_or_create_stem_tokens(stem2)
    if not tokens1 or not tokens2:
        return 0.0

    min_len = min(len(s1), len(s2))
    raw_containment = len(s1 & s2) / min_len if min_len > 0 else 0.0

    u1 = len(s1 | s2)
    raw_jaccard_1 = len(s1 & s2) / u1 if u1 > 0 else 0.0

    norm_s1 = {normalize_token_stem(t) for t in s1}
    norm_s2 = {normalize_token_stem(t) for t in s2}
    norm_min = min(len(norm_s1), len(norm_s2))
    norm_containment = len(norm_s1 & norm_s2) / norm_min if norm_min > 0 else 0.0
    norm_u1 = len(norm_s1 | norm_s2)
    norm_jaccard_1 = len(norm_s1 & norm_s2) / norm_u1 if norm_u1 > 0 else 0.0

    containment = max(raw_containment, norm_containment)
    jaccard_1 = max(raw_jaccard_1, norm_jaccard_1)

    u2 = len(b1 | b2)
    jaccard_2 = len(b1 & b2) / u2 if u2 > 0 else 0.0

    seq_ratio = 0.0
    if norm1 and norm2:
        matcher = difflib.SequenceMatcher(None, norm1, norm2)
        if prune:
            base = (0.35 * containment) + (0.25 * jaccard_1) + (0.20 * jaccard_2)
            for bound in (matcher.real_quick_ratio, matcher.quick_ratio):
                upper = base + 0.20 * bound()
                if upper < _STEM_PRUNE_BELOW - 1e-4:
                    return round(upper, 4)
        seq_ratio = matcher.ratio()

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
        normalize_text(_field(o, "text", str(o) if not isinstance(o, dict) else ""))
        for o in (opts1 or [])
    ]
    texts2 = [
        normalize_text(_field(o, "text", str(o) if not isinstance(o, dict) else ""))
        for o in (opts2 or [])
    ]
    texts1 = [t for t in texts1 if t]
    texts2 = [t for t in texts2 if t]

    if not texts1 or not texts2:
        return 0.0

    matches = 0
    for t1 in texts1:
        for t2 in texts2:
            if t1 == t2:
                matches += 1
                break
            l1, l2 = len(t1), len(t2)
            if max(l1, l2) > 0 and (min(l1, l2) / max(l1, l2)) < _OPTION_LENGTH_RATIO_FLOOR:
                continue
            if compute_sequence_ratio(t1, t2) > _OPTION_MATCH_RATIO:
                matches += 1
                break

    return round(matches / max(len(texts1), len(texts2)), 4)


def compute_question_similarity(
    candidate: dict[str, Any] | Any,
    reference: dict[str, Any] | Any,
    *,
    prune: bool = False,
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
    stem_sim = compute_stem_similarity(stem1, stem2, prune=prune)

    cand_key_text = extract_correct_answer_text(candidate)
    ref_key_text = extract_correct_answer_text(reference)
    key_sim = 0.0
    is_substantive_key = False
    key_token_overlap = 0
    key_containment = 0.0
    norm_k1: set[str] = set()
    norm_k2: set[str] = set()
    if cand_key_text and ref_key_text:
        key_sim = compute_stem_similarity(cand_key_text, ref_key_text)
        _, _, k_set1, _ = get_or_create_stem_tokens(cand_key_text)
        _, _, k_set2, _ = get_or_create_stem_tokens(ref_key_text)
        norm_k1 = {normalize_token_stem(t) for t in k_set1}
        norm_k2 = {normalize_token_stem(t) for t in k_set2}
        common_tokens = norm_k1 & norm_k2
        key_token_overlap = len(common_tokens)
        min_k = min(len(norm_k1), len(norm_k2))
        key_containment = (key_token_overlap / min_k) if min_k > 0 else 0.0
        min_words = min(len(cand_key_text.split()), len(ref_key_text.split()))
        is_substantive_key = min_words >= 3

    p_cand = _field(candidate, "passage_id")
    p_ref = _field(reference, "passage_id")
    same_passage = bool(p_cand and p_ref and str(p_cand) == str(p_ref))
    stim_cand = _field(candidate, "stimulus_text")
    stim_ref = _field(reference, "stimulus_text")
    if (
        not same_passage
        and stim_cand
        and stim_ref
        and len(str(stim_cand)) > 80
        and str(stim_cand) == str(stim_ref)
    ):
        same_passage = True
    if not same_passage:
        b_cand = _field(candidate, "batch_id")
        b_ref = _field(reference, "batch_id")
        is_p_cand = _field(candidate, "passage_required") in (
            True,
            "Yes",
            "single_passage",
        ) or bool(p_cand or stim_cand)
        is_p_ref = _field(reference, "passage_required") in (True, "Yes", "single_passage") or bool(
            p_ref or stim_ref
        )
        if b_cand and b_ref and str(b_cand) == str(b_ref) and is_p_cand and is_p_ref:
            same_passage = True

    # Cross-stem-key inverse collision detection (critical for same-passage items)
    is_inverse_collision = False
    inverse_reason = ""
    if same_passage and cand_key_text and ref_key_text and stem1 and stem2:
        norm_s1 = extract_normalized_stem_set(stem1)
        norm_s2 = extract_normalized_stem_set(stem2)

        generic_stem_words = frozenset(
            {
                "accord",
                "passag",
                "author",
                "suggest",
                "claim",
                "state",
                "describ",
                "follow",
                "best",
                "which",
                "would",
                "most",
                "direct",
                "support",
                "explain",
                "indic",
                "paragraph",
                "result",
                "observ",
                "find",
                "show",
                "base",
                "concern",
                "evaluat",
                "hypothet",
                "order",
                "perform",
                "propos",
                "suppos",
                "how",
                "why",
                "what",
                "where",
                "when",
                "true",
                "statement",
                "question",
            }
        )
        s1_sub = {t for t in norm_s1 if len(t) > 3 and t not in generic_stem_words}
        s2_sub = {t for t in norm_s2 if len(t) > 3 and t not in generic_stem_words}
        k1_sub = {t for t in norm_k1 if len(t) > 3 and t not in generic_stem_words}
        k2_sub = {t for t in norm_k2 if len(t) > 3 and t not in generic_stem_words}

        cross_1_2 = s1_sub & k2_sub  # Cand stem vs Ref key
        cross_2_1 = s2_sub & k1_sub  # Ref stem vs Cand key

        if len(cross_1_2) >= 2 and len(cross_2_1) >= 2 and (len(cross_1_2) + len(cross_2_1) >= 4):
            is_inverse_collision = True
            inverse_reason = (
                f"Same-passage inverse question collision: Cand stem shares {len(cross_1_2)} terms with Ref key "
                f"({', '.join(sorted(cross_1_2)[:3])}), and Cand key shares {len(cross_2_1)} terms with Ref stem "
                f"({', '.join(sorted(cross_2_1)[:3])})"
            )

    is_same_passage_key_collision = (
        same_passage
        and is_substantive_key
        and (
            key_sim >= 0.55
            or (key_token_overlap >= 3 and (key_containment >= 0.30 or key_sim >= 0.25))
        )
    )

    is_key_collision = is_inverse_collision or (
        is_substantive_key and (key_sim >= 0.55 or is_same_passage_key_collision)
    )

    if stem_sim < _STEM_PRUNE_BELOW and not is_key_collision:
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

    # 1. Intra-passage anti-collision (questions on the same reading passage)
    if same_passage:
        if is_inverse_collision:
            return 0.82, inverse_reason

        if is_same_passage_key_collision:
            effective_key_ratio = max(key_sim, key_containment)
            overall = max(0.78, round(0.50 * effective_key_ratio + 0.50 * stem_sim, 4))
            return (
                overall,
                f"Same-passage shared answer key concept ({key_token_overlap} shared key terms, {int(key_sim * 100)}% match)",
            )
        if stem_sim >= 0.50:
            overall = max(0.76, stem_sim)
            return overall, f"Same-passage stem collision ({int(stem_sim * 100)}% match)"

    # 2. General cross-question correct answer collision (substantive keys)
    if is_substantive_key and key_sim >= 0.70 and (stem_sim >= 0.35 or opts_sim >= 0.50):
        overall = max(0.76, round(0.50 * key_sim + 0.35 * stem_sim + 0.15 * opts_sim, 4))
        return overall, f"Identical correct answer rationale ({int(key_sim * 100)}% key match)"

    # 3. If stems are nearly identical, that alone drives the collision
    if stem_sim >= _STEM_NEAR_DUPLICATE:
        overall = stem_sim
        reason = f"High question stem textual overlap ({int(stem_sim * 100)}%)"
    # 4. If options are identical or near-identical and the stem has moderate-to-high overlap
    elif opts_sim >= _OPTIONS_NEAR_IDENTICAL and stem_sim >= _STEM_MODERATE:
        overall = round((0.50 * stem_sim) + (0.50 * opts_sim), 4)
        reason = f"Identical answer choices ({int(opts_sim * 100)}%) and conceptual stem match ({int(stem_sim * 100)}%)"
    # 5. If both stem and options have substantial overlap
    elif stem_sim >= _STEM_SUBSTANTIAL and opts_sim >= _OPTIONS_SUBSTANTIAL:
        overall = round((0.60 * stem_sim) + (0.40 * opts_sim), 4)
        reason = f"Question stem ({int(stem_sim * 100)}%) and answer choice ({int(opts_sim * 100)}%) collision"
    else:
        if is_substantive_key and key_sim >= 0.50:
            overall = round((0.50 * stem_sim) + (0.30 * opts_sim) + (0.20 * key_sim), 4)
            reason = f"Overall conceptual & key similarity ({int(overall * 100)}%)"
        else:
            overall = round((0.70 * stem_sim) + (0.30 * opts_sim), 4)
            reason = f"Overall conceptual similarity ({int(overall * 100)}%)"

    vec_sim = reference.get("_vector_similarity") if isinstance(reference, dict) else None
    if vec_sim is not None and float(vec_sim) > overall:
        return float(vec_sim), f"pgvector Semantic Cosine Match ({int(float(vec_sim) * 100)}%)"

    vec_sim = reference.get("_vector_similarity") if isinstance(reference, dict) else None
    if vec_sim is not None and float(vec_sim) > overall:
        return float(vec_sim), f"pgvector Semantic Cosine Match ({int(float(vec_sim) * 100)}%)"

    return overall, reason
