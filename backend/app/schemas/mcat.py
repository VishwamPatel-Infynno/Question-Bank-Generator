from __future__ import annotations

import json
import logging
from enum import Enum
from pathlib import Path


class MCATSection(str, Enum):
    CHEM_PHYS = "chem_phys"
    CARS = "cars"
    BIO_BIOCHEM = "bio_biochem"
    PSYCH_SOC = "psych_soc"


MCAT_SECTION_LABELS = {
    MCATSection.CHEM_PHYS: "Chemical and Physical Foundations of Biological Systems",
    MCATSection.CARS: "Critical Analysis and Reasoning Skills",
    MCATSection.BIO_BIOCHEM: "Biological and Biochemical Foundations of Living Systems",
    MCATSection.PSYCH_SOC: "Psychological, Social, and Biological Foundations of Behavior",
}

MCAT_SECTION_SHORT_LABELS = {
    MCATSection.CHEM_PHYS: "Chem / Phys",
    MCATSection.CARS: "CARS",
    MCATSection.BIO_BIOCHEM: "Bio / Biochem",
    MCATSection.PSYCH_SOC: "Psych / Soc",
}

MCAT_SECTION_CODES = {
    MCATSection.CHEM_PHYS: "CP",
    MCATSection.CARS: "CARS",
    MCATSection.BIO_BIOCHEM: "BB",
    MCATSection.PSYCH_SOC: "PS",
}

MCAT_PACING = {
    MCATSection.CHEM_PHYS: {"target": "~96s / question", "desc": "59 questions in 95 mins"},
    MCATSection.CARS: {"target": "~101s / question", "desc": "53 questions in 90 mins"},
    MCATSection.BIO_BIOCHEM: {"target": "~96s / question", "desc": "59 questions in 95 mins"},
    MCATSection.PSYCH_SOC: {"target": "~96s / question", "desc": "59 questions in 95 mins"},
}

MCAT_SUBTOPICS = {
    MCATSection.CHEM_PHYS: [
        "General Chemistry (Stoichiometry, Equilibrium & Electrochemistry)",
        "Organic Chemistry (Reaction Mechanisms, Functional Groups & Separations)",
        "Classical & Fluid Mechanics (Kinematics, Fluids, Work & Energy)",
        "Thermodynamics & Kinetics (Enthalpy, Entropy & Reaction Rates)",
        "Waves, Sound, Optics & Light",
        "Biochemical Solutions, Buffers & Acid-Base Chemistry",
    ],
    MCATSection.CARS: [
        "Humanities (Philosophy, Ethics & Epistemology)",
        "Humanities (Art, Literature & Cultural Studies)",
        "Social Sciences (History, Sociology & Political Theory)",
        "Social Sciences (Anthropology & Economic Systems)",
        "Foundations of Comprehension (Direct Inferences & Thesis Extraction)",
        "Reasoning Within the Text (Argument Evaluation & Author Tone)",
        "Reasoning Beyond the Text (New Evidence & Analogous Scenarios)",
    ],
    MCATSection.BIO_BIOCHEM: [
        "Biochemistry & Enzyme Kinetics (Michaelis-Menten & Allosteric Regulation)",
        "Metabolic Pathways & Cellular Bioenergetics (Glycolysis, Krebs, OxPhos)",
        "Molecular Genetics, DNA Replication & Gene Expression",
        "Cellular Biology, Membrane Transport & Microbiology",
        "Organ Systems Physiology (Cardiovascular, Renal, Endocrine & Nervous)",
        "Laboratory Methods & Experimental Research Design",
    ],
    MCATSection.PSYCH_SOC: [
        "Sensation, Perception & Cognitive Psychology",
        "Behavioral Neuroscience & Biological Bases of Behavior",
        "Social Psychology, Social Cognition & Group Dynamics",
        "Sociological Theories, Social Institutions & Stratification",
        "Demographic Changes, Culture & Health Disparities",
    ],
}

