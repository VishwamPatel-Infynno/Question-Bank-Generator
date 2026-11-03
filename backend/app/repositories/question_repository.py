import logging
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import and_, delete, func, or_, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.db.base import to_datetime, to_iso_str
from app.db.session import async_session_factory
from app.models.batch import GenerationBatchModel
from app.models.passage import PassageModel
from app.models.question import QuestionModel
from app.schemas import DuplicateInfo, OptionChoice, Question, ReviewScore

logger = logging.getLogger(__name__)


def _model_to_schema(m: QuestionModel, slim: bool = False) -> Question:
    """Converts a SQLAlchemy QuestionModel to a Pydantic Question schema.

    When slim=True, heavy nested arrays and diagnostic JSON blobs
    (stage_outcomes, iterations_history, token_usage_details) are omitted
    to minimize serialization overhead and memory footprint in list queries.
    """
    options = [OptionChoice(**o) for o in (m.options or [])]
    rubric = ReviewScore(**m.review_rubric) if m.review_rubric else None
    dup_info = (
        DuplicateInfo(**m.duplicate_info)
        if getattr(m, "duplicate_info", None) and isinstance(m.duplicate_info, dict)
        else None
    )

    answer_ids = m.correct_answer_ids
    if not answer_ids and m.correct_answer_id:
        answer_ids = [k.strip().upper() for k in m.correct_answer_id.split(",") if k.strip()]

    return Question(
        id=m.id,
        run_id=m.run_id,
        batch_id=m.batch_id,
        job_id=getattr(m, "job_id", None),
        status=getattr(m, "status", None) or "in_bank",
        section=m.section,
        section_label=m.section_label,
        subtopic=m.subtopic,
        difficulty=m.difficulty,
        stimulus_text=m.stimulus_text or "",
        question_stem=m.question_stem,
        options=options,
        correct_answer_id=m.correct_answer_id,
        correct_answer_ids=answer_ids or [],
        explanation=m.explanation,
        image_url=m.image_url,
        image_svg=m.image_svg,
        image_description=m.image_description,
        final_score=m.final_score,
        review_rubric=rubric,
        iteration_count=m.iteration_count or 1,
        iterations_history=[] if slim else (m.iterations_history or []),
        created_at=to_iso_str(m.created_at),
        updated_at=to_iso_str(m.updated_at) if m.updated_at else None,
        total_tokens=m.total_tokens or 0,
        prompt_tokens=m.prompt_tokens or 0,
        completion_tokens=m.completion_tokens or 0,
        cost_usd=float(m.cost_usd) if m.cost_usd is not None else 0.0,
        token_usage_details=[] if slim else (m.token_usage_details or []),
        combination_id=m.combination_id,
        content_domain=m.content_domain,
        question_type=m.question_type,
        interaction_type=m.interaction_type or "single_choice",
        primary_trap=m.primary_trap,
        passage_required=m.passage_required,
        passage_questions=m.passage_questions,
        passage_id=getattr(m, "passage_id", None),
        passage_mode=getattr(m, "passage_mode", None),
        visual_type=m.visual_type or "None",
        mcat_scaled_score=getattr(m, "mcat_scaled_score", None),
        aamc_skill=getattr(m, "aamc_skill", None),
        subject=getattr(m, "subject", None),
        unit=getattr(m, "unit", None),
        topic=getattr(m, "topic", None),
        subskill=getattr(m, "subskill", None),
        likely_mistake_pattern=getattr(m, "likely_mistake_pattern", None),
        duplicate_info=dup_info,
        is_duplicate_override=bool(getattr(m, "is_duplicate_override", False)),
        is_deleted=bool(getattr(m, "is_deleted", False)),
        deleted_at=to_iso_str(m.deleted_at) if getattr(m, "deleted_at", None) else None,
        stage_outcomes={} if slim else (m.stage_outcomes or {}),
    )


