"""
ai.py - AI-Native interactive copilot endpoints for editorial and study tools.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.api.security import limit_generation_requests
from app.services.ai_copilot import (
    audit_passage,
    enhance_instructions,
    refine_question,
    synthesize_study_guide,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ai", tags=["AI Copilot"])


class EnhanceInstructionsRequest(BaseModel):
    instructions: str = Field(
        ..., min_length=1, max_length=3000, description="Raw educator instructions to enhance"
    )
    section: str = Field(..., description="MCAT section e.g. bio_biochem, cars")
    topic: str | None = Field(None, max_length=200)
    difficulty: str | None = Field(None, max_length=50)


class RefineQuestionRequest(BaseModel):
    question: dict[str, Any] = Field(..., description="Full question dictionary")
    instruction: str = Field(
        ..., min_length=2, max_length=1000, description="Editorial instruction"
    )
    action: str = Field(
        "custom",
        description="Action type: polish_distractor, simplify_explanation, invert_sibling, custom",
    )


class AuditPassageRequest(BaseModel):
    passage_text: str = Field(
        ..., min_length=10, max_length=25000, description="Reading passage text to analyze"
    )


class StudyGuideRequest(BaseModel):
    questions: list[dict[str, Any]] = Field(
        ..., min_length=1, max_length=100, description="List of questions to synthesize"
    )


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