AAMC_REASONING_SKILLS = {
    "Skill_1": "Knowledge of Scientific Concepts and Principles",
    "Skill_2": "Scientific Reasoning and Problem Solving",
    "Skill_3": "Reasoning About the Design and Execution of Research",
    "Skill_4": "Data-based and Statistical Reasoning",
    "CARS_Skill_1": "Foundations of Comprehension",
    "CARS_Skill_2": "Reasoning Within the Text",
    "CARS_Skill_3": "Reasoning Beyond the Text",
}

AAMC_SKILL_LABELS = {
    "Skill_1": "AAMC Skill 1: Scientific Concepts",
    "Skill_2": "AAMC Skill 2: Scientific Reasoning",
    "Skill_3": "AAMC Skill 3: Research Design",
    "Skill_4": "AAMC Skill 4: Data & Statistics",
    "CARS_Skill_1": "CARS Skill 1: Comprehension",
    "CARS_Skill_2": "CARS Skill 2: Reasoning In-Text",
    "CARS_Skill_3": "CARS Skill 3: Reasoning Beyond",
}


class Difficulty(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    EASY = "easy"
    HARD = "hard"


SECTION_CODE_MAP = {
    # Official MCAT codes & keys
    "CP": MCATSection.CHEM_PHYS,
    "CARS": MCATSection.CARS,
    "BB": MCATSection.BIO_BIOCHEM,
    "PS": MCATSection.PSYCH_SOC,
    "chem_phys": MCATSection.CHEM_PHYS,
    "cars": MCATSection.CARS,
    "bio_biochem": MCATSection.BIO_BIOCHEM,
    "psych_soc": MCATSection.PSYCH_SOC,
    "chemical_and_physical_foundations": MCATSection.CHEM_PHYS,
    "critical_analysis_and_reasoning_skills": MCATSection.CARS,
    "biological_and_biochemical_foundations": MCATSection.BIO_BIOCHEM,
    "psychological_social_and_biological_foundations": MCATSection.PSYCH_SOC,
}


def normalize_section(val: str) -> MCATSection:
    """Normalizes 'CP', 'CARS', 'BB', 'PS', or full names into MCATSection."""
    if isinstance(val, MCATSection):
        return val
    cleaned = str(val).strip()
    if cleaned in SECTION_CODE_MAP:
        return SECTION_CODE_MAP[cleaned]
    upper = cleaned.upper()
    if upper in SECTION_CODE_MAP:
        return SECTION_CODE_MAP[upper]
    lower = cleaned.lower()
    if lower in SECTION_CODE_MAP:
        return SECTION_CODE_MAP[lower]
    return MCATSection.CHEM_PHYS


def calculate_mcat_scaled_score(audit_total: int, difficulty: str = "medium") -> dict:
    """
    Calibrates internal 100-point psychometric audit score into official AAMC MCAT scaled score.
    Returns:
        section_score: 118 - 132 scale (125 is 50th percentile)
        composite_score: 472 - 528 scale (500 is 50th percentile)
        percentile: Estimated percentile rank e.g. "96th Percentile"
    """
    diff = str(difficulty).lower()
    is_hard = diff in ("high", "hard")

    # Determine baseline section score (118-132)
    if audit_total >= 96:
        base_sec = 132 if is_hard else 131
        percentile = "99th+ Percentile (Elite)"
    elif audit_total >= 92:
        base_sec = 130 if is_hard else 129
        percentile = "96th Percentile (Top Tier)"
    elif audit_total >= 88:
        base_sec = 128 if is_hard else 127
        percentile = "88th Percentile (Competitive)"
    elif audit_total >= 82:
        base_sec = 126
        percentile = "72nd Percentile (Solid)"
    elif audit_total >= 75:
        base_sec = 125
        percentile = "50th Percentile (Median)"
    elif audit_total >= 65:
        base_sec = 123
        percentile = "35th Percentile"
    else:
        base_sec = max(118, 118 + int((audit_total / 100.0) * 5))
        percentile = "Below Average"

    composite = base_sec * 4
    return {
        "section_score": base_sec,
        "composite_score": composite,
        "percentile": percentile,
    }


# Load Manager Dependent Taxonomy
_DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "mcat_dependent_taxonomy.json"
try:
    with open(_DATA_PATH, encoding="utf-8") as _f:
        DEPENDENT_TAXONOMY = json.load(_f)
except (OSError, json.JSONDecodeError) as _taxonomy_error:
    logging.getLogger(__name__).error(
        "Could not load %s (%s); using an EMPTY taxonomy. Selection flows will have no data.",
        _DATA_PATH,
        _taxonomy_error,
    )
    DEPENDENT_TAXONOMY = {
        "schema_version": "1.0",
        "exam": {"id": "MCAT", "name": "MCAT"},
        "selection_flow": ["section", "subject", "unit", "topic", "subtopic", "skill", "subskill"],
        "sections": [],
        "skills": [],
        "generation_options": {},
        "generation_form_fields": [],
    }

# Dynamic extraction from taxonomy JSON
_gen_options = DEPENDENT_TAXONOMY.get("generation_options", {})

CONTENT_DOMAINS = [item.get("id") for item in _gen_options.get("content_domain", [])] or [
    "General_Chemistry",
    "Organic_Chemistry",
    "Biochemistry",
    "Physics",
    "Molecular_Biology",
    "Microbiology",
    "Human_Physiology",
    "Cognitive_Psychology",
    "Behavioral_Neuroscience",
    "Sociology",
    "Humanities_Philosophy",
    "Social_Sciences",
]

CONTENT_DOMAINS_DETAILED = _gen_options.get("content_domain", [])

QUESTION_TYPES = [item.get("id") for item in _gen_options.get("question_type", [])] or [
    "DISCRETE_MCQ",
    "PASSAGE_BASED_MCQ",
    "GRAPH_INTERPRETATION",
    "TABLE_INTERPRETATION",
    "EXPERIMENTAL_DESIGN",
    "CALCULATION",
    "DATA_INTERPRETATION",
    "PASSAGE_INFERENCE",
]

QUESTION_TYPES_DETAILED = _gen_options.get("question_type", [])

PRIMARY_TRAPS = [item.get("id") for item in _gen_options.get("primary_trap", [])] or [
    "CONCEPT_CONFUSION",
    "WRONG_BASE",
    "UNIT_CONVERSION",
    "FORMULA_MISAPPLICATION",
    "SIGN_CONVENTION",
    "PROPORTIONALITY_ERROR",
    "ASSUMPTION_MISSED",
    "CAUSE_EFFECT_CONFUSION",
    "CORRELATION_CAUSATION",
    "CONTROL_GROUP_CONFUSION",
    "VARIABLE_CONFUSION",
    "SAMPLE_SIZE_BIAS",
    "STATISTICAL_SIGNIFICANCE",
    "GRAPH_AXIS_MISREADING",
    "TABLE_COMPARISON_ERROR",
    "TREND_EXTRAPOLATION",
    "MECHANISM_CONFUSION",
    "EXCEPTION_OVERLOOKED",
    "NEGATION_MISREAD",
    "SCOPE_SHIFT",
    "UNSUPPORTED_INFERENCE",
    "PASSAGE_CONTRADICTION",
    "OVERGENERALIZATION",
    "DISTRACTOR_OVERINTERPRETATION",
    "ANSWER_CHOICE_CONFLATION",
]

PRIMARY_TRAPS_DETAILED = _gen_options.get("primary_trap", [])

# Canonical cognitive trap rotation sequence for batch diversity & anti-collision re-prompting
ALT_TRAP_ROTATION: tuple[str, ...] = (
    "CONCEPT_CONFUSION",
    "FORMULA_MISAPPLICATION",
    "SIGN_CONVENTION",
    "PROPORTIONALITY_ERROR",
    "VARIABLE_CONFUSION",
    "CAUSE_EFFECT_CONFUSION",
    "TREND_EXTRAPOLATION",
    "ASSUMPTION_MISSED",
)

LIKELY_MISTAKE_PATTERNS = _gen_options.get("likely_mistake_pattern", {}).get("values", [])

TAXONOMY_SKILLS = DEPENDENT_TAXONOMY.get("skills", [])


def get_taxonomy_data() -> dict:
    """Returns the full parsed manager MCAT dependent taxonomy."""
    return DEPENDENT_TAXONOMY


def get_skills_for_section(section_val: str | MCATSection) -> list[dict]:
    """Returns skills with subskills applicable to a given section code e.g. CP, BB, PS, CARS."""
    sec = normalize_section(section_val)
    sec_code = MCAT_SECTION_CODES.get(sec, "CP")
    return [sk for sk in TAXONOMY_SKILLS if sec_code in sk.get("applies_to", [])]


def get_section_tree(section_val: str | MCATSection) -> dict | None:
    """Finds the section hierarchy tree for a given MCATSection or string."""
    sec = normalize_section(section_val)
    sec_code = MCAT_SECTION_CODES.get(sec, "CP")
    for s in DEPENDENT_TAXONOMY.get("sections", []):
        if s.get("id") == sec_code:
            return s
    return None


def normalize_primary_trap(trap_str: str | None) -> str | None:
    """Normalizes any primary distractor trap string to an official AAMC taxonomy ID."""
    if not trap_str or trap_str in ("Automatic", "None", ""):
        return None
    clean = str(trap_str).strip()
    if clean in PRIMARY_TRAPS:
        return clean
    up = clean.upper().replace(" ", "_").replace("-", "_")
    if up in PRIMARY_TRAPS:
        return up
    legacy_map = {
        "OUT_OF_SCOPE": "UNSUPPORTED_INFERENCE",
        "DISTORTION_OPPOSITE": "PASSAGE_CONTRADICTION",
        "OUTSIDE_KNOWLEDGE_IN_CARS": "UNSUPPORTED_INFERENCE",
        "EXTREME_LANGUAGE": "OVERGENERALIZATION",
        "CALCULATION_FORMULA_TRAP": "FORMULA_MISAPPLICATION",
        "HALF_RIGHT_FALSE_PREMISE": "ANSWER_CHOICE_CONFLATION",
        "KEYWORD_TRAP": "DISTRACTOR_OVERINTERPRETATION",
        "PARTIAL_MATCH": "EXCEPTION_OVERLOOKED",
        "HALF_TRUTH": "ANSWER_CHOICE_CONFLATION",
        "UNWARRANTED_ASSUMPTION": "ASSUMPTION_MISSED",
        "CALCULATION_TRAP": "FORMULA_MISAPPLICATION",
    }
    if up in legacy_map:
        return legacy_map[up]
    clean_lower = clean.lower().replace("_", " ").replace("-", " ")
    for item in PRIMARY_TRAPS_DETAILED:
        val = item.get("value", "").lower()
        if val == clean_lower or clean_lower in val:
            return item.get("id")
    return up


def normalize_mistake_pattern(pattern_str: str | None) -> str | None:
    """Normalizes a student misconception to an official AAMC pattern value or preserves clean custom string."""
    if not pattern_str or pattern_str in ("Automatic", "None", ""):
        return None
    clean = str(pattern_str).strip()
    up = clean.upper().replace(" ", "_").replace("-", "_")
    for item in LIKELY_MISTAKE_PATTERNS:
        if item.get("id") == up or item.get("id") == clean:
            return item.get("value", clean)
        val = item.get("value", "").lower()
        if clean.lower() == val or clean.lower() in val:
            return item.get("value", clean)
    return clean