def _schema_to_model(q: Question) -> QuestionModel:
    """Converts a Pydantic Question schema to a SQLAlchemy QuestionModel."""
    options_data = [opt.model_dump() for opt in q.options]
    rubric_data = q.review_rubric.model_dump() if q.review_rubric else None
    dup_data = q.duplicate_info.model_dump() if q.duplicate_info else None

    return QuestionModel(
        id=q.id,
        run_id=q.run_id,
        batch_id=q.batch_id,
        job_id=getattr(q, "job_id", None),
        status=getattr(q, "status", None) or "in_bank",
        section=q.section,
        section_label=q.section_label,
        subtopic=q.subtopic,
        difficulty=q.difficulty,
        stimulus_text=q.stimulus_text,
        question_stem=q.question_stem,
        options=options_data,
        correct_answer_id=q.correct_answer_id,
        correct_answer_ids=q.correct_answer_ids,
        explanation=q.explanation,
        image_url=q.image_url,
        image_svg=q.image_svg,
        image_description=q.image_description,
        final_score=q.final_score,
        review_rubric=rubric_data,
        iteration_count=q.iteration_count,
        iterations_history=q.iterations_history,
        created_at=to_datetime(q.created_at),
        updated_at=to_datetime(q.updated_at) if q.updated_at else datetime.now(UTC),
        total_tokens=q.total_tokens,
        prompt_tokens=q.prompt_tokens,
        completion_tokens=q.completion_tokens,
        cost_usd=q.cost_usd,
        token_usage_details=q.token_usage_details,
        combination_id=q.combination_id,
        content_domain=q.content_domain,
        question_type=q.question_type,
        interaction_type=q.interaction_type,
        primary_trap=q.primary_trap,
        passage_required=q.passage_required,
        passage_questions=q.passage_questions,
        passage_id=q.passage_id,
        passage_mode=q.passage_mode,
        visual_type=q.visual_type,
        mcat_scaled_score=q.mcat_scaled_score,
        aamc_skill=q.aamc_skill,
        subject=q.subject,
        unit=q.unit,
        topic=q.topic,
        subskill=q.subskill,
        likely_mistake_pattern=q.likely_mistake_pattern,
        duplicate_info=dup_data,
        is_duplicate_override=q.is_duplicate_override,
        is_deleted=bool(getattr(q, "is_deleted", False)),
        deleted_at=to_datetime(q.deleted_at) if getattr(q, "deleted_at", None) else None,
        stage_outcomes=q.stage_outcomes,
    )


async def save_question(q: Question) -> Question:
    """Inserts or updates a question in PostgreSQL, auto-syncing passages and batches."""
    now_dt = datetime.now(UTC)
    now_iso = now_dt.isoformat()
    q.updated_at = now_iso

    async with async_session_factory() as session:
        # 1. Auto-sync Passage record atomically if passage_id and stimulus_text exist
        if q.passage_id and q.stimulus_text and q.stimulus_text.strip():
            p_stmt = (
                pg_insert(PassageModel)
                .values(
                    id=q.passage_id,
                    title=f"{q.subtopic or q.section} Passage",
                    text=q.stimulus_text.strip(),
                    word_count=len(q.stimulus_text.split()),
                    section=q.section,
                    subtopic=q.subtopic,
                    image_url=q.image_url,
                    image_svg=q.image_svg,
                    image_description=q.image_description,
                    created_at=to_datetime(q.created_at),
                    updated_at=now_dt,
                )
                .on_conflict_do_update(
                    index_elements=["id"],
                    set_={
                        "text": q.stimulus_text.strip(),
                        "word_count": len(q.stimulus_text.split()),
                        "updated_at": now_dt,
                    },
                )
            )
            await session.execute(p_stmt)

        # 2. Auto-sync GenerationBatch record atomically if batch_id exists (idempotent, no inflation on edit)
        if q.batch_id:
            b_stmt = (
                pg_insert(GenerationBatchModel)
                .values(
                    id=q.batch_id,
                    section=q.section,
                    subtopic=q.subtopic,
                    difficulty=q.difficulty,
                    passage_mode=q.passage_mode,
                    target_count=1,
                    actual_count=1,
                    total_tokens=q.total_tokens or 0,
                    cost_usd=q.cost_usd or 0.0,
                    status="completed",
                    created_at=to_datetime(q.created_at),
                    updated_at=now_dt,
                )
                .on_conflict_do_nothing(index_elements=["id"])
            )
            await session.execute(b_stmt)

        # 3. Save QuestionModel
        model = _schema_to_model(q)
        await session.merge(model)
        await session.commit()
        return q


