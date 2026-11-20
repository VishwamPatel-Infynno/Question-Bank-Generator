"""
embeddings.py - High-performance embedding service with pgvector compatibility.

Provides asynchronous vector generation for questions, passages, and queries via LiteLLM
with a bounded in-memory LRU cache and deterministic unit vectors for offline mode only.
"""

from __future__ import annotations

import hashlib
import logging
import math
import re
from collections import OrderedDict
from typing import Any

from app.core.config import config
from app.schemas import extract_field as _field

logger = logging.getLogger(__name__)

# In-memory bounded LRU vector cache: sha256(model:text) -> list[float]
_EMBEDDING_CACHE: OrderedDict[str, list[float]] = OrderedDict()
_MAX_CACHE_SIZE = 1024


def _cache_get(key: str) -> list[float] | None:
    vec = _EMBEDDING_CACHE.get(key)
    if vec is not None:
        _EMBEDDING_CACHE.move_to_end(key)
    return vec


def _cache_put(key: str, vec: list[float]) -> None:
    _EMBEDDING_CACHE[key] = vec
    _EMBEDDING_CACHE.move_to_end(key)
    while len(_EMBEDDING_CACHE) > _MAX_CACHE_SIZE:
        _EMBEDDING_CACHE.popitem(last=False)


def _hash_text(text: str, model: str) -> str:
    """Generates a cache key combining normalized text and the embedding model."""
    normalized = re.sub(r"\s+", " ", text.strip().lower())
    return hashlib.sha256(f"{model}:{normalized}".encode()).hexdigest()


def deterministic_unit_vector(text: str, dimension: int = 1536) -> list[float]:
    """
    Generates a deterministic, normalized 1536-dimensional unit vector from text.
    Guarantees:
    - Same text -> exactly identical unit vector.
    - L2 norm is strictly 1.0 (+/- 1e-6).
    - Runs in < 0.1ms offline with zero external network dependencies.
    """
    normalized = re.sub(r"\s+", " ", text.strip().lower())
    if not normalized:
        return [0.0] * dimension

    # Use multi-pass SHA-256 hashing to seed dimension values
    vec: list[float] = []
    chunk_count = math.ceil(dimension / 8)  # 8 floats (4 bytes each) per 32-byte sha256 hash
    for chunk_idx in range(chunk_count):
        seed = f"{normalized}:{chunk_idx}"
        digest = hashlib.sha256(seed.encode("utf-8")).digest()
        for i in range(0, len(digest), 4):
            if len(vec) >= dimension:
                break
            # Convert 4 bytes to an integer and scale to [-1.0, 1.0]
            val = int.from_bytes(digest[i : i + 4], byteorder="big", signed=True)
            vec.append(float(val) / 2147483648.0)

    # Normalize vector to unit length (L2 norm = 1.0)
    norm = math.sqrt(sum(x * x for x in vec))
    if norm > 1e-9:
        vec = [x / norm for x in vec]
    else:
        vec[0] = 1.0

    return vec


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """Computes cosine similarity between two float vectors in [-1.0, 1.0]."""
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b, strict=False))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a <= 1e-9 or norm_b <= 1e-9:
        return 0.0
    return max(-1.0, min(1.0, dot / (norm_a * norm_b)))


def cosine_distance(a: list[float], b: list[float]) -> float:
    """Computes cosine distance: 1 - cosine_similarity."""
    return max(0.0, 1.0 - cosine_similarity(a, b))


async def embed_text(text: str, model: str | None = None) -> list[float] | None:
    """Embeds one string; None when the live provider failed (never a fake vector)."""
    results = await embed_texts([text], model=model)
    return results[0] if results else None


