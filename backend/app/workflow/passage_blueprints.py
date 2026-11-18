"""
passage_blueprints.py - Passage set blueprints, slot specializations, and claim extraction.

Defines the 5-question pedagogical slot blueprints for CARS and Science passage sets,
domain rotation pools, and dynamic passage claim extraction helpers.
"""

from __future__ import annotations

import logging
import re

from app.agents.base import call_llm, safe_json_loads
from app.core.config import config
from app.schemas import GenerationRequest, is_cars

logger = logging.getLogger(__name__)

MODALITY_ROTATION_BY_SECTION: dict[str, list[str]] = {
    "bio_biochem": [
        "histopathology (e.g. H&E tissue biopsy, cellular histology, blood smear)",
        "scientific_diagram (e.g. enzyme kinetics plot, SDS-PAGE gel, metabolic pathway)",
        "gross_anatomy (e.g. organ cross-section, cardiac chambers, renal architecture)",
        "cellular_microscopy (e.g. TEM micrograph of mitochondrial cristae, sarcomere ultrastructure)",
        "physiology_trace (e.g. 12-lead ECG strip, cardiac action potential, PV loop)",
    ],
    "chem_phys": [
        "scientific_diagram (e.g. reaction mechanism, titration curve, optics diagram, circuit)",
        "diagnostic_radiology (e.g. plain radiograph X-ray, CT attenuation, ultrasound, MRI)",
        "physiology_trace (e.g. cardiac electrical trace, respiratory pressure-volume curve)",
        "cellular_microscopy (e.g. membrane channel ultrastructure, electron micrograph)",
    ],
    "psych_soc": [
        "scientific_diagram (e.g. experimental scatter plot with regression line, psychophysics curve)",
        "diagnostic_radiology (e.g. fMRI BOLD cortical activation scan, PET neuroimaging)",
        "gross_anatomy (e.g. neuroanatomical structures: limbic system, hippocampus, amygdala)",
        "clinical_pathology (e.g. neurological examination findings, emotion processing stimuli)",
    ],
}

CARS_SLOT4_APPLICATION_DOMAINS: list[str] = [
    "Clinical Medical Ethics & Patient Autonomy (e.g., triage protocols, informed consent disputes, surrogate decision-making)",
    "Environmental Policy & Conservation Governance (e.g., water rights allocation, biodiversity treaties, ecological remediation)",
    "Historical Jurisprudence & Constitutional Law (e.g., statutory interpretation, judicial precedent, executive wartime powers)",
    "Art Curation & Architectural Preservation (e.g., museum restitution claims, urban monument removal, adaptive reuse ethics)",
    "Behavioral Economics & Consumer Welfare (e.g., regulatory nudges, anti-monopoly enforcement, public utility rate-setting)",
    "Artificial Intelligence & Algorithmic Governance (e.g., automated recidivism risk scoring, facial recognition limits, transparency mandates)",
    "Higher Education & Standardized Evaluation Policy (e.g., affirmative action, holistic admissions, vocational tracking)",
    "Civic Infrastructure & Urban Planning (e.g., transit equity, eminent domain, disaster mitigation zoning)",
    "Academic Publishing & Scientific Integrity (e.g., peer review confidentiality, replication mandates, patenting academic discoveries)",
    "International Diplomacy & Treaty Compliance (e.g., arms inspection protocols, cross-border carbon border adjustments, diplomatic immunity)",
]

SCIENCE_SLOT5_EXPERIMENTAL_CONDITIONS: list[str] = [
    "Targeted Small-Molecule Enzyme Inhibition (e.g., novel competitive vs allosteric inhibitor added to assay)",
    "Genetic Knockdown / CRISPR Disruption (e.g., siRNA silencing of target kinase or transporter)",
    "Physiological Stress / Environmental Perturbation (e.g., altered extracellular pH, hyperosmotic shock, hypothermic incubation)",
    "Isotopic Tracer / Radioligand Competition (e.g., deuterated substrate substitution or pulse-chase labeling)",
    "Site-Directed Mutagenesis (e.g., conservative vs non-conservative active-site residue substitution)",
    "Receptor Antagonism / Channel Blockade (e.g., selective receptor blocker or ionophore titration)",
    "Metabolic Intermediate Depletion (e.g., nutrient starvation, glycolytic inhibitor, or uncoupling agent)",
    "Co-culture / Multi-Tissue Interaction (e.g., conditioned media transfer or paracrine signaling assay)",
    "Altered Kinetic Substrate Range (e.g., varying substrate concentrations across Vmax / Km regimes)",
    "In Vivo Animal Model Validation (e.g., knockout mouse phenotype vs in vitro cell culture findings)",
]


