"""
syllabus_ingestion.py - Document and syllabus ingestion service for AAMC MCAT taxonomy mapping.

Extracts text from syllabi, lecture notes, and curriculum documents (PDF, TXT, MD),
analyzes academic content against official AAMC Foundational Concepts and Subtopics,
and synthesizes optimized batch generation proposals with tailored instructions.
"""

from __future__ import annotations

import io
import json
import logging
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from app.agents.base import call_llm, safe_json_loads
from app.core.config import config
from app.schemas.mcat import (
    MCAT_SECTION_LABELS,
    MCAT_SUBTOPICS,
    MCATSection,
)

logger = logging.getLogger(__name__)

TAXONOMY_PATH = Path(__file__).resolve().parent.parent / "data" / "mcat_dependent_taxonomy.json"
_CACHED_TAXONOMY: dict[str, Any] | None = None


def get_taxonomy_data() -> dict[str, Any]:
    """Loads and caches the AAMC taxonomy structure."""
    global _CACHED_TAXONOMY
    if _CACHED_TAXONOMY is None:
        try:
            if TAXONOMY_PATH.exists():
                with open(TAXONOMY_PATH, encoding="utf-8") as f:
                    _CACHED_TAXONOMY = json.load(f)
            else:
                _CACHED_TAXONOMY = {}
        except Exception as exc:
            logger.warning("Failed to load taxonomy from %s: %s", TAXONOMY_PATH, exc)
            _CACHED_TAXONOMY = {}
    return _CACHED_TAXONOMY


@dataclass
class SuggestedBatchProposal:
    thematic_angle: str
    question_count: int = 5
    topic: str | None = None
    subtopic: str | None = None


@dataclass
class SyllabusIngestionResult:
    section: str
    section_name: str
    topic: str
    subtopic: str
    difficulty: str
    confidence: float
    summary: str
    matched_concepts: list[str]
    matched_topics: list[str]
    suggested_batches: list[dict[str, Any]]
    suggested_instructions: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def extract_text_from_file_bytes(
    file_bytes: bytes, filename: str = "", max_chars: int = 30000
) -> str:
    """
    Extracts plain text from document bytes (PDF, plain text, markdown).
    Truncates at max_chars to keep within LLM context budget.
    """
    if not file_bytes:
        return ""

    filename_lower = filename.lower()
    text_content = ""

    # PDF Extraction via pypdf
    if filename_lower.endswith(".pdf") or file_bytes.startswith(b"%PDF"):
        try:
            import pypdf

            reader = pypdf.PdfReader(io.BytesIO(file_bytes))
            pages_text = []
            for i, page in enumerate(reader.pages):
                page_str = page.extract_text() or ""
                if page_str.strip():
                    pages_text.append(f"--- Page {i + 1} ---\n{page_str.strip()}")
                if sum(len(p) for p in pages_text) >= max_chars:
                    break
            text_content = "\n\n".join(pages_text)
        except Exception as exc:
            logger.warning("PDF extraction failed (%s); attempting raw string fallback.", exc)
            text_content = file_bytes.decode("utf-8", errors="ignore")

    # Plain text / Markdown / HTML / JSON fallback
    if not text_content:
        for enc in ("utf-8", "latin-1", "cp1252"):
            try:
                text_content = file_bytes.decode(enc)
                break
            except Exception:
                continue

    text_content = text_content.strip()
    if len(text_content) > max_chars:
        text_content = text_content[:max_chars] + "\n... [Document truncated for analysis]"

    return text_content


def _deterministic_taxonomy_match(text: str) -> SyllabusIngestionResult:
    """
    Deterministic keyword frequency match against MCAT taxonomy for offline mode or test velocity.
    """
    lower = text.lower()

    # Section keyword weights
    scores = {
        MCATSection.BIO_BIOCHEM: sum(
            lower.count(k)
            for k in [
                "protein",
                "amino acid",
                "enzyme",
                "dna",
                "rna",
                "cell",
                "membrane",
                "metabolism",
                "glycolysis",
                "krebs",
                "genetics",
                "biochem",
                "biology",
                "cellular",
                "pathway",
                "organelle",
                "transcription",
                "translation",
            ]
        ),
        MCATSection.CHEM_PHYS: sum(
            lower.count(k)
            for k in [
                "physics",
                "chemistry",
                "mechanics",
                "fluid",
                "dynamics",
                "bernoulli",
                "buoyancy",
                "thermodynamics",
                "kinetics",
                "velocity",
                "force",
                "circuit",
                "current",
                "optics",
                "voltage",
                "acid",
                "base",
                "titration",
                "equilibrium",
                "stoichiometry",
                "reaction",
                "solvent",
                "electrochemistry",
                "work",
                "energy",
                "pressure",
                "gas law",
            ]
        ),
        MCATSection.PSYCH_SOC: sum(
            lower.count(k)
            for k in [
                "psychology",
                "sociology",
                "behavior",
                "cognition",
                "memory",
                "conditioning",
                "social",
                "stratification",
                "demographics",
                "perception",
                "attitude",
                "identity",
                "emotion",
                "stress",
                "neural",
                "brain",
            ]
        ),
        MCATSection.CARS: sum(
            lower.count(k)
            for k in [
                "philosophy",
                "humanities",
                "ethics",
                "rhetoric",
                "author",
                "argument",
                "literary",
                "historian",
                "jurisprudence",
                "aesthetic",
                "critique",
                "passage",
            ]
        ),
    }

    best_sec = max(scores, key=scores.get)
    # Ensure minimum score
    if scores[best_sec] == 0:
        best_sec = MCATSection.BIO_BIOCHEM

    sec_key = best_sec.value
    sec_label = MCAT_SECTION_LABELS[best_sec]
    candidate_subtopics = MCAT_SUBTOPICS.get(best_sec, ["General MCAT Concepts"])

    # Pick best subtopic
    matched_subtopic = candidate_subtopics[0]
    best_sub_count = -1
    for sub in candidate_subtopics:
        c = sum(
            lower.count(token.lower()) for token in sub.replace("(", " ").replace(")", " ").split()
        )
        if c > best_sub_count:
            best_sub_count = c
            matched_subtopic = sub

    # Match topic
    topic = matched_subtopic.split("(")[0].strip() if "(" in matched_subtopic else matched_subtopic

    confidence = min(
        0.98, max(0.65, round(0.50 + (scores[best_sec] / (sum(scores.values()) + 1) * 0.45), 2))
    )

    # Formulate batches
    batches = [
        {
            "thematic_angle": f"Core principles and mechanisms of {topic}",
            "question_count": 5,
            "topic": topic,
            "subtopic": matched_subtopic,
        },
        {
            "thematic_angle": f"Advanced experimental and analytical applications in {topic}",
            "question_count": 5,
            "topic": topic,
            "subtopic": matched_subtopic,
        },
    ]

    return SyllabusIngestionResult(
        section=sec_key,
        section_name=sec_label,
        topic=topic,
        subtopic=matched_subtopic,
        difficulty="medium",
        confidence=confidence,
        summary=f"Curriculum centered on {topic} within {sec_label}.",
        matched_concepts=[f"Foundational Concept: {topic}"],
        matched_topics=[matched_subtopic],
        suggested_batches=batches,
        suggested_instructions=(
            f"Focus on high-yield AAMC testing objectives for {topic}. "
            "Prioritize multi-step experimental problem solving and data analysis."
        ),
    )


