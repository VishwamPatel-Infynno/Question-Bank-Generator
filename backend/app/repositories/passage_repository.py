from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import and_, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import scoped_session
from app.models.passage import PassageModel
from app.models.question import QuestionModel
from app.repositories._filters import (
    LIKE_ESCAPE,
    active_passage_clause,
    active_question_clause,
    clamp_list_limit,
    like_contains,
)
from app.repositories.mappers import passage_model_to_schema, passage_schema_to_model
from app.schemas import Passage

logger = logging.getLogger(__name__)


async def get_passages(
    section: str | None = None,
    subtopic: str | None = None,
    search: str | None = None,
    include_deleted: bool = False,
    sort_by: str | None = "newest",
    limit: int | None = None,
    offset: int | None = 0,
    session: AsyncSession | None = None,
) -> list[Passage]:
    """Retrieves shared reading passages with optional filtering, search, pagination, and aggregated question_count."""
    async with scoped_session(session) as s:
        stmt = (
            select(PassageModel, func.count(QuestionModel.id).label("q_count"))
            .outerjoin(
                QuestionModel,
                and_(
                    QuestionModel.passage_id == PassageModel.id,
                    active_question_clause(),
                ),
            )
            .group_by(PassageModel.id)
        )
        if not include_deleted:
            stmt = stmt.where(active_passage_clause())
        if section:
            stmt = stmt.where(PassageModel.section == section)
        if subtopic:
            stmt = stmt.where(PassageModel.subtopic == subtopic)
        if search:
            wildcard = like_contains(search.strip())
            stmt = stmt.where(
                or_(
                    PassageModel.text.ilike(wildcard, escape=LIKE_ESCAPE),
                    PassageModel.title.ilike(wildcard, escape=LIKE_ESCAPE),
                    PassageModel.subtopic.ilike(wildcard, escape=LIKE_ESCAPE),
                    PassageModel.id.ilike(wildcard, escape=LIKE_ESCAPE),
                )
            )

        if sort_by == "oldest":
            stmt = stmt.order_by(PassageModel.created_at.asc())
        elif sort_by == "title":
            stmt = stmt.order_by(PassageModel.title.asc())
        elif sort_by == "questions":
            stmt = stmt.order_by(
                func.count(QuestionModel.id).desc(), PassageModel.created_at.desc()
            )
        else:
            stmt = stmt.order_by(PassageModel.created_at.desc())
        if offset and offset > 0:
            stmt = stmt.offset(offset)
        stmt = stmt.limit(clamp_list_limit(limit))
        result = await s.execute(stmt)
        rows = result.all()
        return [passage_model_to_schema(m, int(q_count or 0)) for m, q_count in rows]


async def count_passages(
    section: str | None = None,
    subtopic: str | None = None,
    search: str | None = None,
    include_deleted: bool = False,
    session: AsyncSession | None = None,
) -> int:
    """Counts reading passages matching filtering and search criteria via native SQL aggregation."""
    async with scoped_session(session) as s:
        stmt = select(func.count(PassageModel.id))
        if not include_deleted:
            stmt = stmt.where(active_passage_clause())
        if section:
            stmt = stmt.where(PassageModel.section == section)
        if subtopic:
            stmt = stmt.where(PassageModel.subtopic == subtopic)
        if search:
            wildcard = like_contains(search.strip())
            stmt = stmt.where(
                or_(
                    PassageModel.text.ilike(wildcard, escape=LIKE_ESCAPE),
                    PassageModel.title.ilike(wildcard, escape=LIKE_ESCAPE),
                    PassageModel.subtopic.ilike(wildcard, escape=LIKE_ESCAPE),
                    PassageModel.id.ilike(wildcard, escape=LIKE_ESCAPE),
                )
            )
        result = await s.execute(stmt)
        return int(result.scalar() or 0)


async def get_passage_by_id(
    passage_id: str,
    include_deleted: bool = False,
    session: AsyncSession | None = None,
) -> Passage | None:
    """Retrieves a single passage by primary key ID with aggregated active question count."""
    async with scoped_session(session) as s:
        stmt = (
            select(PassageModel, func.count(QuestionModel.id).label("q_count"))
            .outerjoin(
                QuestionModel,
                and_(
                    QuestionModel.passage_id == PassageModel.id,
                    active_question_clause(),
                ),
            )
            .where(PassageModel.id == passage_id)
            .group_by(PassageModel.id)
        )
        if not include_deleted:
            stmt = stmt.where(active_passage_clause())
        result = await s.execute(stmt)
        row = result.first()
        if not row:
            return None
        m, q_count = row
        return passage_model_to_schema(m, int(q_count or 0))


async def save_passage(passage: Passage, session: AsyncSession | None = None) -> Passage:
    """Creates or updates a passage record, syncing stimulus_text to linked questions."""
    passage.updated_at = datetime.now(UTC).isoformat()
    word_count = len(passage.text.split()) if passage.text else 0
    passage.word_count = word_count
    async with scoped_session(session) as s:
        model = passage_schema_to_model(passage)
        await s.merge(model)

        # Synchronize stimulus_text and visual stimulus to all linked questions if text is present
        if passage.id and passage.text is not None:
            values_to_update: dict[str, Any] = {
                "stimulus_text": passage.text,
            }
            if passage.image_url is not None:
                values_to_update["image_url"] = passage.image_url
            if passage.image_svg is not None:
                values_to_update["image_svg"] = passage.image_svg
            if passage.image_description is not None:
                values_to_update["image_description"] = passage.image_description

            await s.execute(
                update(QuestionModel)
                .where(QuestionModel.passage_id == passage.id)
                .values(**values_to_update)
            )

        await s.commit()
        return passage


async def delete_passage(passage_id: str, session: AsyncSession | None = None) -> tuple[bool, int]:
    """Soft-deletes a passage and its associated questions from active views while preserving all data for batch progress."""
    now_dt = datetime.now(UTC)
    async with scoped_session(session) as s:
        # Check if passage exists
        passage = await s.get(PassageModel, passage_id)
        if not passage:
            return False, 0

        # 1. Soft-delete all linked questions
        del_q_res = await s.execute(
            update(QuestionModel)
            .where(QuestionModel.passage_id == passage_id, QuestionModel.is_deleted.is_(False))
            .values(is_deleted=True, deleted_at=now_dt)
        )
        deleted_q_count = del_q_res.rowcount or 0

        # 2. Soft-delete the passage row
        passage.is_deleted = True
        passage.deleted_at = now_dt

        # Note: We do NOT clear job passage_id, and we do NOT decrement job or batch actual_count,
        # so that Batch Progress history remains 100% intact.
        await s.commit()

    logger.info(
        "Soft-deleted passage %s and %s associated question(s) (preserved for batch progress).",
        passage_id,
        deleted_q_count,
    )
    return True, deleted_q_count


async def restore_passage(passage_id: str, session: AsyncSession | None = None) -> bool:
    """Restores a soft-deleted passage."""
    async with scoped_session(session) as s:
        passage = await s.get(PassageModel, passage_id)
        if not passage:
            return False
        # Bring back the questions that were removed together with the passage (same deletion
        # timestamp), but not ones an editor deleted individually at another time.
        if passage.deleted_at is not None:
            await s.execute(
                update(QuestionModel)
                .where(
                    QuestionModel.passage_id == passage_id,
                    QuestionModel.deleted_at == passage.deleted_at,
                )
                .values(is_deleted=False, deleted_at=None)
            )
        passage.is_deleted = False
        passage.deleted_at = None
        await s.commit()
        return True
