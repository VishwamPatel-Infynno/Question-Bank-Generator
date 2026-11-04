from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query

from app.repositories import (
    delete_passage,
    get_passage_by_id,
    get_passages,
    get_questions,
    restore_passage,
    save_passage,
)
from app.schemas import Passage

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Passages"])


@router.get("/passages")
async def list_passages(
    section: Annotated[str | None, Query()] = None,
    subtopic: Annotated[str | None, Query()] = None,
    search: Annotated[str | None, Query()] = None,
):
    """Lists reading passages in the question bank."""
    passages = await get_passages(section=section, subtopic=subtopic, search=search)
    return {"passages": [p.model_dump() for p in passages]}


@router.get("/passages/{passage_id}")
async def get_single_passage(passage_id: str):
    """Retrieves a single reading passage with its linked questions."""
    p = await get_passage_by_id(passage_id)
    if not p:
        raise HTTPException(status_code=404, detail="Passage not found")

    linked_questions = await get_questions(passage_id=passage_id)
    return {
        "passage": p.model_dump(),
        "questions": [q.model_dump() for q in linked_questions],
    }


@router.post("/passages")
async def create_or_update_passage(passage: Passage):
    """Admin endpoint to create or update a passage record."""
    saved = await save_passage(passage)
    return {"success": True, "passage": saved.model_dump()}


@router.delete("/passages/{passage_id}")
async def remove_passage(passage_id: str):
    """Admin endpoint to soft-delete a passage record and its associated questions (preserving batch progress)."""
    success, deleted_q_count = await delete_passage(passage_id)
    if not success:
        raise HTTPException(status_code=404, detail="Passage not found")
    return {
        "success": True,
        "deleted_id": passage_id,
        "deleted_questions_count": deleted_q_count,
    }


@router.post("/passages/{passage_id}/restore")
async def restore_single_passage(passage_id: str):
    """Admin endpoint to restore a soft-deleted passage record."""
    success = await restore_passage(passage_id)
    if not success:
        raise HTTPException(status_code=404, detail="Passage not found")
    return {"success": True, "restored_id": passage_id}