async def save_questions_batch(questions: list[Question]) -> list[str]:
    """Inserts or updates an array of questions in PostgreSQL within a single atomic transaction, auto-syncing passages and batches."""
    if not questions:
        return []

    now_dt = datetime.now(UTC)
    now_iso = now_dt.isoformat()
    saved_ids = []

    async with async_session_factory() as session:
        # Pre-group passages and batches to optimize DB roundtrips
        passages_to_upsert: dict[str, PassageModel] = {}
        batches_to_upsert: dict[str, dict[str, Any]] = {}

        for q in questions:
            q.updated_at = now_iso

            # Aggregate passages
            if (
                q.passage_id
                and q.stimulus_text
                and q.stimulus_text.strip()
                and q.passage_id not in passages_to_upsert
            ):
                passages_to_upsert[q.passage_id] = PassageModel(
                    id=q.passage_id,
                    title=f"{q.subtopic or q.section} Passage",
                    text=q.stimulus_text.strip(),
                    word_count=len(q.stimulus_text.split()),
                    section=q.section,
                    subtopic=q.subtopic,
                    image_url=q.image_url,
                    image_svg=q.image_svg,
                    image_description=q.image_description,
                    created_at=to_datetime(q.created_at),
                    updated_at=now_dt,
                )

            # Aggregate batches
            if q.batch_id:
                if q.batch_id not in batches_to_upsert:
                    batches_to_upsert[q.batch_id] = {
                        "section": q.section,
                        "subtopic": q.subtopic,
                        "difficulty": q.difficulty,
                        "passage_mode": q.passage_mode,
                        "count": 0,
                        "tokens": 0,
                        "cost": 0.0,
                        "created_at": to_datetime(q.created_at),
                    }
                b_info = batches_to_upsert[q.batch_id]
                b_info["count"] += 1
                b_info["tokens"] += q.total_tokens or 0
                b_info["cost"] += q.cost_usd or 0.0

        # Upsert passages
        for pid, p_mod in passages_to_upsert.items():
            existing_p = await session.get(PassageModel, pid)
            if not existing_p:
                session.add(p_mod)
            else:
                existing_p.text = p_mod.text
                existing_p.word_count = p_mod.word_count
                if p_mod.image_svg and not existing_p.image_svg:
                    existing_p.image_svg = p_mod.image_svg
                if p_mod.image_url and not existing_p.image_url:
                    existing_p.image_url = p_mod.image_url
                if p_mod.image_description and not existing_p.image_description:
                    existing_p.image_description = p_mod.image_description
                existing_p.updated_at = now_dt

        # Upsert batches (create batch record if it doesn't exist, leave existing batch aggregates intact to avoid double-counting)
        for bid, b_info in batches_to_upsert.items():
            existing_b = await session.get(GenerationBatchModel, bid)
            if not existing_b:
                b_model = GenerationBatchModel(
                    id=bid,
                    section=b_info["section"],
                    subtopic=b_info["subtopic"],
                    difficulty=b_info["difficulty"],
                    passage_mode=b_info["passage_mode"],
                    target_count=b_info["count"],
                    actual_count=b_info["count"],
                    total_tokens=b_info["tokens"],
                    cost_usd=b_info["cost"],
                    status="completed",
                    created_at=b_info["created_at"],
                    updated_at=now_dt,
                )
                session.add(b_model)
            else:
                existing_b.updated_at = now_dt

        # Upsert questions
        for q in questions:
            model = _schema_to_model(q)
            await session.merge(model)
            saved_ids.append(q.id)

        await session.commit()

    return saved_ids


