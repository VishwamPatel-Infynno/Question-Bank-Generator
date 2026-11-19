"""
rag.py - Retrieval-Augmented Generation (RAG) & pgvector semantic search engine.

Integrates native PostgreSQL pgvector HNSW indexing, full-text search hybrid retrieval,
few-shot exemplar selection, and anti-collision neighbor grounding for question generation.
"""

from __future__ import annotations

import logging
from dataclasses import asdict, dataclass
from typing import Any

from sqlalchemy import text

from app.core.config import config
from app.db.session import async_session_factory
from app.schemas import GenerationRequest, enum_value
from app.services.embeddings import embed_question, embed_text

logger = logging.getLogger(__name__)


@dataclass
class SimilarQuestionResult:
    """Represents a question match retrieved via vector or hybrid search."""

    id: str
    section: str
    subtopic: str
    question_stem: str
    correct_answer_id: str
    explanation: str
    final_score: int
    similarity: float
    retrieval_method: str = "vector"
    options: list[dict[str, Any]] | None = None
    distractor_analysis: dict[str, Any] | None = None
    primary_trap: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class RAGExemplarContext:
    """Few-shot exemplar questions and cognitive traps retrieved for prompt grounding."""

    exemplars: list[dict[str, Any]]
    avoidance_stems: list[str]
    common_traps: list[str]
    prompt_context: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


async def find_similar_questions(
    query: str | list[float],
    *,
    section: str | None = None,
    subtopic: str | None = None,
    limit: int = 5,
    min_similarity: float = 0.5,
    exclude_ids: list[str] | None = None,
) -> list[SimilarQuestionResult]:
    """
    Finds semantically similar questions using pgvector cosine distance (<=>).
    Query can be either raw text or a precomputed 1536-dimensional float vector.
    """
    if not config.ENABLE_PGVECTOR_RAG:
        return []

    # Resolve vector
    query_vec = query if isinstance(query, list) else await embed_text(str(query))
    if not query_vec or len(query_vec) != config.EMBEDDING_DIMENSION:
        return []

    vec_str = "[" + ",".join(f"{x:.6f}" for x in query_vec) + "]"

    conditions = [
        "is_deleted = false",
        "status IN ('in_bank', 'ai_validated', 'batch_only')",
        "embedding IS NOT NULL",
    ]
    params: dict[str, Any] = {
        "limit": max(1, min(100, limit)),
        "min_sim": float(min_similarity),
    }

    if section:
        conditions.append("section = :section")
        params["section"] = enum_value(section)

    if subtopic:
        conditions.append("subtopic = :subtopic")
        params["subtopic"] = str(subtopic).strip()

    if exclude_ids:
        placeholders = [f":ex_{i}" for i in range(len(exclude_ids))]
        conditions.append(f"id NOT IN ({', '.join(placeholders)})")
        for i, ex_id in enumerate(exclude_ids):
            params[f"ex_{i}"] = ex_id

    where_clause = " AND ".join(conditions)

    sql = text(f"""
        SELECT
            id, section, subtopic, question_stem, correct_answer_id, explanation, final_score,
            (1.0 - (embedding <=> '{vec_str}'::vector)) AS similarity,
            options, review_rubric, primary_trap
        FROM questions
        WHERE {where_clause}
          AND (1.0 - (embedding <=> '{vec_str}'::vector)) >= :min_sim
        ORDER BY embedding <=> '{vec_str}'::vector ASC
        LIMIT :limit;
    """)

    try:
        async with async_session_factory() as session:
            result = await session.execute(sql, params)
            rows = result.fetchall()
            return [
                SimilarQuestionResult(
                    id=str(row[0]),
                    section=str(row[1]),
                    subtopic=str(row[2]),
                    question_stem=str(row[3]),
                    correct_answer_id=str(row[4]),
                    explanation=str(row[5] or ""),
                    final_score=int(row[6] or 0),
                    similarity=round(float(row[7]), 4),
                    retrieval_method="pgvector_cosine",
                    options=row[8] if len(row) > 8 and isinstance(row[8], list) else None,
                    distractor_analysis=(
                        row[9].get("distractor_analysis")
                        if len(row) > 9 and isinstance(row[9], dict)
                        else None
                    ),
                    primary_trap=str(row[10]) if len(row) > 10 and row[10] else None,
                )
                for row in rows
            ]
    except Exception as exc:
        logger.warning("pgvector similarity search failed (%s); returning empty pool.", exc)
        return []


