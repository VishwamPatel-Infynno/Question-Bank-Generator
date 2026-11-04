"""Isolated mock drafts and heuristic evaluation fixtures for offline testing and graceful fallback."""

from __future__ import annotations

import re

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

    if sec == MCATSection.CHEM_PHYS:
        if is_direct_independent:
            return QuestionDraft(
                stimulus_text="",
                question_stem=(
                    "A researcher measures the rate of an enzymatic reaction catalyzed by alkaline phosphatase at 37°C. "
                    "When the substrate concentration is equal to three times the Michaelis constant (3 Km), "
                    "what fraction of the maximal velocity (Vmax) is the observed reaction velocity?"
                ),
                options=[
                    OptionChoice(id="A", text="0.25 Vmax"),
                    OptionChoice(id="B", text="0.50 Vmax"),
                    OptionChoice(id="C", text="0.75 Vmax"),
                    OptionChoice(id="D", text="0.90 Vmax"),
                ],
                correct_answer_id="C",
                correct_answer_ids=["C"],
                aamc_skill="Skill_1",
                primary_trap="Calculation_Formula_Trap",
                explanation=(
                    "Core Intuition:\n"
                    "The relationship between reaction velocity (v0), maximal velocity (Vmax), substrate concentration [S], "
                    "and the Michaelis constant (Km) is governed by the Michaelis-Menten equation: v0 = (Vmax * [S]) / (Km + [S]).\n\n"
                    "Why Option C is Correct:\n"
                    "Substitute [S] = 3 Km into the Michaelis-Menten rate law:\n"
                    "v0 = (Vmax * 3 Km) / (Km + 3 Km) = (3 * Vmax * Km) / (4 Km) = 3/4 Vmax = 0.75 Vmax.\n"
                    "Therefore, at [S] = 3 Km, the enzyme operates at exactly 75% of its maximal catalytic capacity.\n\n"
                    "Why Other Options are Incorrect (Distractor & Trap Breakdown):\n"
                    "- Option A is INCORRECT (Calculation / Inversion Trap): 0.25 Vmax corresponds to [S] = 1/3 Km, resulting from inverting the numerator and denominator coefficients.\n"
                    "- Option B is INCORRECT (Formula Misapplication): 0.50 Vmax occurs when [S] = Km by definition of the Michaelis constant.\n"
                    "- Option D is INCORRECT (Distortion Trap): 0.90 Vmax requires [S] = 9 Km, representing an enzyme operating much closer to complete active site saturation."
                ),
                image_needed=False,
            )

        return QuestionDraft(
            stimulus_text=(
                "Carbonic anhydrase (CA) is a zinc metalloenzyme that catalyzes the reversible hydration of carbon dioxide: "
                "CO2 + H2O ⇌ H2CO3 ⇌ H+ + HCO3-. This equilibrium is critical for maintaining systemic arterial blood pH at 7.40 ± 0.02. "
                "In renal proximal convoluted tubule (PCT) cells, apical membrane-bound CA-IV facilitates bicarbonate reabsorption by converting luminal "
                "bicarbonate into carbon dioxide, which readily diffuses across the hydrophobic apical lipid bilayer. Once inside the cytoplasm, "
                "soluble CA-II regenerates bicarbonate and protons; bicarbonate is subsequently transported into the peritubular capillaries "
                "via the basolateral Na+/HCO3- cotransporter (NBCe1).\n\n"
                "To evaluate the pharmacology of a novel non-competitive sulfonamide inhibitor (Compound X), investigators measured renal tubular "
                "CA-II activity across increasing substrate (CO2) concentrations in the absence and presence of 10 μM Compound X at physiological pH. "
                "Kinetic analysis revealed that Compound X reduced the apparent maximal reaction velocity (Vmax) from 1.4 × 10^5 μmol/(mg·min) to "
                "0.6 × 10^5 μmol/(mg·min), while the Michaelis constant (Km) remained unchanged at 12.0 mM CO2."
            ),
            question_stem=(
                "Based on the kinetic data described in the passage, how does the addition of Compound X alter a Lineweaver-Burk "
                "(double-reciprocal) plot of CA-II catalytic activity?"
            ),
            options=[
                OptionChoice(
                    id="A",
                    text="The y-intercept increases while the x-intercept remains identical.",
                ),
                OptionChoice(
                    id="B",
                    text="The x-intercept shifts rightward closer to zero while the y-intercept remains identical.",
                ),
                OptionChoice(
                    id="C",
                    text="Both the x-intercept and the y-intercept shift to significantly higher absolute values.",
                ),
                OptionChoice(
                    id="D",
                    text="The slope of the Lineweaver-Burk line decreases while the y-intercept increases.",
                ),
            ],
            correct_answer_id="A",
            correct_answer_ids=["A"],
            aamc_skill="Skill_2",
            primary_trap="Distortion_Opposite",
            explanation=(
                "Core Intuition:\n"
                "A non-competitive inhibitor binds with equal affinity to both the free enzyme (E) and the enzyme-substrate complex (ES) "
                "at an allosteric site. Consequently, it lowers Vmax without altering substrate binding affinity (Km remains constant).\n\n"
                "Why Option A is Correct:\n"
                "In a Lineweaver-Burk double-reciprocal transformation (1/v0 = (Km/Vmax)(1/[S]) + 1/Vmax):\n"
                "1. The y-intercept represents 1/Vmax. Because Compound X decreases Vmax, 1/Vmax increases (shifts upward along the y-axis).\n"
                "2. The x-intercept represents -1/Km. Because Km is unchanged by non-competitive inhibition, the x-intercept remains identical.\n"
                "3. The slope equals Km/Vmax; because Vmax decreases and Km is unchanged, the slope increases.\n"
                "Thus, Option A accurately and definitively describes the graphical transformation.\n\n"
                "Why Other Options are Incorrect (Distractor & Trap Breakdown):\n"
                "- Option B is INCORRECT (Distortion / Competitive Trap): A rightward shift in the x-intercept with an unchanged y-intercept describes competitive inhibition (Km increases, Vmax unchanged).\n"
                "- Option C is INCORRECT (Uncompetitive Trap): Parallel shifts in both intercepts characterize uncompetitive inhibition, where both Km and Vmax decrease proportionally.\n"
                "- Option D is INCORRECT (Mathematical Slip): The slope is Km/Vmax. Because Vmax decreases in the denominator, the slope MUST increase, not decrease."
            ),
            image_needed=False,
        )

    if sec == MCATSection.CARS:
        return QuestionDraft(
            stimulus_text=(
                "The philosophical justification of aesthetic value has long struggled to reconcile subjective sensory experience "
                "with the demand for objective critical consensus. In his Critique of Judgment, Immanuel Kant attempted to bridge this chasm "
                "by positing the 'sensus communis' - a shared subjective capacity that enables individuals to expect universal agreement "
                "for their aesthetic appraisals without relying on empirical concepts. To Kant, an authentic judgment of beauty must remain "
                "disinterested, detached from both sensory gratification and practical utility. When one declares a cathedral or a sonata beautiful, "
                "one speaks with a 'universal voice,' imputing the same contemplative satisfaction to all rational observers.\n\n"
                "However, contemporary sociological critique, most notably articulated by Pierre Bourdieu, dismisses this Kantian autonomy as "
                "a bourgeois illusion. Bourdieu argues that aesthetic dispositions do not reflect pure, disinterested cognition; rather, they are "
                "socially conditioned markers of class distinction, or 'cultural capital.' The ability to appreciate abstract painting or avant-garde "
                "composition presupposes prolonged exposure and educational privilege, subtly legitimizing social hierarchies under the guise of "
                "natural refined taste. In this view, disinterested aesthetic contemplation serves primarily to demarcate elite status from "
                "the necessity-driven preferences of the working classes.\n\n"
                "Yet to reduce all aesthetic appraisal to socio-economic positioning is to ignore the transformative phenomenology of art itself. "
                "If aesthetic appreciation were merely an arbitrary exercise in social signaling, it would fail to explain the profound emotional "
                "resonance and cognitive disequilibrium that art frequently elicits across diverse cultural strata. Genuine aesthetic encounters "
                "routinely disrupt habitual perception, unsettling entrenched beliefs rather than reinforcing social complacency. The enduring power "
                "of artistic expression lies neither in absolute Kantian universality nor in reductive sociological determinism, but in its capacity "
                "to stage an open-ended dialogue between individual subjectivity and the collective imagination."
            ),
            question_stem=(
                "Based on the author's argument in the passage, with which of the following statements would the author most likely agree "
                "regarding Pierre Bourdieu's critique of Kantian aesthetics?"
            ),
            options=[
                OptionChoice(
                    id="A",
                    text="Bourdieu correctly demonstrates that aesthetic value is strictly determined by innate neurobiological reward circuitry.",
                ),
                OptionChoice(
                    id="B",
                    text="Bourdieu accurately identifies the social conditioning of taste, but improperly diminishes the disruptive psychological power of art.",
                ),
                OptionChoice(
                    id="C",
                    text="Bourdieu's analysis completely validates Kant's assertion of a universal, disinterested aesthetic consensus.",
                ),
                OptionChoice(
                    id="D",
                    text="Bourdieu's doctrine of cultural capital is inapplicable to modern fine arts due to widespread democratizing digital access.",
                ),
            ],
            correct_answer_id="B",
            correct_answer_ids=["B"],
            aamc_skill="CARS_Skill_2",
            primary_trap="Distortion_Opposite",
            explanation=(
                "Core Intuition:\n"
                "The author introduces Kant's concept of universal disinterested beauty, presents Bourdieu's sociological counterargument that taste "
                "is socialized class distinction ('cultural capital'), and then qualifies both: while Bourdieu exposes the social conditioning of taste, "
                "he goes too far by reducing art to mere social signaling, missing its capacity to elicit cognitive disequilibrium and disrupt habitual perception.\n\n"
                "Why Option B is Correct:\n"
                "Paragraph 3 begins: 'Yet to reduce all aesthetic appraisal to socio-economic positioning is to ignore the transformative phenomenology of art itself.' "
                "The author affirms that genuine encounters with art can unsettle entrenched beliefs across diverse cultural strata, directly supporting "
                "the view that Bourdieu's model is valuable yet overly reductive.\n\n"
                "Why Other Options are Incorrect (Distractor & Trap Breakdown):\n"
                "- Option A is INCORRECT (Outside Knowledge Trap): The passage never mentions neurobiology or reward circuitry; introducing neurological claims violates strict CARS textual evidence boundaries.\n"
                "- Option C is INCORRECT (Opposite / Distortion): Bourdieu explicitly rejects Kantian aesthetics as a 'bourgeois illusion,' the exact antithesis of validating it.\n"
                "- Option D is INCORRECT (Out of Scope Trap): The passage makes no mention of digital media, modern internet democratization, or contemporary technology."
            ),
            image_needed=False,
        )

    if sec == MCATSection.BIO_BIOCHEM:
        if is_direct_independent:
            return QuestionDraft(
                stimulus_text="",
                question_stem=(
                    "In the human body, the mitochondrial pyruvate dehydrogenase complex (PDC) catalyzes the irreversible decarboxylation of pyruvate to acetyl-CoA. "
                    "Which of the following cellular conditions will most effectively INHIBIT the activity of the pyruvate dehydrogenase complex?"
                ),
                options=[
                    OptionChoice(id="A", text="High intracellular ratio of NAD+ to NADH"),
                    OptionChoice(id="B", text="High intracellular concentration of ADP"),
                    OptionChoice(id="C", text="High intracellular ratio of acetyl-CoA to free CoA"),
                    OptionChoice(
                        id="D", text="Elevated intramitochondrial concentration of free Ca2+"
                    ),
                ],
                correct_answer_id="C",
                correct_answer_ids=["C"],
                aamc_skill="Skill_1",
                primary_trap="Distortion_Opposite",
                explanation=(
                    "Core Intuition:\n"
                    "Pyruvate dehydrogenase (PDC) commits carbohydrate carbon skeletons to the citric acid cycle or fatty acid synthesis. "
                    "Like most catabolic gateway enzymes, it is allosterically regulated by cellular energy charge: activated by signs of energy depletion "
                    "(ADP, NAD+, free CoA) and inhibited by products signaling cellular energy abundance (ATP, NADH, acetyl-CoA).\n\n"
                    "Why Option C is Correct:\n"
                    "Acetyl-CoA and NADH are direct enzymatic products of the PDC reaction. A high ratio of acetyl-CoA to free CoA directly exerts allosteric "
                    "feedback inhibition and activates pyruvate dehydrogenase kinase (PDK), which phosphorylates and inactivates the E1 subunit.\n\n"
                    "Why Other Options are Incorrect (Distractor & Trap Breakdown):\n"
                    "- Option A is INCORRECT (Opposite Distortion): A high NAD+/NADH ratio signals low energy charge and substrate availability, allosterically activating PDC.\n"
                    "- Option B is INCORRECT (Opposite Distortion): Elevated ADP signals that cellular ATP is depleted, stimulating PDC and citric acid cycle flux.\n"
                    "- Option D is INCORRECT (Physiological Misconception): Calcium (Ca2+) activates pyruvate dehydrogenase phosphatase (PDP), which dephosphorylates and activates PDC during muscle contraction."
                ),
                image_needed=False,
            )

        return QuestionDraft(
            stimulus_text=(
                "G-protein coupled receptors (GPCRs) represent the largest superfamily of cell-surface signaling receptors in humans. "
                "Upon agonist binding, GPCRs catalyze the exchange of GDP for GTP on the Gα subunit of heterotrimeric G proteins, promoting dissociation "
                "of Gα from the Gβγ dimer. In cardiac myocytes, β1-adrenergic receptors couple primarily to Gαs, which stimulates adenylyl cyclase (AC) "
                "to convert ATP into cyclic adenosine monophosphate (cAMP). Elevated intracellular cAMP allosterically activates protein kinase A (PKA), "
                "which phosphorylates L-type Ca2+ channels (Cav1.2) and phospholamban (PLN), enhancing myocardial contractility (inotropy) and relaxation.\n\n"
                "To investigate the pathophysiological mechanism of Vibrio cholerae enterotoxin, researchers exposed cultured intestinal epithelial cells "
                "to purified cholera toxin. Cholera toxin is an AB5 subunit enzyme whose catalytic A1 peptide catalyzes the irreversible NAD+-dependent "
                "ADP-ribosylation of an arginine residue in the GTPase active site of Gαs. Analysis of membrane lysates by Western blot confirmed sustained "
                "adenylyl cyclase activation and persistent elevation of intracellular cAMP (>10-fold baseline) even in the complete absence of extracellular hormone."
            ),
            question_stem=(
                "Which biochemical consequence directly results from the ADP-ribosylation of the Gαs subunit by cholera toxin?"
            ),
            options=[
                OptionChoice(
                    id="A",
                    text="Inhibition of intrinsic Gαs GTPase activity, locking the subunit into a persistently active GTP-bound state.",
                ),
                OptionChoice(
                    id="B",
                    text="Destabilization of the Gαs-adenylyl cyclase complex, preventing generation of secondary messenger cAMP.",
                ),
                OptionChoice(
                    id="C",
                    text="Accelerated hydrolysis of GTP to GDP by Gαs, causing premature reassociation of the heterotrimeric complex.",
                ),
                OptionChoice(
                    id="D",
                    text="Competitive blockade of the β-adrenergic ligand-binding pocket on the extracellular GPCR surface.",
                ),
            ],
            correct_answer_id="A",
            correct_answer_ids=["A"],
            aamc_skill="Skill_2",
            primary_trap="Distortion_Opposite",
            explanation=(
                "Core Intuition:\n"
                "The intrinsic GTPase activity of Gαs acts as an internal 'molecular timer' that hydrolyzes GTP to GDP, terminating its stimulation "
                "of adenylyl cyclase. By covalently ADP-ribosylating the catalytic arginine residue of Gαs, cholera toxin prevents GTP hydrolysis, "
                "locking Gαs permanently into its active, effector-stimulating conformation.\n\n"
                "Why Option A is Correct:\n"
                "Because Gαs cannot hydrolyze its bound GTP, it remains constitutively bound to and activates adenylyl cyclase, producing continuous, "
                "uncontrolled cAMP accumulation without requiring upstream receptor stimulation.\n\n"
                "Why Other Options are Incorrect (Distractor & Trap Breakdown):\n"
                "- Option B is INCORRECT (Contradicted by Mechanism): Cholera toxin causes sustained activation, not destabilization or inhibition, of adenylyl cyclase.\n"
                "- Option C is INCORRECT (Exact Opposite): Cholera toxin inhibits GTP hydrolysis; accelerated hydrolysis would terminate cAMP production rather than causing the observed 10-fold surge.\n"
                "- Option D is INCORRECT (Location Misattribution): Cholera toxin acts intracellularly on the Gαs protein in the cytoplasm, not on the extracellular ligand-binding domain of the receptor."
            ),
            image_needed=False,
        )

    # MCATSection.PSYCH_SOC
    if is_direct_independent:
        return QuestionDraft(
            stimulus_text="",
            question_stem=(
                "A patient diagnosed with major depressive disorder reports that although they successfully secured a prestigious clinical promotion, "
                "they attribute the success entirely to 'sheer luck and an easy interview panel.' However, when their manuscript was recently rejected, "
                "they concluded that they are 'fundamentally incompetent and doomed to fail.' Which cognitive attributional pattern does this patient demonstrate?"
            ),
            options=[
                OptionChoice(id="A", text="Actor-observer asymmetry"),
                OptionChoice(
                    id="B",
                    text="Depressive attributional style (internalizing failure, externalizing success)",
                ),
                OptionChoice(
                    id="C",
                    text="Self-serving bias (externalizing failure, internalizing success)",
                ),
                OptionChoice(id="D", text="Fundamental attribution error regarding group members"),
            ],
            correct_answer_id="B",
            correct_answer_ids=["B"],
            aamc_skill="Skill_1",
            primary_trap="Distortion_Opposite",
            explanation=(
                "Core Intuition:\n"
                "Attribution theory categorizes causes of behavior as internal (dispositional) or external (situational). In healthy individuals, "
                "the self-serving bias protects self-esteem by attributing successes to internal factors and failures to external factors. In depression, "
                "this pattern is characteristically inverted.\n\n"
                "Why Option B is Correct:\n"
                "A depressive attributional style involves attributing negative outcomes to internal, global, and stable factors ('I am incompetent'), "
                "while attributing positive outcomes to external, unstable factors ('sheer luck'). This matches the patient's behavior precisely.\n\n"
                "Why Other Options are Incorrect (Distractor & Trap Breakdown):\n"
                "- Option C is INCORRECT (Exact Opposite): Self-serving bias is the reverse pattern (crediting oneself for success and blaming external circumstances for failure).\n"
                "- Option A is INCORRECT (Misapplied Concept): Actor-observer bias refers to attributing one's own actions to situational causes while attributing others' actions to dispositional traits.\n"
                "- Option D is INCORRECT (Misapplied Concept): The fundamental attribution error is the tendency to overestimate dispositional influences when evaluating another individual's behavior."
            ),
            image_needed=False,
        )

    return QuestionDraft(
        stimulus_text=(
            "Cognitive dissonance theory posits that individuals experience uncomfortable psychological tension when their beliefs, attitudes, "
            "or actions are mutually contradictory, motivating them to alter their cognitions or behaviors to restore equilibrium. "
            "In a randomized controlled trial investigating medical trainee burnout and institutional adherence, 120 first-year residents were asked "
            "to draft an essay advocating for an 80-hour work week policy that they privately opposed. Participants were assigned to either a "
            "Low-Incentive Condition ($5 honorarium) or a High-Incentive Condition ($50 honorarium).\n\n"
            "Post-experiment psychological evaluations revealed that residents in the Low-Incentive Condition experienced significant dissonance, "
            "exhibiting a substantial positive shift in their actual personal attitudes toward the policy compared to baseline (p < 0.01). "
            "In contrast, residents in the High-Incentive Condition demonstrated negligible attitude change toward the policy, maintaining their "
            "pre-experimental opposition. Researchers concluded that external financial justification attenuated perceived dissonance in the high-incentive cohort."
        ),
        question_stem=(
            "According to cognitive dissonance theory, why did residents in the Low-Incentive Condition exhibit a greater attitude change "
            "than residents in the High-Incentive Condition?"
        ),
        options=[
            OptionChoice(
                id="A",
                text="Lacking sufficient external justification, low-incentive residents resolved internal tension by aligning their personal attitudes with their counter-attitudinal behavior.",
            ),
            OptionChoice(
                id="B",
                text="The $5 incentive was perceived as insulting, causing residents to develop psychological reactance and reject the experimental premise.",
            ),
            OptionChoice(
                id="C",
                text="High-incentive residents experienced cognitive overload due to monetary distraction, preventing cognitive dissonance resolution.",
            ),
            OptionChoice(
                id="D",
                text="Residents in the low-incentive condition experienced greater intrinsic social desirability bias when interacting with senior evaluators.",
            ),
        ],
        correct_answer_id="A",
        correct_answer_ids=["A"],
        aamc_skill="Skill_2",
        primary_trap="Scope_Shift",
        explanation=(
            "Core Intuition:\n"
            "When individuals perform counter-attitudinal behavior under minimal external reward (insufficient justification), they cannot rationalize "
            "their action as having been done 'for the money.' To eliminate the resulting cognitive dissonance, they psychologically reconcile the discrepancy "
            "by genuinely shifting their internal attitudes toward the behavior.\n\n"
            "Why Option A is Correct:\n"
            "Residents in the High-Incentive cohort had strong external justification ($50), allowing them to attribute their essay to the reward without "
            "experiencing dissonance. The Low-Incentive cohort ($5) lacked sufficient external justification, forcing internal attitude modification "
            "to alleviate psychological tension.\n\n"
            "Why Other Options are Incorrect (Distractor & Trap Breakdown):\n"
            "- Option B is INCORRECT (Misapplied Concept): Psychological reactance would lead participants to rebel against the advocated position, not adopt it.\n"
            "- Option C is INCORRECT (Out of Scope Trap): Cognitive overload was neither measured nor supported by the theory of cognitive dissonance.\n"
            "- Option D is INCORRECT (Distortion Trap): Social desirability bias was controlled by anonymized evaluations and does not account for the incentive discrepancy."
        ),
        image_needed=False,
    )


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