async def get_repository_metrics(status: str | None = None) -> dict[str, Any]:
    """Computes repository-wide metrics via native SQL aggregation with zero Python memory overhead."""
    async with async_session_factory() as session:
        stmt = select(
            func.count(QuestionModel.id).label("total_count"),
            func.coalesce(func.sum(QuestionModel.total_tokens), 0).label("total_tokens"),
            func.coalesce(func.sum(QuestionModel.cost_usd), 0.0).label("total_cost_usd"),
        ).where(QuestionModel.is_deleted.is_(False))
        if status and status != "all":
            stmt = stmt.where(QuestionModel.status == status)
        res = await session.execute(stmt)
        row = res.one()
        return {
            "total_count": int(row.total_count),
            "total_tokens": int(row.total_tokens),
            "total_cost_usd": round(float(row.total_cost_usd), 5),
        }


async def get_questions(
    section: str | None = None,
    difficulty: str | None = None,
    search: str | None = None,
    combination_id: str | None = None,
    run_id: str | None = None,
    batch_id: str | None = None,
    job_id: str | None = None,
    passage_id: str | None = None,
    status: str | None = None,
    limit: int | None = None,
    offset: int | None = 0,
    slim: bool = False,
    include_deleted: bool = False,
) -> list[Question]:
    """Retrieves questions from PostgreSQL with optional filtering, hybrid full-text search, pagination, and slim payload projection."""
    async with async_session_factory() as session:
        stmt = select(QuestionModel)

        if not include_deleted:
            stmt = stmt.where(QuestionModel.is_deleted.is_(False))

        if section:
            stmt = stmt.where(QuestionModel.section == section)
        if difficulty:
            diff_lower = difficulty.strip().lower()
            if diff_lower in ["low", "easy"]:
                stmt = stmt.where(QuestionModel.difficulty.in_(["low", "Low", "easy", "Easy"]))
            elif diff_lower in ["high", "hard"]:
                stmt = stmt.where(QuestionModel.difficulty.in_(["high", "High", "hard", "Hard"]))
            elif diff_lower in ["medium", "standard"]:
                stmt = stmt.where(
                    QuestionModel.difficulty.in_(["medium", "Medium", "standard", "Standard"])
                )
            else:
                stmt = stmt.where(QuestionModel.difficulty == difficulty)
        if combination_id:
            stmt = stmt.where(QuestionModel.combination_id == combination_id)
        if run_id:
            stmt = stmt.where(QuestionModel.run_id == run_id)
        if batch_id:
            stmt = stmt.where(QuestionModel.batch_id == batch_id)
        if job_id:
            stmt = stmt.where(QuestionModel.job_id == job_id)
        if passage_id:
            stmt = stmt.where(QuestionModel.passage_id == passage_id)
        if status and status != "all":
            stmt = stmt.where(QuestionModel.status == status)
            if status == "ai_validated":
                stmt = stmt.where(QuestionModel.final_score > 90)
                # Strictly withhold questions whose parent batch is actively in progress
                in_progress_batches = select(GenerationBatchModel.id).where(
                    GenerationBatchModel.status == "in_progress"
                )
                stmt = stmt.where(
                    or_(
                        QuestionModel.batch_id.is_(None),
                        QuestionModel.batch_id.notin_(in_progress_batches),
                    )
                )

        if search:
            search_clean = search.strip()
            wildcard = f"%{search_clean}%"

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

            stmt = stmt.where(
                or_(
                    fts_condition,
                    QuestionModel.id.ilike(wildcard),
                    QuestionModel.question_stem.ilike(wildcard),
                    QuestionModel.stimulus_text.ilike(wildcard),
                    QuestionModel.subtopic.ilike(wildcard),
                    QuestionModel.explanation.ilike(wildcard),
                    QuestionModel.combination_id.ilike(wildcard),
                    QuestionModel.content_domain.ilike(wildcard),
                    QuestionModel.run_id.ilike(wildcard),
                    QuestionModel.batch_id.ilike(wildcard),
                    QuestionModel.passage_id.ilike(wildcard),
                )
            )

        stmt = stmt.order_by(QuestionModel.created_at.desc())
        if offset and offset > 0:
            stmt = stmt.offset(offset)
        if limit and limit > 0:
            stmt = stmt.limit(limit)
        result = await session.execute(stmt)
        models = result.scalars().all()
        return [_model_to_schema(m, slim=slim) for m in models]