async def hybrid_search_questions(
    query_text: str,
    *,
    section: str | None = None,
    subtopic: str | None = None,
    limit: int = 10,
    vector_weight: float = 0.7,
) -> list[SimilarQuestionResult]:
    """
    Performs hybrid retrieval combining pgvector cosine distance and PostgreSQL GIN full-text search.
    Calculates unified score = vector_weight * vector_sim + (1 - vector_weight) * fts_rank.
    """
    if not query_text.strip():
        return []

    # 1. Fetch vector matches
    vector_matches = await find_similar_questions(
        query_text,
        section=section,
        subtopic=subtopic,
        limit=limit * 2,
        min_similarity=0.4,
    )
    vector_map = {m.id: m for m in vector_matches}

    # 2. Fetch full-text search matches via PostgreSQL ts_rank
    conditions = [
        "is_deleted = false",
        "status IN ('in_bank', 'ai_validated', 'batch_only')",
    ]
    params: dict[str, Any] = {
        "fts_query": query_text.strip(),
        "limit": limit * 2,
    }
    if section:
        conditions.append("section = :section")
        params["section"] = enum_value(section)
    if subtopic:
        conditions.append("subtopic = :subtopic")
        params["subtopic"] = str(subtopic).strip()

    where_clause = " AND ".join(conditions)

    sql = text(f"""
        SELECT
            id, section, subtopic, question_stem, correct_answer_id, explanation, final_score,
            ts_rank_cd(
                to_tsvector('english',
                    coalesce(question_stem, '') || ' ' ||
                    coalesce(stimulus_text, '') || ' ' ||
                    coalesce(subtopic, '') || ' ' ||
                    coalesce(explanation, '')
                ),
                plainto_tsquery('english', :fts_query)
            ) AS fts_score,
            options, review_rubric, primary_trap
        FROM questions
        WHERE {where_clause}
          AND to_tsvector('english',
                coalesce(question_stem, '') || ' ' ||
                coalesce(stimulus_text, '') || ' ' ||
                coalesce(subtopic, '') || ' ' ||
                coalesce(explanation, '')
              ) @@ plainto_tsquery('english', :fts_query)
        ORDER BY fts_score DESC
        LIMIT :limit;
    """)

    fts_map: dict[str, tuple[Any, float]] = {}
    try:
        async with async_session_factory() as session:
            res = await session.execute(sql, params)
            for row in res.fetchall():
                fts_map[str(row[0])] = (row, float(row[7]))
    except Exception as exc:
        logger.debug("PostgreSQL FTS match query failed (%s); continuing with vector results.", exc)

    # Normalize FTS scores to [0, 1]
    max_fts = max((score for _, score in fts_map.values()), default=1.0) or 1.0

    all_ids = set(vector_map.keys()) | set(fts_map.keys())
    combined_results: list[tuple[float, SimilarQuestionResult]] = []

    fts_weight = 1.0 - vector_weight

    for qid in all_ids:
        vec_item = vector_map.get(qid)
        fts_item = fts_map.get(qid)

        v_sim = vec_item.similarity if vec_item else 0.35
        f_sim = (fts_item[1] / max_fts) if fts_item else 0.0

        hybrid_score = round((v_sim * vector_weight) + (f_sim * fts_weight), 4)

        if vec_item:
            base_item = vec_item
            base_item.similarity = hybrid_score
            base_item.retrieval_method = "hybrid_pgvector_fts" if fts_item else "pgvector_cosine"
        else:
            row = fts_item[0]
            base_item = SimilarQuestionResult(
                id=str(row[0]),
                section=str(row[1]),
                subtopic=str(row[2]),
                question_stem=str(row[3]),
                correct_answer_id=str(row[4]),
                explanation=str(row[5] or ""),
                final_score=int(row[6] or 0),
                similarity=hybrid_score,
                retrieval_method="fts_lexical",
                options=row[8] if len(row) > 8 and isinstance(row[8], list) else None,
                distractor_analysis=(
                    row[9].get("distractor_analysis")
                    if len(row) > 9 and isinstance(row[9], dict)
                    else None
                ),
                primary_trap=str(row[10]) if len(row) > 10 and row[10] else None,
            )
        combined_results.append((hybrid_score, base_item))

    combined_results.sort(key=lambda x: x[0], reverse=True)
    return [item for _, item in combined_results[:limit]]