def resolve_slot_domain_index(req: GenerationRequest, attempt: int = 0) -> int:
    """Deterministically extracts or hashes a rotation index (0-9) for slot directives, rotating across replenishment attempts."""
    offset = max(0, attempt)
    if req.thematic_angle:
        match = re.search(r"(?:job|set)\s*#?(\d+)", req.thematic_angle, re.IGNORECASE)
        if match:
            num = int(match.group(1))
            return (num - 1 + offset) % 10
    seed_str = req.passage_id or req.batch_id or req.thematic_angle or req.run_id or ""
    if seed_str:
        return (abs(hash(seed_str)) + offset) % 10
    return offset % 10


# Standard AAMC CARS 5-Question Set Blueprint
CARS_PASSAGE_SET_BLUEPRINTS: list[dict[str, str]] = [
    {
        "skill": "CARS1",
        "archetype": "Central Claim / Main Thesis",
        "directive": (
            "SLOT 1 FOCUS: Test the author's overarching thesis, central argument, or primary communicative purpose across the entire passage. "
            "Formulate an unambiguous stem asking for the author's core claim or purpose."
        ),
    },
    {
        "skill": "CARS1",
        "archetype": "Local Detail & Passage Evidence",
        "directive": (
            "SLOT 2 FOCUS: Test direct textual comprehension of a specific concept, term, or relationship discussed in the early paragraphs (Paragraph 1 or 2). "
            "Do NOT ask about the overarching thesis; test local textual evidence."
        ),
    },
    {
        "skill": "CARS2",
        "archetype": "Rhetorical Function / Author's Stance",
        "directive": (
            "SLOT 3 FOCUS: Test the logical or rhetorical function of a specific phrase, metaphor, or cited example in the middle of the passage "
            "(e.g., why the author mentions X, or how Paragraph 3 functions relative to Paragraph 2). Do NOT repeat the main claim or early definitions."
        ),
    },
    {
        "skill": "CARS3",
        "archetype": "Reasoning Beyond the Text: Novel Scenario Application",
        "directive": (
            "SLOT 4 FOCUS: Reasoning Beyond the Text (Novel Scenario Application). "
            "Extrapolate the author's reasoning to a NEW, hypothetical scenario NOT described in the text. "
            "MANDATORY NON-OVERLAP: Must NOT test local textual recall from Paragraph 1, 2, or 3."
        ),
    },
    {
        "skill": "CARS3",
        "archetype": "Reasoning Beyond the Text: Challenge / Weaken Assumptions",
        "directive": (
            "SLOT 5 FOCUS: Reasoning Beyond the Text (Evaluating Counter-Evidence). "
            "Identify a specific secondary assumption, qualification, or boundary condition presented in the later paragraphs (Paragraph 4 or 5). "
            "Formulate a question asking which new hypothetical finding or counter-example would most directly challenge, weaken, or complicate that specific point. "
            "MANDATORY ANTI-DUPLICATION RULE: "
            "1. You MUST NOT challenge the primary thesis tested in Slot 1. "
            "2. You MUST NOT test the local evidence from Paragraph 1 or 2 tested in Slot 2. "
            "3. You MUST NOT test the rhetorical device from Paragraph 3 tested in Slot 3. "
            "4. You MUST NOT use the hypothetical application scenario tested in Slot 4. "
            "Anchor exclusively on the concluding paragraph's assumptions."
        ),
    },
]