async def get_question_by_id(question_id: str, include_deleted: bool = False) -> Question | None:
    """Retrieves a single question by primary key ID."""
    async with async_session_factory() as session:
        stmt = select(QuestionModel).where(QuestionModel.id == question_id)
        if not include_deleted:
            stmt = stmt.where(QuestionModel.is_deleted.is_(False))
        res = await session.execute(stmt)
        model = res.scalar_one_or_none()
        if not model:
            return None
        return _model_to_schema(model)


async def delete_question(question_id: str) -> bool:
    """Soft-deletes a question by primary key ID, preserving it for batch progress."""
    now_dt = datetime.now(UTC)
    async with async_session_factory() as session:
        stmt = (
            update(QuestionModel)
            .where(QuestionModel.id == question_id)
            .values(is_deleted=True, deleted_at=now_dt)
        )
        res = await session.execute(stmt)
        await session.commit()
        return bool(res.rowcount and res.rowcount > 0)


async def delete_questions_batch(question_ids: list[str]) -> int:
    """Soft-deletes multiple questions by primary key IDs in a single atomic SQL transaction, preserving them for batch progress."""
    if not question_ids:
        return 0
    now_dt = datetime.now(UTC)
    async with async_session_factory() as session:
        stmt = (
            update(QuestionModel)
            .where(QuestionModel.id.in_(question_ids))
            .values(is_deleted=True, deleted_at=now_dt)
        )
        result = await session.execute(stmt)
        await session.commit()
    return result.rowcount or 0


async def hard_delete_questions_batch(question_ids: list[str]) -> int:
    """Permanently purges questions by primary key IDs from the database (used for duplicate resolution and trimming excess buffer)."""
    if not question_ids:
        return 0
    async with async_session_factory() as session:
        stmt = delete(QuestionModel).where(QuestionModel.id.in_(question_ids))
        result = await session.execute(stmt)
        await session.commit()
    return result.rowcount or 0


async def hard_delete_question(question_id: str) -> bool:
    """Permanently purges a single question by ID from the database."""
    if not question_id:
        return False
    async with async_session_factory() as session:
        stmt = delete(QuestionModel).where(QuestionModel.id == question_id)
        result = await session.execute(stmt)
        await session.commit()
    return bool(result.rowcount and result.rowcount > 0)


async def restore_question(question_id: str) -> Question | None:
    """Restores a soft-deleted question back to active status, and restores its passage if soft-deleted."""
    now_dt = datetime.now(UTC)
    async with async_session_factory() as session:
        stmt = select(QuestionModel).where(QuestionModel.id == question_id)
        res = await session.execute(stmt)
        q = res.scalar_one_or_none()
        if not q:
            return None
        q.is_deleted = False
        q.deleted_at = None
        q.updated_at = now_dt

        # If question has a linked passage that was soft-deleted, restore the passage too
        if q.passage_id:
            p_stmt = (
                update(PassageModel)
                .where(PassageModel.id == q.passage_id)
                .values(is_deleted=False, deleted_at=None)
            )
            await session.execute(p_stmt)

        await session.commit()
        return _model_to_schema(q)


async def update_question_status(question_id: str, status: str) -> bool:
    """Updates the lifecycle status of a single question."""
    now_dt = datetime.now(UTC)
    async with async_session_factory() as session:
        stmt = select(QuestionModel).where(QuestionModel.id == question_id)
        res = await session.execute(stmt)
        q = res.scalar_one_or_none()
        if not q:
            return False
        q.status = status
        if status in ("in_bank", "ai_validated", "batch_only"):
            q.is_deleted = False
            q.deleted_at = None
        q.updated_at = now_dt
        await session.commit()
        return True


async def batch_update_question_status(question_ids: list[str], status: str) -> int:
    """Updates the lifecycle status of multiple questions in a single atomic transaction."""
    if not question_ids:
        return 0
    now_dt = datetime.now(UTC)
    async with async_session_factory() as session:
        update_vals: dict[str, Any] = {"status": status, "updated_at": now_dt}
        if status in ("in_bank", "ai_validated", "batch_only"):
            update_vals["is_deleted"] = False
            update_vals["deleted_at"] = None

        stmt = update(QuestionModel).where(QuestionModel.id.in_(question_ids)).values(**update_vals)
        result = await session.execute(stmt)
        await session.commit()
        return result.rowcount or 0