async def retrieve_rag_exemplar_context(
    req: GenerationRequest,
    limit: int = 3,
) -> RAGExemplarContext:
    """
    Retrieves exemplar questions (score >= 90) and nearest neighbor avoidance stems
    to ground the generator prompt in authentic psychometrics while preventing duplication.
    """
    sec = enum_value(req.section)
    sub = req.subtopic or ""
    query_context = f"{sec} {sub} {req.thematic_angle or ''}".strip()

    # 1. Retrieve top-scoring exemplars for few-shot structural calibration
    exemplar_matches = await hybrid_search_questions(
        query_context,
        section=sec,
        subtopic=sub,
        limit=limit + 2,
    )
    high_yield_exemplars = [
        m.to_dict() for m in exemplar_matches if m.final_score >= config.RAG_EXEMPLAR_MIN_SCORE
    ][:limit]

    # 2. Retrieve nearest neighbor avoidance stems to enforce novelty
    semantic_neighbors = await find_similar_questions(
        query_context,
        section=sec,
        subtopic=sub,
        limit=4,
        min_similarity=0.60,
    )
    avoidance_stems = [
        m.question_stem[:160] + "..." if len(m.question_stem) > 160 else m.question_stem
        for m in semantic_neighbors
    ]

    # 3. Retrieve common traps historically flagged for this subtopic
    common_traps: list[str] = []
    try:
        async with async_session_factory() as session:
            trap_sql = text("""
                SELECT primary_trap, count(*) as count
                FROM questions
                WHERE section = :sec AND subtopic = :sub AND primary_trap IS NOT NULL
                GROUP BY primary_trap
                ORDER BY count DESC
                LIMIT 4;
            """)
            res = await session.execute(trap_sql, {"sec": sec, "sub": sub})
            common_traps = [str(r[0]) for r in res.fetchall() if r[0]]
    except Exception as exc:
        logger.debug("Could not fetch historical traps (%s).", exc)

    # 4. Format prompt injection block
    prompt_lines: list[str] = []
    if high_yield_exemplars:
        prompt_lines.append("[AAMC PSYCHOMETRIC BENCHMARK EXEMPLARS (High-Yield Calibration)]:")
        for i, ex in enumerate(high_yield_exemplars):
            prompt_lines.append(
                f"\n--- Benchmark Exemplar #{i + 1} (Score: {ex['final_score']}/100) ---"
            )
            prompt_lines.append(f"Stem: {ex['question_stem']}")
            opts = ex.get("options")
            if isinstance(opts, list) and len(opts) == 4:
                prompt_lines.append("Options:")
                for opt in opts:
                    opt_id = opt.get("id") or opt.get("key") or ""
                    opt_text = opt.get("text") or ""
                    is_key = " (Correct Key)" if opt_id == ex.get("correct_answer_id") else ""
                    prompt_lines.append(f"  {opt_id}. {opt_text}{is_key}")
            else:
                prompt_lines.append(f"Key: {ex.get('correct_answer_id', 'A')}")

            exp = ex.get("explanation")
            if exp:
                exp_str = exp if isinstance(exp, str) else str(exp)
                prompt_lines.append(f"Rationale: {exp_str[:300]}")

            trap = ex.get("primary_trap")
            if trap:
                prompt_lines.append(f"Target Trap Modeled: {trap}")

    if avoidance_stems:
        prompt_lines.append("\n[STRICT NOVELTY & ANTI-DUPLICATION CONSTRAINT]:")
        prompt_lines.append("The Question Bank already contains questions testing:")
        prompt_lines.extend(f"- {stem}" for stem in avoidance_stems)
        prompt_lines.append(
            "You MUST formulate a completely novel scenario testing an unaddressed variable, mechanism, or relationship."
        )

    if common_traps:
        prompt_lines.append(
            f"\n[TARGET COGNITIVE TRAPS]: Prioritize authentic distractors modeled on: {', '.join(common_traps)}."
        )

    prompt_context = "\n".join(prompt_lines).strip()
    return RAGExemplarContext(
        exemplars=high_yield_exemplars,
        avoidance_stems=avoidance_stems,
        common_traps=common_traps,
        prompt_context=prompt_context,
    )


async def backfill_question_embeddings(batch_size: int = 50) -> dict[str, int]:
    """
    Scans questions missing vector embeddings and populates them in batches.
    Idempotent and safe to run on startup or via background task.
    """
    total_backfilled = 0

    try:
        async with async_session_factory() as session:
            # Query questions where embedding is NULL
            select_sql = text(f"""
                SELECT id, section, subtopic, question_stem, options, correct_answer_id, explanation
                FROM questions
                WHERE is_deleted = false AND embedding IS NULL
                LIMIT {batch_size};
            """)
            res = await session.execute(select_sql)
            rows = res.fetchall()
            if not rows:
                return {"backfilled": 0, "remaining": 0}

            for row in rows:
                qid = str(row[0])
                q_dict = {
                    "section": row[1],
                    "subtopic": row[2],
                    "question_stem": row[3],
                    "options": row[4],
                    "correct_answer_id": row[5],
                    "explanation": row[6],
                }
                vec = await embed_question(q_dict)
                vec_str = "[" + ",".join(f"{x:.6f}" for x in vec) + "]"
                update_sql = text(f"""
                    UPDATE questions
                    SET embedding = '{vec_str}'::vector
                    WHERE id = :qid;
                """)
                await session.execute(update_sql, {"qid": qid})
                total_backfilled += 1

            await session.commit()

            # Count remaining
            count_sql = text(
                "SELECT count(*) FROM questions WHERE is_deleted = false AND embedding IS NULL;"
            )
            count_res = await session.execute(count_sql)
            remaining = int(count_res.scalar() or 0)

            logger.info(
                "Backfilled embeddings for %s questions (%s remaining).",
                total_backfilled,
                remaining,
            )
            return {"backfilled": total_backfilled, "remaining": remaining}

    except Exception as exc:
        logger.warning("Embedding backfill task encountered an error: %s", exc)
        return {"backfilled": total_backfilled, "error": str(exc)}
