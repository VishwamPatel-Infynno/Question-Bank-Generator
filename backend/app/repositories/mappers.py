from __future__ import annotations

from datetime import UTC, datetime

from app.db.base import to_datetime, to_iso_str
from app.models.passage import PassageModel
from app.models.question import QuestionModel
from app.schemas.question import (
    DuplicateInfo,
    OptionChoice,
    Passage,
    Question,
    ReviewScore,
)


def model_to_schema(m: QuestionModel, slim: bool = False) -> Question:
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
        visual_medical_category=getattr(m, "visual_medical_category", None),
        visual_clinical_description=getattr(m, "visual_clinical_description", None),
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
        embedding=getattr(m, "embedding", None),
    )


def schema_to_model(q: Question) -> QuestionModel:
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
        visual_medical_category=getattr(q, "visual_medical_category", None),
        visual_clinical_description=getattr(q, "visual_clinical_description", None),
        mcat_scaled_score=q.mcat_scaled_score,
        aamc_skill=q.aamc_skill,
        subject=q.subject,
        unit=q.unit,
        topic=q.topic,
        subskill=q.subskill,
        likely_mistake_pattern=q.likely_mistake_pattern,
        duplicate_info=dup_data,
        is_duplicate_override=q.is_duplicate_override,
        is_deleted=bool(q.is_deleted),
        deleted_at=to_datetime(q.deleted_at) if q.deleted_at else None,
        stage_outcomes=q.stage_outcomes,
        embedding=getattr(q, "embedding", None),
    )


def passage_model_to_schema(m: PassageModel, question_count: int = 0) -> Passage:
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


def passage_schema_to_model(p: Passage) -> PassageModel:
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