async def embed_texts(texts: list[str], model: str | None = None) -> list[list[float] | None]:
    """
    Generates embedding vectors for a list of strings (one entry per input, order preserved).
    Checks the LRU cache first and batches misses to LiteLLM. Deterministic vectors are used
    only in offline mode; when a live provider call fails the affected entries are ``None``
    (and nothing is cached) so a fake vector is never persisted or compared as if it were real.
    """
    if not texts:
        return []

    target_model = model or config.EMBEDDING_MODEL
    dim = config.EMBEDDING_DIMENSION

    results: list[list[float] | None] = [None] * len(texts)
    misses_indices: list[int] = []
    misses_texts: list[str] = []

    for idx, t in enumerate(texts):
        cached = _cache_get(_hash_text(t, target_model))
        if cached is not None and len(cached) == dim:
            results[idx] = cached
        else:
            misses_indices.append(idx)
            misses_texts.append(t)

    if not misses_texts:
        return results

    # Offline mode or missing keys -> fast deterministic generation
    if config.OFFLINE_MODE:
        for orig_idx, t in zip(misses_indices, misses_texts, strict=False):
            vec = deterministic_unit_vector(t, dim)
            results[orig_idx] = vec
            _cache_put(_hash_text(t, target_model), vec)
        return results

    # Attempt live LiteLLM embedding call
    try:
        import litellm

        api_key = config.OPENAI_API_KEY or config.DEEPINFRA_API_KEY or None
        response = await litellm.aembedding(
            model=target_model,
            input=misses_texts,
            api_key=api_key,
        )
        data = getattr(response, "data", [])
        if len(data) != len(misses_texts):
            raise ValueError(
                f"LiteLLM embedding response length mismatch ({len(data)} vs {len(misses_texts)})"
            )
        for orig_idx, t, item in zip(misses_indices, misses_texts, data, strict=False):
            raw_vec = (
                item.get("embedding")
                if isinstance(item, dict)
                else getattr(item, "embedding", None)
            )
            if raw_vec and len(raw_vec) == dim:
                results[orig_idx] = raw_vec
                _cache_put(_hash_text(t, target_model), raw_vec)
            else:
                logger.warning("Embedding provider returned a missing/wrong-size vector; skipping.")
    except Exception as exc:
        logger.warning(
            "LiteLLM embedding call failed for %s items (%s); no embedding will be stored.",
            len(misses_texts),
            exc,
        )

    return results


def build_question_embedding_text(question: dict[str, Any] | Any) -> str:
    """Formats a question dictionary or model into a rich semantic string for embedding."""
    sec = _field(question, "section") or "MCAT"
    sub = _field(question, "subtopic") or ""
    stem = _field(question, "question_stem") or ""
    expl = _field(question, "explanation") or ""
    key = _field(question, "correct_answer_id") or ""

    opts = _field(question, "options") or []
    opt_strs = []
    if isinstance(opts, list):
        for o in opts:
            if isinstance(o, dict):
                opt_strs.append(f"{o.get('id', '')}: {o.get('text', '')}")
            elif hasattr(o, "text"):
                opt_strs.append(f"{getattr(o, 'id', '')}: {getattr(o, 'text', '')}")
    options_summary = "; ".join(opt_strs)

    return (
        f"Section: {sec} | Subtopic: {sub} | Question: {stem} | "
        f"Choices: {options_summary} | Key: {key} | Explanation: {expl[:500]}"
    ).strip()


async def embed_question(question: dict[str, Any] | Any) -> list[float] | None:
    """Generates an embedding vector for a candidate or stored question."""
    text = build_question_embedding_text(question)
    return await embed_text(text)


async def embed_passage(
    passage: str | dict[str, Any] | Any,
    title: str = "",
    section: str = "",
) -> list[float] | None:
    """Generates an embedding vector for a reading passage (accepts str, dict, or Passage model)."""
    if isinstance(passage, str):
        p_text = passage
        p_title = title
        p_sec = section
    elif isinstance(passage, dict):
        p_text = passage.get("passage_text") or passage.get("text") or ""
        p_title = passage.get("title") or passage.get("topic") or title
        p_sec = passage.get("section") or section
    else:
        p_text = getattr(passage, "passage_text", "") or getattr(passage, "text", "")
        p_title = getattr(passage, "title", "") or getattr(passage, "topic", "") or title
        p_sec = getattr(passage, "section", "") or section

    payload = f"Passage Title: {p_title} | Section: {p_sec}\n\n{p_text[:3000]}"
    return await embed_text(payload)
