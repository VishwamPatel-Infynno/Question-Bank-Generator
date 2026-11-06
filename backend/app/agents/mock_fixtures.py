"""Isolated mock drafts and heuristic evaluation fixtures for offline testing and graceful fallback."""

from __future__ import annotations

import re

from app.agents.mock_drafts import MOCK_DRAFTS
from app.schemas import (
    GenerationRequest,
    MCATSection,
    OptionChoice,
    QuestionDraft,
    ReviewScore,
    normalize_section,
)


def _build_raw_mock_draft(req: GenerationRequest) -> QuestionDraft:
    """Provides high-caliber, authentic fallback AAMC MCAT questions across all 4 sections."""
    sec = normalize_section(req.section)
    is_direct_independent = (
        req.passage_required is not None
        and str(req.passage_required).lower() in ("no", "false")
        and not (req.shared_stimulus and req.shared_stimulus.strip())
        and sec != MCATSection.CARS  # CARS is strictly passage-based
    )
    fields = MOCK_DRAFTS.get((sec.value, is_direct_independent)) or MOCK_DRAFTS[(sec.value, False)]
    return QuestionDraft(**fields)


def evaluate_heuristically(
    draft: QuestionDraft, _req: GenerationRequest, iteration: int
) -> ReviewScore:
    """Provides authentic mock evaluation for test suites and offline resilience."""
    if iteration == 1:
        # Intentionally scores 88 (<= 90) on iteration 1 to activate Re-Generator loop in tests
        return ReviewScore(
            authenticity_score=22,
            clarity_score=23,
            distractor_score=21,
            explanation_score=22,
            total_score=88,
            strengths=[
                (
                    "Authentic experimental research vignette conforming to AAMC MCAT standards"
                    if draft.stimulus_text
                    else "Direct question stem with self-contained premises conforming to AAMC discrete standards"
                ),
                "Question stem is clear and scientifically rigorous",
            ],
            weaknesses=[
                "Distractor options could feature deeper experimental cognitive traps",
                "Explanation could further elaborate on why each distractor is definitively ruled out",
            ],
            recommendations=[
                "Elevate distractor sophistication by incorporating realistic biochemical or calculation traps",
                "Explicitly refute all 3 incorrect choices in the pedagogical explanation",
            ],
            passed=False,
        )
    # Iteration 2+ scores 95 (> 90) to certify publication quality
    return ReviewScore(
        authenticity_score=24,
        clarity_score=24,
        distractor_score=23,
        explanation_score=24,
        total_score=95,
        strengths=[
            "Distractors refined into sophisticated cognitive traps",
            "Comprehensive step-by-step scientific proof with distractor counter-analysis",
            "Flawless adherence to AAMC medical admissions conventions",
        ],
        weaknesses=[],
        recommendations=[],
        passed=True,
    )


def improve_draft_heuristically(
    draft: QuestionDraft, _review: ReviewScore, iteration: int
) -> QuestionDraft:
    """Enhances draft for offline mock remediation cycles."""
    enhanced_explanation = (
        f"{draft.explanation}\n\n"
        f"[Re-Generator Quality Enhancement - Iteration {iteration}]:\n"
        f"• Addressed Reviewer Critique: Enhanced distractor plausibility and eliminated borderline ambiguity.\n"
        f"• Explicit Distractor Analysis:\n"
    )
    for opt in draft.options:
        is_key = opt.id in draft.correct_answer_ids or opt.id in [
            k.strip().upper() for k in draft.correct_answer_id.split(",") if k.strip()
        ]
        if is_key:
            enhanced_explanation += f"  - Option {opt.id} [CORRECT]: Validated with primary scientific premise and incontrovertible logical steps.\n"
        else:
            enhanced_explanation += f"  - Option {opt.id} [DISTRACTOR]: Plausible trap representing common conceptual error, ruled out by experimental evidence.\n"

    new_options = [OptionChoice(id=o.id, text=o.text) for o in draft.options]

    return QuestionDraft(
        stimulus_text=draft.stimulus_text,
        question_stem=draft.question_stem,
        options=new_options,
        correct_answer_id=draft.correct_answer_id,
        correct_answer_ids=draft.correct_answer_ids,
        explanation=enhanced_explanation,
        primary_trap=draft.primary_trap,
        aamc_skill=draft.aamc_skill,
        likely_mistake_pattern=draft.likely_mistake_pattern,
        image_needed=draft.image_needed,
        image_prompt_or_type=draft.image_prompt_or_type,
    )


