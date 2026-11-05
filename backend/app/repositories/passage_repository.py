from __future__ import annotations

import logging
from datetime import UTC, datetime

from sqlalchemy import and_, func, or_, select, update

from app.db.base import to_datetime, to_iso_str
from app.db.session import async_session_factory
from app.models.passage import PassageModel
from app.models.question import QuestionModel
from app.repositories._filters import active_passage_clause, active_question_clause
from app.schemas import Passage

logger = logging.getLogger(__name__)


def _passage_model_to_schema(m: PassageModel, question_count: int = 0) -> Passage:
    """Converts a SQLAlchemy PassageModel to a Pydantic Passage schema."""
    return Passage(
        id=m.id,
        title=m.title,
        text=m.text,
        word_count=m.word_count,
        section=m.section,
        subtopic=m.subtopic,
        image_url=m.image_url,
        image_svg=m.image_svg,
        image_description=m.image_description,
        question_count=question_count,
        is_deleted=getattr(m, "is_deleted", False) or False,
        deleted_at=to_iso_str(m.deleted_at) if getattr(m, "deleted_at", None) else None,
        created_at=to_iso_str(m.created_at),
        updated_at=to_iso_str(m.updated_at) if m.updated_at else None,
    )


def _passage_schema_to_model(p: Passage) -> PassageModel:
    """Converts a Pydantic Passage schema to a SQLAlchemy PassageModel."""
    word_count = p.word_count or (len(p.text.split()) if p.text else 0)
    return PassageModel(
        id=p.id,
        title=p.title,
        text=p.text,
        word_count=word_count,
        section=p.section,
        subtopic=p.subtopic,
        image_url=p.image_url,
        image_svg=p.image_svg,
        image_description=p.image_description,
        is_deleted=bool(p.is_deleted),
        deleted_at=to_datetime(p.deleted_at) if p.deleted_at else None,
        created_at=to_datetime(p.created_at),
        updated_at=to_datetime(p.updated_at) if p.updated_at else datetime.now(UTC),
    )


async def get_passages(
    section: str | None = None,
    subtopic: str | None = None,
    search: str | None = None,
    include_deleted: bool = False,
) -> list[Passage]:
    """Retrieves shared reading passages with optional filtering, search, and aggregated question_count."""
    async with async_session_factory() as session:
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
            wildcard = f"%{search.strip()}%"
            stmt = stmt.where(
                or_(
                    PassageModel.text.ilike(wildcard),
                    PassageModel.title.ilike(wildcard),
                    PassageModel.subtopic.ilike(wildcard),
                    PassageModel.id.ilike(wildcard),
                )
            )

        stmt = stmt.order_by(PassageModel.created_at.desc())
        result = await session.execute(stmt)
        rows = result.all()
        return [_passage_model_to_schema(m, int(q_count or 0)) for m, q_count in rows]


async def get_passage_by_id(passage_id: str, include_deleted: bool = False) -> Passage | None:
    """Retrieves a single passage by primary key ID with aggregated active question count."""
    async with async_session_factory() as session:
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
        result = await session.execute(stmt)
        row = result.first()
        if not row:
            return None
        m, q_count = row
        return _passage_model_to_schema(m, int(q_count or 0))


async def save_passage(passage: Passage) -> Passage:
    """Creates or updates a passage record, syncing stimulus_text to linked questions."""
    passage.updated_at = datetime.now(UTC).isoformat()
    word_count = len(passage.text.split()) if passage.text else 0
    passage.word_count = word_count
    async with async_session_factory() as session:
        model = _passage_schema_to_model(passage)
        await session.merge(model)

        # Synchronize stimulus_text and visual stimulus to all linked questions if text is present
        if passage.id and passage.text is not None:
            values_to_update: dict = {
                "stimulus_text": passage.text,
            }
            if passage.image_url is not None:
                values_to_update["image_url"] = passage.image_url
            if passage.image_svg is not None:
                values_to_update["image_svg"] = passage.image_svg
            if passage.image_description is not None:
                values_to_update["image_description"] = passage.image_description

            await session.execute(
                update(QuestionModel)
                .where(QuestionModel.passage_id == passage.id)
                .values(**values_to_update)
            )

        await session.commit()
        return passage


async def delete_passage(passage_id: str) -> tuple[bool, int]:
    """Soft-deletes a passage and its associated questions from active views while preserving all data for batch progress."""
    now_dt = datetime.now(UTC)
    async with async_session_factory() as session:
        # Check if passage exists
        passage = await session.get(PassageModel, passage_id)
        if not passage:
            return False, 0

        # 1. Soft-delete all linked questions
        del_q_res = await session.execute(
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
        await session.commit()

    logger.info(
        f"Soft-deleted passage {passage_id} and {deleted_q_count} associated question(s) (preserved for batch progress)."
    )
    return True, deleted_q_count


async def restore_passage(passage_id: str) -> bool:
    """Restores a soft-deleted passage."""
    async with async_session_factory() as session:
        passage = await session.get(PassageModel, passage_id)
        if not passage:
            return False
        # Bring back the questions that were removed together with the passage (same deletion
        # timestamp), but not ones an editor deleted individually at another time.
        if passage.deleted_at is not None:
            await session.execute(
                update(QuestionModel)
                .where(
                    QuestionModel.passage_id == passage_id,
                    QuestionModel.deleted_at == passage.deleted_at,
                )
                .values(is_deleted=False, deleted_at=None)
            )
        passage.is_deleted = False
        passage.deleted_at = None
        await session.commit()
        return True