async def get_question_status_counts() -> dict[str, int]:
    """Returns counts of questions grouped by lifecycle status."""
    async with async_session_factory() as session:
        in_progress_batches = select(GenerationBatchModel.id).where(
            GenerationBatchModel.status == "in_progress"
        )
        stmt = (
            select(QuestionModel.status, func.count(QuestionModel.id))
            .where(
                QuestionModel.is_deleted.is_(False),
                or_(
                    QuestionModel.status != "ai_validated",
                    and_(
                        QuestionModel.status == "ai_validated",
                        QuestionModel.final_score > 90,
                        or_(
                            QuestionModel.batch_id.is_(None),
                            QuestionModel.batch_id.notin_(in_progress_batches),
                        ),
                    ),
                ),
            )
            .group_by(QuestionModel.status)
        )
        res = await session.execute(stmt)
        counts = {row[0] or "in_bank": row[1] for row in res.all()}

        del_stmt = select(func.count(QuestionModel.id)).where(QuestionModel.is_deleted.is_(True))
        deleted_count = (await session.execute(del_stmt)).scalar() or 0

        return {
            "ai_validated": counts.get("ai_validated", 0),
            "in_bank": counts.get("in_bank", 0),
            "discarded": counts.get("discarded", 0),
            "below_threshold": counts.get("below_threshold", 0),
            "batch_only": counts.get("batch_only", 0),
            "deleted": deleted_count,
            "total": sum(counts.values()),
        }


async def get_subtopic_reference_questions(
    section: str,
    subtopic: str | None = None,
    limit: int = 50,
) -> list[Question]:
    """
    Retrieves recent questions from the question bank matching the section and subtopic
    to serve as the collision reference pool for deduplication.
    """
    async with async_session_factory() as session:
        stmt = select(QuestionModel).where(
            QuestionModel.is_deleted.is_(False),
            QuestionModel.status.in_(["in_bank", "ai_validated", "approved"]),
        )
        if section:
            sec_val = section.value if hasattr(section, "value") else str(section)
            stmt = stmt.where(
                or_(
                    QuestionModel.section == sec_val,
                    QuestionModel.section_label.ilike(f"%{sec_val}%"),
                )
            )
        if subtopic and subtopic.strip():
            sub_val = subtopic.strip()
            stmt = stmt.where(
                or_(
                    QuestionModel.subtopic == sub_val,
                    QuestionModel.subtopic.ilike(f"%{sub_val}%"),
                )
            )

        stmt = stmt.order_by(QuestionModel.created_at.desc()).limit(limit)
        result = await session.execute(stmt)
        models = result.scalars().all()
        return [_model_to_schema(m) for m in models]


async def override_question_duplicate(question_id: str) -> Question | None:
    """Marks a question's duplicate alert as manually overridden and approved in the database."""
    now_iso = datetime.now(UTC).isoformat()
    now_dt = datetime.now(UTC)
    async with async_session_factory() as session:
        model = await session.get(QuestionModel, question_id)
        if not model:
            return None
        model.is_duplicate_override = True
        dup_dict = dict(model.duplicate_info or {})
        dup_dict["is_overridden"] = True
        dup_dict["overridden_at"] = now_iso
        model.duplicate_info = dup_dict
        model.status = "in_bank"
        model.updated_at = now_dt
        await session.commit()
        await session.refresh(model)
        return _model_to_schema(model)


__all__ = [
    "batch_update_question_status",
    "delete_question",
    "delete_questions_batch",
    "get_question_by_id",
    "get_question_status_counts",
    "get_questions",
    "get_repository_metrics",
    "get_subtopic_reference_questions",
    "hard_delete_question",
    "hard_delete_questions_batch",
    "override_question_duplicate",
    "restore_question",
    "save_question",
    "save_questions_batch",
    "update_question_status",
]