# Authentic multi-question variant definitions for offline testing and collision-free fallback
_MOCK_QUESTION_VARIANTS: dict[str, list[dict]] = {
    "chem_phys_independent": [
        {
            "stem": "In a photoelectric experiment, monochromatic ultraviolet light strikes a cesium target with work function 2.14 eV. If the incident photon energy is 3.50 eV, what is the maximum kinetic energy of the emitted photoelectrons?",
            "options": [
                {"id": "A", "text": "0.68 eV"},
                {"id": "B", "text": "1.36 eV"},
                {"id": "C", "text": "2.14 eV"},
                {"id": "D", "text": "5.64 eV"},
            ],
            "correct": "B",
            "explanation": "Kmax = Ephoton - Φ = 3.50 eV - 2.14 eV = 1.36 eV.",
        },
        {
            "stem": "An object is positioned 30 cm in front of a thin converging lens with a focal length of 10 cm. At what distance from the lens does the real image form?",
            "options": [
                {"id": "A", "text": "15 cm"},
                {"id": "B", "text": "20 cm"},
                {"id": "C", "text": "25 cm"},
                {"id": "D", "text": "30 cm"},
            ],
            "correct": "A",
            "explanation": "Using 1/f = 1/do + 1/di: 1/10 - 1/30 = 2/30 = 1/15, so di = 15 cm.",
        },
        {
            "stem": "An incompressible, non-viscous fluid flows through a horizontal tube that narrows to one-half of its initial cross-sectional area. According to Bernoulli's equation, how does fluid velocity and pressure change at the constriction?",
            "options": [
                {"id": "A", "text": "Velocity doubles and pressure decreases"},
                {"id": "B", "text": "Velocity doubles and pressure increases"},
                {"id": "C", "text": "Velocity halves and pressure increases"},
                {"id": "D", "text": "Velocity quadruples and pressure remains constant"},
            ],
            "correct": "A",
            "explanation": "By continuity (A1v1 = A2v2), halving area doubles velocity. By Bernoulli's equation, increased velocity leads to a decrease in static pressure.",
        },
        {
            "stem": "A standard galvanic cell is constructed with Zn/Zn2+ (E° = -0.76 V) and Cu/Cu2+ (E° = +0.34 V) half-cells. What is the standard cell potential (E°cell) and the thermodynamic spontaneity of the forward reaction?",
            "options": [
                {"id": "A", "text": "+1.10 V, spontaneous (ΔG° < 0)"},
                {"id": "B", "text": "-0.42 V, nonspontaneous (ΔG° > 0)"},
                {"id": "C", "text": "+0.42 V, spontaneous (ΔG° < 0)"},
                {"id": "D", "text": "-1.10 V, nonspontaneous (ΔG° > 0)"},
            ],
            "correct": "A",
            "explanation": "E°cell = E°cathode - E°anode = +0.34 V - (-0.76 V) = +1.10 V. Because E°cell > 0, ΔG° = -nFE°cell < 0 (spontaneous).",
        },
    ],
    "chem_phys_passage": [
        {
            "stem": "Based on the mechanism described in paragraph 1, by what primary process does carbon dioxide cross the apical membrane of renal proximal tubule cells?",
            "options": [
                {
                    "id": "A",
                    "text": "Passive simple diffusion through the hydrophobic lipid bilayer",
                },
                {"id": "B", "text": "Secondary active transport via Na+/CO2 symport"},
                {"id": "C", "text": "Facilitated diffusion through aquaporin channels"},
                {"id": "D", "text": "Primary active transport driven by ATP hydrolysis"},
            ],
            "correct": "A",
            "explanation": "CO2 is a small nonpolar gas that readily diffuses across biological membranes without carrier proteins.",
        },
        {
            "stem": "If severe hypoventilation causes systemic arterial blood pH to drop to 7.15, how will the bicarbonate buffer equilibrium respond to counteract the acidosis?",
            "options": [
                {
                    "id": "A",
                    "text": "Shift left toward CO2 hydration to consume excess bicarbonate",
                },
                {
                    "id": "B",
                    "text": "Shift toward CO2 and H2O to buffer excess protons by consuming HCO3-",
                },
                {"id": "C", "text": "Inhibit renal tubular carbonic anhydrase activity"},
                {"id": "D", "text": "Suppress basolateral Na+/HCO3- cotransport"},
            ],
            "correct": "B",
            "explanation": "Excess H+ drives the equilibrium H+ + HCO3- ⇌ H2CO3 ⇌ H2O + CO2 to the left, buffering hydronium ions.",
        },
        {
            "stem": "The passage states that Compound X is a non-competitive inhibitor of CA-II. How is the catalytic efficiency (kcat / Km) of the enzyme affected in the presence of 10 μM Compound X?",
            "options": [
                {
                    "id": "A",
                    "text": "Catalytic efficiency decreases because kcat decreases while Km is unchanged",
                },
                {
                    "id": "B",
                    "text": "Catalytic efficiency remains unchanged because both kcat and Km decrease",
                },
                {"id": "C", "text": "Catalytic efficiency increases due to allosteric activation"},
                {"id": "D", "text": "Catalytic efficiency decreases solely because Km increases"},
            ],
            "correct": "A",
            "explanation": "Non-competitive inhibitors reduce Vmax (and thus kcat = Vmax/[E]t) while leaving substrate affinity Km unaltered, reducing kcat/Km.",
        },
        {
            "stem": "Following intracellular hydration of CO2 in renal tubular cells, which transporter mediates the basolateral extrusion of bicarbonate into the peritubular capillaries?",
            "options": [
                {"id": "A", "text": "NBCe1 (electrogenic Na+/HCO3- cotransporter)"},
                {"id": "B", "text": "Apical membrane-bound CA-IV"},
                {"id": "C", "text": "Na+/K+ ATPase electrogenic pump"},
                {"id": "D", "text": "Carbonic anhydrase soluble CA-II"},
            ],
            "correct": "A",
            "explanation": "The passage explicitly identifies NBCe1 as the basolateral cotransporter carrying bicarbonate into peritubular capillaries.",
        },
    ],
    "cars_passage": [
        {
            "stem": "Which of the following best summarizes the author's primary argument regarding the nature of authentic aesthetic judgment?",
            "options": [
                {
                    "id": "A",
                    "text": "Aesthetic appraisal operates as an open-ended dialogue between individual phenomenology and shared culture.",
                },
                {
                    "id": "B",
                    "text": "Bourdieu's sociological determinism thoroughly refutes any transcendent aesthetic claims.",
                },
                {
                    "id": "C",
                    "text": "Kant's concept of the sensus communis correctly explains empirical consensus across all cultures.",
                },
                {
                    "id": "D",
                    "text": "Cultural capital has become irrelevant due to contemporary artistic democratization.",
                },
            ],
            "correct": "A",
            "explanation": "Paragraph 3 concludes that artistic power lies in staging an open dialogue between subjectivity and collective imagination.",
        },
        {
            "stem": "In the context of paragraph 2, the author discusses Pierre Bourdieu's concept of 'cultural capital' primarily to:",
            "options": [
                {
                    "id": "A",
                    "text": "Introduce the sociological critique that taste serves as a socially conditioned marker of elite distinction.",
                },
                {
                    "id": "B",
                    "text": "Validate Kant's principle of disinterested contemplative pleasure.",
                },
                {
                    "id": "C",
                    "text": "Argue that working-class individuals lack capacity for aesthetic enjoyment.",
                },
                {
                    "id": "D",
                    "text": "Prove that avant-garde artistic forms are aesthetically superior to traditional forms.",
                },
            ],
            "correct": "A",
            "explanation": "Bourdieu argues taste is conditioned by education and privilege, functioning to legitimate class distinctions.",
        },
        {
            "stem": "Based on the passage, the author would most likely consider which of the following an example of 'disinterested' contemplation?",
            "options": [
                {
                    "id": "A",
                    "text": "Admiring a sculpture's harmonious proportions without regard to its market price or social utility.",
                },
                {
                    "id": "B",
                    "text": "Purchasing an abstract painting to impress colleagues and signal cultural sophistication.",
                },
                {
                    "id": "C",
                    "text": "Appraising an architectural design solely based on its energy efficiency and commercial viability.",
                },
                {
                    "id": "D",
                    "text": "Enjoying a musical composition primarily because it evokes nostalgic personal memories.",
                },
            ],
            "correct": "A",
            "explanation": "Kant defines disinterested aesthetic judgment as contemplation free from practical utility or sensory gratification.",
        },
        {
            "stem": "The author asserts that genuine encounters with art routinely disrupt habitual perception primarily because such encounters:",
            "options": [
                {
                    "id": "A",
                    "text": "Elicit cognitive disequilibrium and unsettle entrenched perceptual habits across diverse cultures.",
                },
                {
                    "id": "B",
                    "text": "Conform rigidly to pre-existing Kantian empirical categories.",
                },
                {
                    "id": "C",
                    "text": "Reinforce established social stratification and elite privileges.",
                },
                {
                    "id": "D",
                    "text": "Eliminate all subjective emotional resonance in favor of objective critical analysis.",
                },
            ],
            "correct": "A",
            "explanation": "The author points to cognitive disequilibrium and unsettled habitual beliefs as proof of art's disruptive power.",
        },
    ],
    "bio_biochem_independent": [
        {
            "stem": "In hepatocytes, which allosteric metabolite acts as the most potent feedforward activator of phosphofructokinase-1 (PFK-1), overriding high ATP inhibition?",
            "options": [
                {"id": "A", "text": "Fructose-2,6-bisphosphate"},
                {"id": "B", "text": "Citrate"},
                {"id": "C", "text": "Glucose-6-phosphate"},
                {"id": "D", "text": "Phosphoenolpyruvate"},
            ],
            "correct": "A",
            "explanation": "F2,6BP is synthesized by PFK-2 and is the primary physiological allosteric activator of PFK-1 in glycolysis.",
        },
        {
            "stem": "An oligopeptide has the sequence Glu-His-Trp-Ser-Gly-Leu-Arg-Pro-Gly. What is the approximate net charge of this peptide at physiological pH 7.4?",
            "options": [
                {"id": "A", "text": "0"},
                {"id": "B", "text": "+1"},
                {"id": "C", "text": "-1"},
                {"id": "D", "text": "+2"},
            ],
            "correct": "A",
            "explanation": "At pH 7.4: N-terminus (+1), C-terminus (-1), Glu (-1), His (~0 neutral), Arg (+1). Net charge = +1 - 1 - 1 + 1 = 0.",
        },
        {
            "stem": "In the mitochondrial citric acid cycle, which enzymatic reaction couples high-energy thioester bond cleavage directly to the substrate-level phosphorylation of GDP?",
            "options": [
                {"id": "A", "text": "Succinyl-CoA synthetase"},
                {"id": "B", "text": "Isocitrate dehydrogenase"},
                {"id": "C", "text": "α-Ketoglutarate dehydrogenase complex"},
                {"id": "D", "text": "Malate dehydrogenase"},
            ],
            "correct": "A",
            "explanation": "Succinyl-CoA synthetase (succinate thiokinase) converts succinyl-CoA and GDP + Pi to succinate and GTP.",
        },
        {
            "stem": "A reversible enzyme inhibitor increases the apparent Michaelis constant (Km) by a factor of 3 without altering the maximal reaction velocity (Vmax). What mode of inhibition does this molecule exhibit?",
            "options": [
                {"id": "A", "text": "Competitive inhibition"},
                {"id": "B", "text": "Non-competitive inhibition"},
                {"id": "C", "text": "Uncompetitive inhibition"},
                {"id": "D", "text": "Mixed inhibition"},
            ],
            "correct": "A",
            "explanation": "Competitive inhibitors bind only to the free enzyme, increasing apparent Km while Vmax remains attainable at high [S].",
        },
    ],
    "bio_biochem_passage": [
        {
            "stem": "In intestinal epithelial cells, Vibrio cholerae enterotoxin ADP-ribosylates the Gαs subunit. What enzymatic consequence directly causes massive chloride and fluid hypersecretion?",
            "options": [
                {
                    "id": "A",
                    "text": "Persistent activation of adenylyl cyclase leading to continuous PKA activation of CFTR channels",
                },
                {
                    "id": "B",
                    "text": "Immediate hydrolysis of GTP on Gαs leading to channel closure",
                },
                {"id": "C", "text": "Phosphorylation of phospholamban in intestinal smooth muscle"},
                {"id": "D", "text": "Blockade of apical sodium-glucose cotransporter SGLT1"},
            ],
            "correct": "A",
            "explanation": "ADP-ribosylation locks Gαs in its GTP-bound active state, causing unabated cAMP synthesis, PKA activation, and CFTR open probability.",
        },
        {
            "stem": "The intrinsic GTPase activity of Gα subunits functions physiologically as which of the following regulatory mechanisms?",
            "options": [
                {
                    "id": "A",
                    "text": "A built-in molecular timer that terminates receptor-initiated signaling",
                },
                {
                    "id": "B",
                    "text": "A catalyst that accelerates GDP dissociation from the inactive G-protein",
                },
                {
                    "id": "C",
                    "text": "An energy-generating step required for ATP synthesis by adenylyl cyclase",
                },
                {"id": "D", "text": "An allosteric inhibitor of β1-adrenergic GPCR ligand binding"},
            ],
            "correct": "A",
            "explanation": "GTP hydrolysis to GDP on Gα is an internal clock that turns off downstream effector stimulation and triggers reassociation with Gβγ.",
        },
        {
            "stem": "In cardiac myocytes, protein kinase A (PKA) phosphorylates phospholamban (PLN). How does this phosphorylation event affect myocardial calcium handling during diastole?",
            "options": [
                {
                    "id": "A",
                    "text": "It relieves inhibition of SERCA2a, accelerating cytosolic Ca2+ reuptake into the sarcoplasmic reticulum.",
                },
                {
                    "id": "B",
                    "text": "It inhibits SERCA2a, prolonging elevated cytosolic Ca2+ and delaying relaxation.",
                },
                {"id": "C", "text": "It directly closes L-type Ca2+ channels on the sarcolemma."},
                {
                    "id": "D",
                    "text": "It prevents ryanodine receptor (RyR2) opening during systole.",
                },
            ],
            "correct": "A",
            "explanation": "Unphosphorylated PLN inhibits SERCA2a. PKA phosphorylation disinhibits SERCA2a, speeding calcium reuptake and lusitropy.",
        },
        {
            "stem": "Following agonist dissociation from a GPCR, how is the inactive heterotrimeric G-protein complex reconstituted?",
            "options": [
                {"id": "A", "text": "GDP-bound Gα reassociates with the Gβγ heterodimer."},
                {"id": "B", "text": "GTP-bound Gα binds directly to β-arrestin for degradation."},
                {
                    "id": "C",
                    "text": "The Gβγ dimer is ubiquitinated and transported to the lysosome.",
                },
                {"id": "D", "text": "Adenylyl cyclase hydrolyzes remaining cAMP into 5'-AMP."},
            ],
            "correct": "A",
            "explanation": "Upon GTP hydrolysis, the resulting Gα-GDP has high affinity for Gβγ, reconstituting the basal heterotrimeric complex.",
        },
    ],
    "psych_soc_independent": [
        {
            "stem": "A gambler continues pulling the arm of a slot machine because payoffs occur after an unpredictable number of pulls. Which schedule of reinforcement maintains this high, steady rate of responding?",
            "options": [
                {"id": "A", "text": "Variable-ratio schedule"},
                {"id": "B", "text": "Fixed-interval schedule"},
                {"id": "C", "text": "Variable-interval schedule"},
                {"id": "D", "text": "Fixed-ratio schedule"},
            ],
            "correct": "A",
            "explanation": "Variable-ratio schedules deliver reinforcement after an unpredictable number of responses, generating high response rates resistant to extinction.",
        },
        {
            "stem": "When an unfamiliar driver cuts into traffic, an observer immediately concludes the driver is reckless and inconsiderate, ignoring the possibility that the driver is rushing to an emergency. This judgment demonstrates:",
            "options": [
                {"id": "A", "text": "The fundamental attribution error"},
                {"id": "B", "text": "The self-serving bias"},
                {"id": "C", "text": "The halo effect"},
                {"id": "D", "text": "The availability heuristic"},
            ],
            "correct": "A",
            "explanation": "The fundamental attribution error is the bias toward attributing others' behaviors to internal dispositional factors rather than situational pressures.",
        },
        {
            "stem": "According to Weber's Law, if an individual can just distinguish between weights of 100 g and 105 g, what is the minimum difference required to detect a change from a 300 g reference weight?",
            "options": [
                {"id": "A", "text": "15 g"},
                {"id": "B", "text": "5 g"},
                {"id": "C", "text": "10 g"},
                {"id": "D", "text": "30 g"},
            ],
            "correct": "A",
            "explanation": "Weber fraction = ΔI/I = 5/100 = 0.05. For 300 g: ΔI = 300 * 0.05 = 15 g.",
        },
        {
            "stem": "According to Erik Erikson's theory of psychosocial development, an older adult who reflects upon past choices with satisfaction and a sense of life fulfillment has successfully resolved the crisis of:",
            "options": [
                {"id": "A", "text": "Integrity vs. despair"},
                {"id": "B", "text": "Generativity vs. stagnation"},
                {"id": "C", "text": "Intimacy vs. isolation"},
                {"id": "D", "text": "Identity vs. role confusion"},
            ],
            "correct": "A",
            "explanation": "Late adulthood is characterized by integrity vs. despair, where resolution yields wisdom and acceptance of one's life.",
        },
    ],
    "psych_soc_passage": [
        {
            "stem": "In social psychology research utilizing the minimal group paradigm, what behavioral pattern is consistently observed even when group assignments are completely arbitrary?",
            "options": [
                {
                    "id": "A",
                    "text": "In-group favoritism and preferential resource allocation to in-group members",
                },
                {
                    "id": "B",
                    "text": "Immediate out-group assimilation and erasure of group boundaries",
                },
                {
                    "id": "C",
                    "text": "Equal distribution of resources across all participants regardless of affiliation",
                },
                {"id": "D", "text": "Increased cognitive dissonance and resistance to authority"},
            ],
            "correct": "A",
            "explanation": "Tajfel's minimal group studies demonstrate that mere categorization into groups triggers in-group favoritism and out-group discrimination.",
        },
        {
            "stem": "When female mathematics students are informed before a high-stakes exam that women typically underperform on the test, their test scores drop significantly. This phenomenon is known as:",
            "options": [
                {"id": "A", "text": "Stereotype threat"},
                {"id": "B", "text": "The Pygmalion effect"},
                {"id": "C", "text": "Social loafing"},
                {"id": "D", "text": "Group polarization"},
            ],
            "correct": "A",
            "explanation": "Stereotype threat occurs when awareness of a negative stereotype induces anxiety and impairs performance in the stereotyped domain.",
        },
        {
            "stem": "In a classic study of teacher expectancy, teachers were falsely told that certain students were intellectual 'late bloomers.' By the end of the year, those students made significant IQ gains. This outcome exemplifies:",
            "options": [
                {"id": "A", "text": "A self-fulfilling prophecy"},
                {"id": "B", "text": "The Thomas theorem"},
                {"id": "C", "text": "The Hawthorne effect"},
                {"id": "D", "text": "Social facilitation"},
            ],
            "correct": "A",
            "explanation": "The Pygmalion study shows how expectations lead to behavioral confirmation, fulfilling the initial false prophecy.",
        },
        {
            "stem": "In Erving Goffman's dramaturgical sociology, a surgeon who maintains strict professional composure in the operating room but vents emotional frustration to close colleagues in the private locker room is moving between:",
            "options": [
                {"id": "A", "text": "Front stage and back stage regions"},
                {"id": "B", "text": "Primary and secondary socialization agents"},
                {"id": "C", "text": "Role conflict and role strain"},
                {"id": "D", "text": "In-group and out-group memberships"},
            ],
            "correct": "A",
            "explanation": "Front stage involves public performance tailored to social expectations; back stage is the private zone where the performer can drop the mask.",
        },
    ],
}


