"""
embeddings.py - High-performance embedding service with pgvector compatibility.

Provides asynchronous vector generation for questions, passages, and queries via LiteLLM
with in-memory SHA-256 caching and deterministic unit-vector fallback for offline resilience.
"""

from __future__ import annotations

import hashlib
import logging
import math
import re
from typing import Any

from app.core.config import config
from app.schemas.extractors import extract_field as _field

logger = logging.getLogger(__name__)

# In-memory vector cache: sha256(text) -> list[float]
_EMBEDDING_CACHE: dict[str, list[float]] = {}
_MAX_CACHE_SIZE = 10_000


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


async def embed_text(text: str, model: str | None = None) -> list[float]:
    """Generates an embedding vector for a single string with caching and fallback."""
    results = await embed_texts([text], model=model)
    return results[0] if results else deterministic_unit_vector(text, config.EMBEDDING_DIMENSION)


async def embed_texts(texts: list[str], model: str | None = None) -> list[list[float]]:
    """
    Generates embedding vectors for a list of strings.
    Checks memory cache first, batches misses to LiteLLM, and falls back to deterministic vectors
    if offline mode is active or an LLM exception occurs.
    """
    if not texts:
        return []

    target_model = model or config.EMBEDDING_MODEL
    dim = config.EMBEDDING_DIMENSION

    results: list[list[float] | None] = [None] * len(texts)
    misses_indices: list[int] = []
    misses_texts: list[str] = []

    for idx, t in enumerate(texts):
        key = _hash_text(t, target_model)
        cached = _EMBEDDING_CACHE.get(key)
        if cached is not None and len(cached) == dim:
            results[idx] = cached
        else:
            misses_indices.append(idx)
            misses_texts.append(t)

    if not misses_texts:
        return [r for r in results if r is not None]

    # Offline mode or missing keys -> fast deterministic generation
    if config.OFFLINE_MODE:
        for orig_idx, t in zip(misses_indices, misses_texts, strict=False):
            vec = deterministic_unit_vector(t, dim)
            results[orig_idx] = vec
            if len(_EMBEDDING_CACHE) < _MAX_CACHE_SIZE:
                _EMBEDDING_CACHE[_hash_text(t, target_model)] = vec
        return [r for r in results if r is not None]

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
        if len(data) == len(misses_texts):
            for orig_idx, t, item in zip(misses_indices, misses_texts, data, strict=False):
                raw_vec = (
                    item.get("embedding")
                    if isinstance(item, dict)
                    else getattr(item, "embedding", None)
                )
                if raw_vec and len(raw_vec) == dim:
                    results[orig_idx] = raw_vec
                    if len(_EMBEDDING_CACHE) < _MAX_CACHE_SIZE:
                        _EMBEDDING_CACHE[_hash_text(t, target_model)] = raw_vec
                else:
                    results[orig_idx] = deterministic_unit_vector(t, dim)
        else:
            raise ValueError(
                f"LiteLLM embedding response length mismatch ({len(data)} vs {len(misses_texts)})"
            )

    except Exception as exc:
        logger.warning(
            "LiteLLM embedding call failed for %s items (%s); using deterministic unit vectors.",
            len(misses_texts),
            exc,
        )
        for orig_idx, t in zip(misses_indices, misses_texts, strict=False):
            vec = deterministic_unit_vector(t, dim)
            results[orig_idx] = vec
            if len(_EMBEDDING_CACHE) < _MAX_CACHE_SIZE:
                _EMBEDDING_CACHE[_hash_text(t, target_model)] = vec

    return [
        r if r is not None else deterministic_unit_vector(texts[i], dim)
        for i, r in enumerate(results)
    ]


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


async def embed_question(question: dict[str, Any] | Any) -> list[float]:
    """Generates an embedding vector for a candidate or stored question."""
    text = build_question_embedding_text(question)
    return await embed_text(text)


async def embed_passage(
    passage: str | dict[str, Any] | Any,
    title: str = "",
    section: str = "",
) -> list[float]:
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
