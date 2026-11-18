"""
csv_export.py - CSV serialization and formatting helpers for Question Bank records.

Provides column header definitions, row builders, and in-memory CSV generation for
MCAT questions, accommodating psychometric scores, image references, and AAMC metadata.
"""

from __future__ import annotations

import csv
import io
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from app.schemas import Question


def build_csv_headers() -> list[str]:
    """Returns column header labels for Question Bank CSV export."""
    return [
        "ID",
        "Run_ID",
        "Batch_ID",
        "Combination_ID",
        "Section",
        "Subcategory",
        "Difficulty",
        "MCAT_Scaled_Score",
        "AAMC_Skill",
        "Content_Domain",
        "Question_Type",
        "Interaction_Type",
        "Primary_Trap",
        "Passage_Required",
        "Visual_Type",
        "Image_URL",
        "Image_Description",
        "Stimulus",
        "Question Stem",
        "Option A",
        "Option B",
        "Option C",
        "Option D",
        "Correct Answer",
        "Explanation",
        "Final Score",
        "Cycles",
        "Created At",
    ]


def build_csv_row(q: Question) -> list[Any]:
    """Constructs a single CSV export row for a Question schema record."""
    opts = {opt.id: opt.text for opt in q.options}
    if q.image_url:
        img_val = f"/api/questions/{q.id}/image" if q.image_url.startswith("data:") else q.image_url
    elif q.image_svg:
        img_val = f"/api/questions/{q.id}/image"
    else:
        img_val = ""

    return [
        q.id,
        q.run_id or "",
        q.batch_id or "",
        q.combination_id or "",
        q.section_label,
        q.subtopic,
        q.difficulty,
        q.mcat_scaled_score or "",
        q.aamc_skill or "",
        q.content_domain or "",
        q.question_type or "",
        q.interaction_type or "single_choice",
        q.primary_trap or "",
        q.passage_required or "",
        q.visual_type or "None",
        img_val,
        q.image_description or "",
        q.stimulus_text or "",
        q.question_stem,
        opts.get("A", ""),
        opts.get("B", ""),
        opts.get("C", ""),
        opts.get("D", ""),
        q.correct_answer_id,
        q.explanation,
        q.final_score,
        q.iteration_count,
        q.created_at,
    ]


def generate_questions_csv(questions: list[Question]) -> str:
    """Generates an RFC 4180 compliant CSV string from an array of Question models."""
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(build_csv_headers())
    for q in questions:
        writer.writerow(build_csv_row(q))
    return output.getvalue()
