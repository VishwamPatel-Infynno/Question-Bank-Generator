"""
ai.py - AI-Native interactive copilot endpoints for editorial and study tools.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator

from app.api.security import limit_generation_requests
from app.services.ai_copilot import (
    audit_passage,
    enhance_instructions,
    refine_question,
    synthesize_study_guide,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ai", tags=["AI Copilot"])

# Free-form question dicts go straight into LLM prompts: bound what one request can make us pay for
MAX_QUESTION_JSON_CHARS = 50_000
MAX_STUDY_GUIDE_JSON_CHARS = 300_000


def _json_size(value: Any) -> int:
    try:
        return len(json.dumps(value, default=str))
    except (TypeError, ValueError):  # circular or otherwise unserializable: treat as oversized
        return MAX_STUDY_GUIDE_JSON_CHARS + 1


class EnhanceInstructionsRequest(BaseModel):
    instructions: str = Field(
        ..., min_length=1, max_length=3000, description="Raw educator instructions to enhance"
    )
    section: str = Field(..., max_length=100, description="MCAT section e.g. bio_biochem, cars")
    topic: str | None = Field(None, max_length=200)
    difficulty: str | None = Field(None, max_length=50)


class RefineQuestionRequest(BaseModel):
    question: dict[str, Any] = Field(..., description="Full question dictionary")
    instruction: str = Field(
        ..., min_length=2, max_length=1000, description="Editorial instruction"
    )
    action: str = Field(
        "custom",
        max_length=50,
        description="Action type: polish_distractor, simplify_explanation, invert_sibling, custom",
    )

    @field_validator("question")
    @classmethod
    def _cap_question_size(cls, value: dict[str, Any]) -> dict[str, Any]:
        if _json_size(value) > MAX_QUESTION_JSON_CHARS:
            raise ValueError(
                f"question must serialize to at most {MAX_QUESTION_JSON_CHARS} characters."
            )
        return value


class AuditPassageRequest(BaseModel):
    passage_text: str = Field(
        ..., min_length=10, max_length=25000, description="Reading passage text to analyze"
    )


class StudyGuideRequest(BaseModel):
    questions: list[dict[str, Any]] = Field(
        ..., min_length=1, max_length=100, description="List of questions to synthesize"
    )

    @field_validator("questions")
    @classmethod
    def _cap_questions_size(cls, value: list[dict[str, Any]]) -> list[dict[str, Any]]:
        if any(_json_size(q) > MAX_QUESTION_JSON_CHARS for q in value):
            raise ValueError(
                f"each question must serialize to at most {MAX_QUESTION_JSON_CHARS} characters."
            )
        if _json_size(value) > MAX_STUDY_GUIDE_JSON_CHARS:
            raise ValueError(
                f"questions must serialize to at most {MAX_STUDY_GUIDE_JSON_CHARS} characters in total."
            )
        return value


@router.post("/enhance-instructions", dependencies=[Depends(limit_generation_requests)])
async def endpoint_enhance_instructions(req: EnhanceInstructionsRequest) -> dict[str, Any]:
    """Enhances raw educator notes into an authentic AAMC prompt mandate."""
    try:
        enhanced = await enhance_instructions(
            instructions=req.instructions,
            section=req.section,
            topic=req.topic,
            difficulty=req.difficulty,
        )
    except Exception as exc:
        logger.error("Enhance instructions failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to enhance instructions.") from exc
    else:
        return {"enhanced_instructions": enhanced}


@router.post("/refine-question", dependencies=[Depends(limit_generation_requests)])
async def endpoint_refine_question(req: RefineQuestionRequest) -> dict[str, Any]:
    """Applies interactive AI refinement to a question."""
    try:
        refined = await refine_question(
            question_data=req.question,
            instruction=req.instruction,
            action=req.action,
        )
    except Exception as exc:
        logger.error("Question refinement failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to refine question.") from exc
    else:
        return {"question": refined}


@router.post("/audit-passage")
async def endpoint_audit_passage(req: AuditPassageRequest) -> dict[str, Any]:
    """Audits reading passage for readability grade level, empirical density, and AAMC alignment."""
    try:
        return audit_passage(req.passage_text)
    except Exception as exc:
        logger.error("Passage audit failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to audit passage.") from exc


@router.post("/study-guide", dependencies=[Depends(limit_generation_requests)])
async def endpoint_study_guide(req: StudyGuideRequest) -> dict[str, Any]:
    """Synthesizes selected questions into a high-yield study guide and flashcards."""
    try:
        return await synthesize_study_guide(req.questions)
    except Exception as exc:
        logger.error("Study guide synthesis failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to synthesize study guide.") from exc
