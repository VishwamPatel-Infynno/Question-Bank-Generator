"""
ai.py - AI-Native interactive copilot endpoints for onboarding, editorial, and study tools.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from pydantic import BaseModel, Field

from app.api.security import limit_generation_requests
from app.services.ai_copilot import (
    audit_passage,
    enhance_instructions,
    parse_magic_setup,
    refine_question,
    synthesize_study_guide,
)
from app.services.syllabus_ingestion import (
    extract_text_from_file_bytes,
    ingest_and_map_syllabus,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ai", tags=["AI Copilot"])


class MagicSetupRequest(BaseModel):
    prompt: str = Field(
        ...,
        min_length=2,
        max_length=2000,
        description="Natural language description of desired question set",
    )


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


class SyllabusTextRequest(BaseModel):
    content: str = Field(
        ..., min_length=10, max_length=50000, description="Syllabus text or learning objectives"
    )
    title: str | None = Field(None, max_length=200, description="Optional document title")


@router.post("/magic-setup", dependencies=[Depends(limit_generation_requests)])
async def endpoint_magic_setup(req: MagicSetupRequest) -> dict[str, Any]:
    """Parses natural language prompt into pre-filled wizard configuration."""
    try:
        return await parse_magic_setup(req.prompt)
    except Exception as exc:
        logger.error("Magic setup failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to parse magic setup prompt.") from exc


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
        return {"enhanced_instructions": enhanced}
    except Exception as exc:
        logger.error("Enhance instructions failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to enhance instructions.") from exc


@router.post("/refine-question", dependencies=[Depends(limit_generation_requests)])
async def endpoint_refine_question(req: RefineQuestionRequest) -> dict[str, Any]:
    """Applies interactive AI refinement to a question."""
    try:
        refined = await refine_question(
            question_data=req.question,
            instruction=req.instruction,
            action=req.action,
        )
        return {"question": refined}
    except Exception as exc:
        logger.error("Question refinement failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to refine question.") from exc


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


@router.post("/ingest-syllabus", dependencies=[Depends(limit_generation_requests)])
async def endpoint_ingest_syllabus(req: SyllabusTextRequest) -> dict[str, Any]:
    """
    Ingests syllabus text or learning objectives, maps to AAMC MCAT taxonomy,
    and proposes an optimized batch generation plan.
    """
    try:
        return await ingest_and_map_syllabus(req.content, title=req.title)
    except Exception as exc:
        logger.error("Syllabus ingestion failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to ingest syllabus.") from exc


@router.post("/ingest-syllabus-file", dependencies=[Depends(limit_generation_requests)])
async def endpoint_ingest_syllabus_file(
    file: UploadFile,
) -> dict[str, Any]:
    """
    Ingests an uploaded syllabus file (PDF, TXT, MD), extracts plain text,
    and maps content to AAMC MCAT taxonomy with a batch generation proposal.
    """
    try:
        content_bytes = await file.read()
        extracted_text = extract_text_from_file_bytes(content_bytes, filename=file.filename or "")
        if not extracted_text.strip():
            raise HTTPException(
                status_code=400,
                detail="Unable to extract text from the uploaded file. Please verify file format.",
            )
        return await ingest_and_map_syllabus(extracted_text, title=file.filename)
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Syllabus file ingestion failed: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=500, detail="Failed to process uploaded syllabus file."
        ) from exc