def get_mock_draft(req: GenerationRequest) -> QuestionDraft:
    """Provides high-caliber, authentic fallback AAMC MCAT questions with resolved primary_trap and likely_mistake_pattern."""
    draft = _build_raw_mock_draft(req)

    # Determine item variant index from thematic angle
    variant_idx = 0
    if req.thematic_angle:
        match = re.search(r"item\s*(\d+)", req.thematic_angle, re.IGNORECASE)
        retry_match = re.search(r"retry\s*(\d+)", req.thematic_angle, re.IGNORECASE)
        attempt_match = re.search(r"attempt\s*(\d+)", req.thematic_angle, re.IGNORECASE)
        base_num = int(match.group(1)) if match else 1
        offset = 0
        if retry_match:
            offset += int(retry_match.group(1))
        if attempt_match:
            offset += int(attempt_match.group(1))
        variant_idx = (base_num - 1 + offset) % 5

    # If variant index > 0, swap in the corresponding unique authentic question
    if variant_idx > 0:
        sec = normalize_section(req.section)
        is_direct_independent = (
            req.passage_required is not None
            and str(req.passage_required).lower() in ("no", "false")
            and not (req.shared_stimulus and req.shared_stimulus.strip())
            and sec != MCATSection.CARS
        )
        sec_key = (
            "chem_phys"
            if sec == MCATSection.CHEM_PHYS
            else (
                "cars"
                if sec == MCATSection.CARS
                else ("bio_biochem" if sec == MCATSection.BIO_BIOCHEM else "psych_soc")
            )
        )
        type_key = "independent" if is_direct_independent else "passage"
        pool_key = f"{sec_key}_{type_key}"
        variants = _MOCK_QUESTION_VARIANTS.get(pool_key, [])
        if variants:
            v = variants[(variant_idx - 1) % len(variants)]
            draft.question_stem = v["stem"]
            draft.options = [OptionChoice(id=o["id"], text=o["text"]) for o in v["options"]]
            draft.correct_answer_id = v["correct"]
            draft.correct_answer_ids = [v["correct"]]
            draft.explanation = v["explanation"]

    # Determine or auto-detect primary trap
    if not draft.primary_trap or draft.primary_trap == "Automatic":
        if req.primary_trap and req.primary_trap != "Automatic":
            draft.primary_trap = req.primary_trap
        else:
            expl = draft.explanation or ""
            taxonomies = [
                ("Out_of_Scope", r"Out\s*of\s*Scope"),
                ("Distortion_Opposite", r"Distortion|Opposite"),
                ("Outside_Knowledge_in_CARS", r"Outside\s*Knowledge"),
                ("Extreme_Language", r"Extreme\s*(?:Language|Quantifier|Word)"),
                ("Correlation_vs_Causation", r"Correlation\s*(?:vs\.?|and)\s*Causation"),
                ("Calculation_Formula_Trap", r"Calculation|Formula"),
                ("Half_Right_False_Premise", r"Half-?Right|False\s*Premise"),
                ("Scope_Shift", r"Scope\s*Shift"),
            ]
            detected = None
            for trap_key, pattern in taxonomies:
                if re.search(pattern, expl, re.IGNORECASE):
                    detected = trap_key
                    break
            draft.primary_trap = detected or "Distortion_Opposite"

    # Determine or auto-detect student misconception / likely mistake pattern
    if req.likely_mistake_pattern and req.likely_mistake_pattern not in ("Automatic", ""):
        if req.likely_mistake_pattern == "None":
            draft.likely_mistake_pattern = None
        else:
            draft.likely_mistake_pattern = req.likely_mistake_pattern
    else:
        # Automatic (Smart AI Choice)
        draft.likely_mistake_pattern = (
            "Confuses external justification with intrinsic attitude alignment"
            if "dissonance" in (draft.question_stem or "").lower()
            else "Uses initial instead of final reference concentration in equilibrium expression"
        )

    return draft