async def ingest_and_map_syllabus(text_content: str, title: str | None = None) -> dict[str, Any]:
    """
    Analyzes document text, mapping it to official AAMC MCAT sections, topics,
    subtopics, and generates an optimized batch generation plan.
    """
    clean_text = text_content.strip()
    if not clean_text:
        return _deterministic_taxonomy_match("biochemistry cellular enzymes").to_dict()

    if config.OFFLINE_MODE:
        return _deterministic_taxonomy_match(clean_text).to_dict()

    system_prompt = (
        "You are an expert AAMC MCAT Curriculum Director and Psychometrician. "
        "Your task is to analyze an uploaded syllabus, lecture outline, or study guide, "
        "map its content to the official AAMC MCAT Content Outline, and propose an optimal "
        "question generation plan."
    )

    user_prompt = f"""
Analyze the following course syllabus / educational document:
Document Title: {title or "Uploaded Syllabus"}

DOCUMENT TEXT:
\"\"\"
{clean_text[:12000]}
\"\"\"

AAMC SECTIONS:
- chem_phys: Chemical and Physical Foundations of Biological Systems
- bio_biochem: Biological and Biochemical Foundations of Living Systems
- psych_soc: Psychological, Social, and Biological Foundations of Behavior
- cars: Critical Analysis and Reasoning Skills

Return ONLY a valid JSON object matching this schema:
{{
  "section": "chem_phys" | "bio_biochem" | "psych_soc" | "cars",
  "section_name": "Full section name",
  "topic": "Primary MCAT Topic name (e.g. Enzyme Kinetics, Thermodynamics, Neurological Foundations)",
  "subtopic": "Specific MCAT subtopic or learning objective",
  "difficulty": "medium" | "high" | "low",
  "confidence": 0.85 to 0.99 (float),
  "summary": "1-2 sentence overview of the syllabus emphasis",
  "matched_concepts": ["Concept 1", "Concept 2"],
  "matched_topics": ["Topic 1", "Topic 2", "Topic 3"],
  "suggested_batches": [
    {{
      "thematic_angle": "Specific research or experimental scenario 1",
      "question_count": 5
    }},
    {{
      "thematic_angle": "Specific research or experimental scenario 2",
      "question_count": 5
    }}
  ],
  "suggested_instructions": "2-3 sentences of authentic educator guidance for the AI question writer"
}}
"""

    try:
        raw_output, _ = await call_llm(
            prompt=user_prompt,
            system_prompt=system_prompt,
            model=config.DEFAULT_TEXT_MODEL,
            temperature=0.2,
            max_tokens=2048,
        )
        parsed = safe_json_loads(raw_output)
        if isinstance(parsed, dict) and "section" in parsed and "topic" in parsed:
            # Validate section
            sec_val = str(parsed["section"]).lower().strip()
            valid_secs = {s.value: s for s in MCATSection}
            if sec_val not in valid_secs:
                sec_val = MCATSection.BIO_BIOCHEM.value

            return {
                "section": sec_val,
                "section_name": MCAT_SECTION_LABELS[valid_secs[sec_val]],
                "topic": str(parsed.get("topic", "General Topic")).strip(),
                "subtopic": str(parsed.get("subtopic", "")).strip()
                or str(parsed.get("topic", "")).strip(),
                "difficulty": str(parsed.get("difficulty", "medium")).lower(),
                "confidence": float(parsed.get("confidence", 0.90)),
                "summary": str(parsed.get("summary", "")).strip(),
                "matched_concepts": list(parsed.get("matched_concepts", [])),
                "matched_topics": list(parsed.get("matched_topics", [])),
                "suggested_batches": list(parsed.get("suggested_batches", [])),
                "suggested_instructions": str(parsed.get("suggested_instructions", "")).strip(),
            }
    except Exception as exc:
        logger.warning("LLM syllabus ingestion failed (%s); using deterministic parser.", exc)

    return _deterministic_taxonomy_match(clean_text).to_dict()
