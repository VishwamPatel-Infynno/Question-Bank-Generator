from __future__ import annotations

from typing import Any

from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import defer

from app.core.config import config
from app.models.batch import GenerationBatchModel
from app.models.question import QuestionModel
from app.repositories._filters import LIKE_ESCAPE, active_question_clause, like_contains
from app.schemas import BatchStatus

# The slim schema omits these blobs anyway (about 70% of a row's bytes): do not read them
SLIM_DEFER = (
    defer(QuestionModel.stage_outcomes),
    defer(QuestionModel.iterations_history),
    defer(QuestionModel.token_usage_details),
)

# Stored difficulty labels vary in spelling and case; every spelling of a level shares one bucket
_LOW_LABELS = ["low", "Low", "easy", "Easy"]
_MEDIUM_LABELS = ["medium", "Medium", "standard", "Standard"]
_HIGH_LABELS = ["high", "High", "hard", "Hard"]
DIFFICULTY_ALIASES: dict[str, list[str]] = {
    **dict.fromkeys(("low", "easy"), _LOW_LABELS),
    **dict.fromkeys(("medium", "standard"), _MEDIUM_LABELS),
    **dict.fromkeys(("high", "hard"), _HIGH_LABELS),
}


def build_question_filters(
    section: str | None = None,
    difficulty: str | None = None,
    search: str | None = None,
    combination_id: str | None = None,
    run_id: str | None = None,
    batch_id: str | None = None,
    job_id: str | None = None,
    passage_id: str | None = None,
    status: str | None = None,
    include_deleted: bool = False,
) -> list[Any]:
    """Builds shared SQLAlchemy filter conditions across list and count queries."""
    conditions: list[Any] = []
    if not include_deleted:
        conditions.append(active_question_clause())

    if section:
        conditions.append(QuestionModel.section == section)
    if difficulty:
        diff_lower = difficulty.strip().lower()
        aliases = DIFFICULTY_ALIASES.get(diff_lower)
        if aliases:
            conditions.append(QuestionModel.difficulty.in_(aliases))
        else:
            conditions.append(QuestionModel.difficulty == difficulty)
    if combination_id:
        conditions.append(QuestionModel.combination_id == combination_id)
    if run_id:
        conditions.append(QuestionModel.run_id == run_id)
    if batch_id:
        conditions.append(QuestionModel.batch_id == batch_id)
    if job_id:
        conditions.append(QuestionModel.job_id == job_id)
    if passage_id:
        conditions.append(QuestionModel.passage_id == passage_id)
    if status and status != "all":
        conditions.append(QuestionModel.status == status)
        if status == "ai_validated":
            in_progress_batches = select(GenerationBatchModel.id).where(
                GenerationBatchModel.status == BatchStatus.IN_PROGRESS
            )
            conditions.append(
                and_(
                    QuestionModel.final_score > config.PASSING_SCORE_THRESHOLD,
                    or_(
                        QuestionModel.batch_id.is_(None),
                        QuestionModel.batch_id.notin_(in_progress_batches),
                    ),
                )
            )

    if search:
        search_clean = search.strip()
        wildcard = like_contains(search_clean)

        # Hybrid PostgreSQL search: tsvector full-text match + ILIKE substring fallback
        fts_vector = func.to_tsvector(
            "english",
            func.coalesce(QuestionModel.question_stem, "")
            + " "
            + func.coalesce(QuestionModel.stimulus_text, "")
            + " "
            + func.coalesce(QuestionModel.subtopic, "")
            + " "
            + func.coalesce(QuestionModel.explanation, ""),
        )
        fts_condition = fts_vector.op("@@")(func.plainto_tsquery("english", search_clean))

        conditions.append(
            or_(
                fts_condition,
                QuestionModel.id.ilike(wildcard, escape=LIKE_ESCAPE),
                QuestionModel.question_stem.ilike(wildcard, escape=LIKE_ESCAPE),
                QuestionModel.stimulus_text.ilike(wildcard, escape=LIKE_ESCAPE),
                QuestionModel.subtopic.ilike(wildcard, escape=LIKE_ESCAPE),
                QuestionModel.explanation.ilike(wildcard, escape=LIKE_ESCAPE),
                QuestionModel.combination_id.ilike(wildcard, escape=LIKE_ESCAPE),
                QuestionModel.content_domain.ilike(wildcard, escape=LIKE_ESCAPE),
                QuestionModel.run_id.ilike(wildcard, escape=LIKE_ESCAPE),
                QuestionModel.batch_id.ilike(wildcard, escape=LIKE_ESCAPE),
                QuestionModel.passage_id.ilike(wildcard, escape=LIKE_ESCAPE),
            )
        )

    return conditions