# Standard AAMC Science 5-Question Set Blueprint (CPBS, BBLS, PSBB)
SCIENCE_PASSAGE_SET_BLUEPRINTS: list[dict[str, str]] = [
    {
        "skill": "Skill_1",
        "archetype": "Scientific Concept & Principle Foundation",
        "directive": (
            "SLOT 1 FOCUS: Test foundational biochemical, physical, or physiological concepts referenced in the early passage introduction (Paragraph 1). "
            "Focus strictly on the primary scientific definition, nomenclature, or fundamental law. "
            "Do NOT evaluate experimental assays, follow-up deductions, or downstream mechanistic outcomes."
        ),
    },
    {
        "skill": "Skill_4",
        "archetype": "Data, Figure & Graph Interpretation",
        "directive": (
            "SLOT 2 FOCUS: Test data-based and statistical reasoning (Skill 4). "
            "Require the examinee to analyze a quantitative trend, data relationship, experimental baseline, or table/figure/graph described in the passage. "
            "Do NOT test pure recall of terminology."
        ),
    },
    {
        "skill": "Skill_3",
        "archetype": "Experimental Design & Methodological Rationale",
        "directive": (
            "SLOT 3 FOCUS: Test reasoning about research design and execution (Skill 3). "
            "Evaluate why a specific control was chosen, how a variable was isolated, or the rationale for a specific experimental assay/reagent. "
            "Do NOT ask about data interpretation or definitions."
        ),
    },
    {
        "skill": "Skill_2",
        "archetype": "Scientific Reasoning & Problem Solving / Downstream Mechanism",
        "directive": (
            "SLOT 4 FOCUS: Test multi-step mechanistic deduction or problem solving (Skill 2). "
            "Require combining a middle/late passage observation with outside foundational knowledge to deduce a downstream molecular mechanism, pathway shift, or calculation. "
            "MANDATORY NON-OVERLAP: You MUST NOT test the introductory definition, historical origin, or primary premise evaluated in Slot 1."
        ),
    },
    {
        "skill": "Skill_2",
        "archetype": "Novel Experimental Condition / Hypothesis Testing",
        "directive": (
            "SLOT 5 FOCUS: Predict the outcome of a novel follow-up experiment or modification to the experimental protocol (Reasoning Beyond the Passage). "
            "Ask examinees to predict the biochemical/physical outcome based on the mechanistic principles established in Paragraph 4 or 5. "
            "MANDATORY ANTI-DUPLICATION RULE: "
            "1. You MUST NOT test the introductory definition from Paragraph 1 tested in Slot 1. "
            "2. You MUST NOT test the primary data/graph interpretation from Slot 2. "
            "3. You MUST NOT test the methodology or controls from Slot 3. "
            "4. You MUST NOT test the downstream mechanism from Slot 4. "
            "Focus exclusively on predicting the result of the new follow-up condition."
        ),
    },
]


