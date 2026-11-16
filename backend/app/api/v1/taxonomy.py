from __future__ import annotations

import hashlib
import json
import logging
from typing import Any

from fastapi import APIRouter, Request, Response

from app.schemas import (
    AAMC_REASONING_SKILLS,
    CONTENT_DOMAINS_DETAILED,
    DEPENDENT_TAXONOMY,
    MCAT_PACING,
    MCAT_SECTION_CODES,
    MCAT_SECTION_LABELS,
    MCAT_SUBTOPICS,
    PRIMARY_TRAPS_DETAILED,
    QUESTION_TYPES_DETAILED,
    TAXONOMY_SKILLS,
    MCATSection,
    get_section_tree,
    get_skills_for_section,
    get_taxonomy_data,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["AAMC Taxonomy & Syllabus"])


def _build_rich_sections_payload():
    sections_list = []
    for sec in MCATSection:
        code = MCAT_SECTION_CODES[sec]
        tree = get_section_tree(sec)
        subjects = tree.get("subjects", []) if tree else []
        # Flatten subtopics across all topics for fast section-level lookups and UI filters
        all_subtopics = []
        for subj in subjects:
            for unit in subj.get("units", []):
                for topic in unit.get("topics", []):
                    all_subtopics.extend(topic.get("subtopics", []))

        subtopics = all_subtopics if all_subtopics else MCAT_SUBTOPICS.get(sec, [])

        sections_list.append(
            {
                "id": sec.value,
                "code": code,
                "label": MCAT_SECTION_LABELS[sec],
                "pacing": MCAT_PACING[sec],
                "subtopics": subtopics,
                "subjects": subjects,
                "skills": get_skills_for_section(sec),
            }
        )

    return {
        "exam": "MCAT",
        "exam_full_name": "Medical College Admission Test (AAMC)",
        "selection_flow": DEPENDENT_TAXONOMY.get(
            "selection_flow",
            ["section", "subject", "unit", "topic", "subtopic", "skill", "subskill"],
        ),
        "sections": sections_list,
        "skills": TAXONOMY_SKILLS,
        "aamc_skills": AAMC_REASONING_SKILLS,
        "generation_options": {
            "difficulty": DEPENDENT_TAXONOMY.get("generation_options", {}).get("difficulty", []),
            "question_type": QUESTION_TYPES_DETAILED,
            "content_domain": CONTENT_DOMAINS_DETAILED,
            "primary_trap": PRIMARY_TRAPS_DETAILED,
            "likely_mistake_pattern": DEPENDENT_TAXONOMY.get("generation_options", {}).get(
                "likely_mistake_pattern", {}
            ),
            "number_of_questions": DEPENDENT_TAXONOMY.get("generation_options", {}).get(
                "number_of_questions", {"default": 5, "minimum": 1, "maximum": 10}
            ),
        },
        "generation_form_fields": DEPENDENT_TAXONOMY.get("generation_form_fields", []),
    }


_CACHED_SECTIONS_PAYLOAD = _build_rich_sections_payload()
_SECTIONS_JSON = json.dumps(_CACHED_SECTIONS_PAYLOAD, sort_keys=True)
_SECTIONS_ETAG = f'"{hashlib.sha256(_SECTIONS_JSON.encode("utf-8")).hexdigest()[:16]}"'

_CACHED_TAXONOMY_PAYLOAD = get_taxonomy_data()
_TAXONOMY_JSON = json.dumps(_CACHED_TAXONOMY_PAYLOAD, sort_keys=True)
_TAXONOMY_ETAG = f'"{hashlib.sha256(_TAXONOMY_JSON.encode("utf-8")).hexdigest()[:16]}"'

_TAXONOMY_CACHE_CONTROL = "public, max-age=3600, stale-while-revalidate=300"


def _matches_etag(client_etag: str | None, server_etag: str) -> bool:
    if not client_etag:
        return False
    if client_etag.strip() == "*":
        return True
    clean_server = server_etag.strip().removeprefix("W/").strip('"')
    tags = [t.strip().removeprefix("W/").strip('"') for t in client_etag.split(",")]
    return clean_server in tags


_DEFAULT_REQUEST: Any = None
_DEFAULT_RESPONSE: Any = None


@router.get("/sections", response_model=None)
async def get_sections(
    request: Request = _DEFAULT_REQUEST,
    response: Response = _DEFAULT_RESPONSE,
) -> Response | dict[str, Any]:
    """Returns official AAMC MCAT sections and their categorized subtopics (in-memory pre-cached)."""
    if request is not None and _matches_etag(request.headers.get("if-none-match"), _SECTIONS_ETAG):
        return Response(
            status_code=304,
            headers={"ETag": _SECTIONS_ETAG, "Cache-Control": _TAXONOMY_CACHE_CONTROL},
        )
    if response is not None:
        response.headers["Cache-Control"] = _TAXONOMY_CACHE_CONTROL
        response.headers["ETag"] = _SECTIONS_ETAG
    return _CACHED_SECTIONS_PAYLOAD


@router.get("/taxonomy", response_model=None)
async def get_taxonomy(
    request: Request = _DEFAULT_REQUEST,
    response: Response = _DEFAULT_RESPONSE,
) -> Response | dict[str, Any]:
    """Returns the official manager-provided MCAT Dependent Taxonomy."""
    if request is not None and _matches_etag(request.headers.get("if-none-match"), _TAXONOMY_ETAG):
        return Response(
            status_code=304,
            headers={"ETag": _TAXONOMY_ETAG, "Cache-Control": _TAXONOMY_CACHE_CONTROL},
        )
    if response is not None:
        response.headers["Cache-Control"] = _TAXONOMY_CACHE_CONTROL
        response.headers["ETag"] = _TAXONOMY_ETAG
    return _CACHED_TAXONOMY_PAYLOAD
