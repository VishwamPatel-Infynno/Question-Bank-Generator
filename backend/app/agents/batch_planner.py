"""
batch_planner.py - Dynamic AI-native batch planning and thematic brainstorming.

Generates syllabus-coherent, distinct pedagogical angles for multi-job batch generation,
eliminating hardcoded modulo arrays. In live mode, uses fast LLM brainstorming; in offline/fallback
mode, derives deterministic topic-tailored angles.
"""

from __future__ import annotations

import logging

from app.agents.base import call_llm, safe_json_loads
from app.core.config import config
from app.schemas import GenerationRequest, enum_value, is_cars

logger = logging.getLogger(__name__)

# In-memory angle cache per batch_id to ensure consistent refill & retry angle assignment
_BATCH_THEMATIC_CACHE: dict[str, list[str]] = {}
_MAX_CACHE_ENTRIES = 500

CARS_PEDAGOGICAL_ASPECTS: list[str] = [
    "Epistemic Justification, Core Thesis & Philosophical Foundations",
    "Methodological Framework, Empirical Support & Textual Evidence",
    "Rhetorical Architecture, Stylistic Metaphors & Authorial Voice",
    "Normative Implications, Ethical Dimensions & Societal Policy",
    "Counter-Arguments, Boundary Conditions & Theoretical Tensions",
    "Historical Contextualization, Historiography & Paradigm Evolution",
    "Hermeneutic Interpretation, Semiotic Analysis & Linguistic Nuance",
    "Institutional Legitimacy, Power Dynamics & Cultural Authority",
    "Aesthetic Representation, Cultural Memory & Critical Theory",
    "Comparative Paradigms & Cross-Disciplinary Extrapolation",
]

SCIENCE_PEDAGOGICAL_ASPECTS: list[str] = [
    "Catalytic Mechanisms, Reaction Kinetics & Rate Determinants",
    "Thermodynamic Stability, Energetic Driving Forces & Equilibrium Shifts",
    "Allosteric & Feedback Regulation in Physiological Milieus",
    "Substrate Specificity, Stereochemistry & Binding Affinity",
    "Downstream Metabolic Flux & Systemic Homeostatic Coupling",
    "Experimental Perturbation: Small-Molecule Inhibition & Mutational Assays",
    "Clinical Pathophysiology & Pharmacological Intervention Points",
    "Cellular Microenvironment: pH, Ionic Gradients & Membrane Dynamics",
    "Transition State Stabilization, Cofactors & Enzymatic Kinetics",
    "Quantitative Analytical Assays, Baseline Calibration & Signal Detection",
]


def _build_deterministic_angles(req: GenerationRequest, count: int) -> list[str]:
    """Generates syllabus-tailored deterministic thematic angles anchored to the requested topic/subtopic."""
    base_topic = (req.subtopic or req.topic or "").strip()
    sec_cars = is_cars(req.section)
    aspects = CARS_PEDAGOGICAL_ASPECTS if sec_cars else SCIENCE_PEDAGOGICAL_ASPECTS

    angles: list[str] = []
    for i in range(count):
        aspect = aspects[i % len(aspects)]
        if base_topic:
            angles.append(f"Set #{i + 1}: {base_topic} — {aspect}")
        else:
            sec_name = enum_value(req.section).replace("_", " ").title()
            angles.append(f"Set #{i + 1}: {sec_name} — {aspect}")
    return angles


async def brainstorm_batch_thematic_angles(
    req: GenerationRequest,
    count: int,
) -> list[str]:
    """
    Dynamically brainstorms distinct, syllabus-tailored thematic angles for jobs in a batch.

    In offline mode or upon external LLM timeout/error, falls back gracefully to deterministic
    syllabus-tailored angles so system reliability and test velocity remain 100%.
    """
    if count <= 0:
        return []

    # Fast deterministic generation for offline mode
    if config.OFFLINE_MODE:
        return _build_deterministic_angles(req, count)

    section_str = enum_value(req.section)
    topic_str = (req.topic or req.subtopic or section_str).strip()
    subtopic_str = (req.subtopic or "").strip()

    system_prompt = (
        "You are an elite AAMC MCAT curriculum architect. Your task is to generate distinct, "
        "syllabus-tailored, mutually non-overlapping pedagogical and thematic angles for a batch of "
        "5-question MCAT passage sets. Each angle must be sharply focused on the user's specific topic, "
        "highlighting an authentic clinical, experimental, or analytical scenario."
    )

    user_prompt = (
        f"MCAT Section: {section_str}\n"
        f"Primary Topic: {topic_str}\n"
        f"Subtopic Focus: {subtopic_str or 'Comprehensive'}\n"
        f"Educator Mandate: {req.additional_instructions or 'Standard AAMC High-Yield'}\n\n"
        f"Generate exactly {count} distinct pedagogical angles for {count} separate passage sets. "
        "Each angle must test a completely different experimental assay, clinical condition, or conceptual facet "
        f"of {topic_str}.\n\n"
        "Return ONLY a JSON array of strings, formatted as:\n"
        "[\n"
        '  "Detailed description of Scenario/Assay 1",\n'
        '  "Detailed description of Scenario/Assay 2"\n'
        "]"
    )

    try:
        model = config.DEFAULT_TEXT_MODEL
        raw_output, _ = await call_llm(
            prompt=user_prompt,
            system_prompt=system_prompt,
            model=model,
            temperature=0.7,
            max_tokens=2500,
        )

        parsed = safe_json_loads(raw_output)

        if isinstance(parsed, list) and len(parsed) >= 1:
            angles: list[str] = []
            for i, item in enumerate(parsed[:count]):
                desc = str(item).strip()
                angles.append(f"Set #{i + 1}: {desc}")

            # If model returned fewer than requested, fill remaining with deterministic angles
            if len(angles) < count:
                deterministic = _build_deterministic_angles(req, count)
                angles.extend(deterministic[len(angles) : count])

            return angles

    except Exception as exc:
        logger.warning(
            "Dynamic batch angle brainstorming failed (%s); falling back to deterministic angles.",
            exc,
        )

    return _build_deterministic_angles(req, count)


async def get_or_create_batch_thematic_angles(
    batch_id: str | None,
    req: GenerationRequest,
    total_jobs: int,
) -> list[str]:
    """Retrieves cached thematic angles for a batch or brainstorms them if not yet generated."""
    if not batch_id:
        return await brainstorm_batch_thematic_angles(req, total_jobs)

    if batch_id in _BATCH_THEMATIC_CACHE:
        cached = _BATCH_THEMATIC_CACHE[batch_id]
        if len(cached) >= total_jobs:
            return cached

    angles = await brainstorm_batch_thematic_angles(req, total_jobs)

    # Maintain cache bounds
    if len(_BATCH_THEMATIC_CACHE) >= _MAX_CACHE_ENTRIES:
        _BATCH_THEMATIC_CACHE.pop(next(iter(_BATCH_THEMATIC_CACHE)))

    _BATCH_THEMATIC_CACHE[batch_id] = angles
    return angles


async def resolve_batch_thematic_angle(
    job_number: int,
    total_jobs: int,
    req: GenerationRequest,
    batch_id: str | None = None,
) -> str:
    """Resolves the specific pedagogical angle for a job within a batch."""
    needed = max(job_number, total_jobs, 1)
    angles = await get_or_create_batch_thematic_angles(batch_id, req, needed)
    idx = (job_number - 1) % len(angles)
    return angles[idx]