async def extract_passage_slot_blueprints(
    passage_text: str,
    req: GenerationRequest,
) -> list[dict[str, str]]:
    """
    Dynamically extracts 5 passage-grounded pedagogical slot blueprints from the reading passage text.
    In live mode, uses fast LLM claim extraction; in offline mode or on failure, uses deterministic
    passage text parsing to anchor Slot 1-5 directly on the passage paragraphs.
    """
    sec_is_cars = is_cars(req.section)
    if not passage_text or not passage_text.strip():
        return CARS_PASSAGE_SET_BLUEPRINTS if sec_is_cars else SCIENCE_PASSAGE_SET_BLUEPRINTS

    paragraphs = [p.strip() for p in passage_text.split("\n\n") if len(p.strip()) > 30]
    if len(paragraphs) < 2:
        paragraphs = [p.strip() for p in passage_text.split("\n") if len(p.strip()) > 30]
    if not paragraphs:
        paragraphs = [passage_text[:200]]

    def _clean_excerpt(p: str, max_words: int = 22) -> str:
        words = p.replace("\n", " ").split()
        if len(words) <= max_words:
            return " ".join(words)
        return " ".join(words[:max_words]) + "..."

    p1_summary = _clean_excerpt(paragraphs[0])
    p2_summary = _clean_excerpt(paragraphs[1] if len(paragraphs) > 1 else paragraphs[0])
    p3_summary = _clean_excerpt(paragraphs[2] if len(paragraphs) > 2 else p2_summary)
    p4_summary = _clean_excerpt(
        paragraphs[3]
        if len(paragraphs) > 3
        else (paragraphs[2] if len(paragraphs) > 2 else p2_summary)
    )
    p_last_summary = _clean_excerpt(paragraphs[-1])
    total_paras = len(paragraphs)

    domain_idx = resolve_slot_domain_index(req)

    def _build_deterministic() -> list[dict[str, str]]:
        if sec_is_cars:
            domain = CARS_SLOT4_APPLICATION_DOMAINS[domain_idx]
            return [
                {
                    "skill": "CARS1",
                    "archetype": "Central Claim / Main Thesis",
                    "directive": (
                        f"SLOT 1 FOCUS: Test the author's overarching thesis or central communicative purpose across the entire passage. "
                        f'Textual anchor: [Paragraph 1 Anchor: "{p1_summary}"].'
                    ),
                    "premise_excerpt": p1_summary,
                },
                {
                    "skill": "CARS1",
                    "archetype": "Local Detail & Passage Evidence",
                    "directive": (
                        f"SLOT 2 FOCUS: Test direct textual comprehension of specific evidence or claims in early paragraphs. "
                        f'Textual anchor: [Paragraph 2 Anchor: "{p2_summary}"]. Do NOT ask about the overarching thesis.'
                    ),
                    "premise_excerpt": p2_summary,
                },
                {
                    "skill": "CARS2",
                    "archetype": "Rhetorical Function / Author's Stance",
                    "directive": (
                        f"SLOT 3 FOCUS: Test the logical or rhetorical function of a specific metaphor, analogy, or cited argument in the middle of the passage. "
                        f'Textual anchor: [Paragraph 3 Anchor: "{p3_summary}"].'
                    ),
                    "premise_excerpt": p3_summary,
                },
                {
                    "skill": "CARS3",
                    "archetype": "Reasoning Beyond the Text: Novel Scenario Application",
                    "directive": (
                        f"SLOT 4 FOCUS: Reasoning Beyond the Text (Novel Scenario Application). "
                        f"Extrapolate the author's reasoning to a contextually harmonious novel scenario in the domain of [{domain}]. "
                        f'Textual anchor: [Paragraph 4 Anchor: "{p4_summary}"].'
                    ),
                    "premise_excerpt": p4_summary,
                },
                {
                    "skill": "CARS3",
                    "archetype": "Reasoning Beyond the Text: Challenge / Weaken Assumptions",
                    "directive": (
                        f"SLOT 5 FOCUS: Reasoning Beyond the Text (Evaluating Counter-Evidence). "
                        f"Identify a specific boundary condition or premise in the concluding paragraphs and test what finding would most directly challenge it. "
                        f'Textual anchor: [Paragraph {total_paras} Concluding Anchor: "{p_last_summary}"].'
                    ),
                    "premise_excerpt": p_last_summary,
                },
            ]
        condition = SCIENCE_SLOT5_EXPERIMENTAL_CONDITIONS[domain_idx]
        return [
            {
                "skill": "Skill_1",
                "archetype": "Scientific Concept & Principle Foundation",
                "directive": (
                    f"SLOT 1 FOCUS: Test foundational physical, chemical, or biological concepts established in the introductory paragraph. "
                    f'Textual anchor: [Paragraph 1 Anchor: "{p1_summary}"].'
                ),
                "premise_excerpt": p1_summary,
            },
            {
                "skill": "Skill_4",
                "archetype": "Data, Figure & Graph Interpretation",
                "directive": (
                    f"SLOT 2 FOCUS: Test data-based and statistical reasoning. Require the examinee to analyze a quantitative trend, figure, or assay baseline described in the passage. "
                    f'Textual anchor: [Paragraph 2 Anchor: "{p2_summary}"].'
                ),
                "premise_excerpt": p2_summary,
            },
            {
                "skill": "Skill_3",
                "archetype": "Experimental Design & Methodological Rationale",
                "directive": (
                    f"SLOT 3 FOCUS: Test reasoning about research design and execution. Evaluate why a specific control was chosen, how a variable was isolated, or the rationale for assay reagents. "
                    f'Textual anchor: [Paragraph 3 Anchor: "{p3_summary}"].'
                ),
                "premise_excerpt": p3_summary,
            },
            {
                "skill": "Skill_2",
                "archetype": "Scientific Reasoning & Problem Solving / Downstream Mechanism",
                "directive": (
                    f"SLOT 4 FOCUS: Test multi-step mechanistic deduction or problem solving combining passage observations with outside scientific knowledge. "
                    f'Textual anchor: [Paragraph 4 Anchor: "{p4_summary}"].'
                ),
                "premise_excerpt": p4_summary,
            },
            {
                "skill": "Skill_2",
                "archetype": "Novel Experimental Condition / Hypothesis Testing",
                "directive": (
                    f"SLOT 5 FOCUS: Predict the outcome of a plausible follow-up experiment or novel perturbation directly modifying the experimental setup in the passage. "
                    f'Perturbation condition: [{condition}]. Textual anchor: [Paragraph {total_paras} Anchor: "{p_last_summary}"].'
                ),
                "premise_excerpt": p_last_summary,
            },
        ]

    if config.OFFLINE_MODE:
        return _build_deterministic()

    try:
        model = config.DEFAULT_TEXT_MODEL
        if sec_is_cars:
            prompt = (
                "Analyze this CARS reading passage and extract 5 specific, strictly non-overlapping slot targets:\n"
                "1. Main thesis / primary communicative claim (anchored in Paragraph 1)\n"
                "2. Specific local detail or empirical assertion (anchored in Paragraph 2)\n"
                "3. Rhetorical function of a key metaphor or cited author (anchored in Paragraph 3)\n"
                "4. A contextually harmonious novel application domain and scenario (anchored in Paragraph 4)\n"
                "5. A specific boundary condition or assumption in the conclusion and a potential counter-finding to challenge it (anchored in the concluding paragraph)\n\n"
                "MANDATORY ANTI-COLLISION REQUIREMENTS: Each slot MUST test a completely disjoint claim across separate paragraphs.\n\n"
                f"Passage:\n{passage_text[:3500]}\n\n"
                "Return ONLY a JSON object with keys 'slot1', 'slot2', 'slot3', 'slot4', 'slot5', each containing a 1-2 sentence directive specifying the exact claim or scenario to test."
            )
        else:
            prompt = (
                "Analyze this MCAT Science reading passage and extract 5 specific, strictly non-overlapping slot targets:\n"
                "1. Foundational principle or definition established in Paragraph 1\n"
                "2. Key quantitative trend, figure, or assay finding in Paragraph 2\n"
                "3. Research design rationale or control variable choice in Paragraph 3\n"
                "4. Downstream molecular mechanism or multi-step pathway deduction in Paragraph 4\n"
                "5. Grounded novel experimental perturbation or follow-up assay modifying the setup in the concluding paragraph\n\n"
                "MANDATORY ANTI-COLLISION REQUIREMENTS: Each slot MUST test a completely disjoint claim or assay across separate paragraphs.\n\n"
                f"Passage:\n{passage_text[:3500]}\n\n"
                "Return ONLY a JSON object with keys 'slot1', 'slot2', 'slot3', 'slot4', 'slot5', each containing a 1-2 sentence directive specifying the exact claim, assay, or perturbation to test."
            )

        raw, _ = await call_llm(
            prompt=prompt,
            system_prompt="You are an expert AAMC psychometrician designing blueprint directives for a 5-question passage set.",
            model=model,
            temperature=0.3,
            max_tokens=2500,
        )
        data = safe_json_loads(raw)
        if isinstance(data, dict) and "slot1" in data and "slot5" in data:
            base_blueprints = (
                CARS_PASSAGE_SET_BLUEPRINTS if sec_is_cars else SCIENCE_PASSAGE_SET_BLUEPRINTS
            )
            blueprints = []
            excerpts = [p1_summary, p2_summary, p3_summary, p4_summary, p_last_summary]
            for i, bp in enumerate(base_blueprints):
                key = f"slot{i + 1}"
                directive_addon = str(data.get(key, "")).strip()
                combined_directive = (
                    f"{bp['directive']} Grounded Passage Target: {directive_addon}"
                    if directive_addon
                    else bp["directive"]
                )
                blueprints.append(
                    {
                        "skill": bp["skill"],
                        "archetype": bp["archetype"],
                        "directive": combined_directive,
                        "premise_excerpt": directive_addon or excerpts[i],
                    }
                )
            return blueprints
    except Exception as exc:
        logger.warning(
            "Dynamic passage claim extraction failed (%s); falling back to deterministic extraction.",
            exc,
        )

    return _build_deterministic()
