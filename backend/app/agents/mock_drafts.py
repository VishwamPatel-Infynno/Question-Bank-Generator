"""Canned AAMC-style drafts used offline and as a graceful fallback, one per (section, independent) key.

Keys are ``(MCATSection value, is_direct_independent)``; CARS is strictly passage-based so it has
no independent variant. Each value is the keyword set of a ``QuestionDraft``.
"""

from __future__ import annotations

from typing import Any

MOCK_DRAFTS: dict[tuple[str, bool], dict[str, Any]] = {
    ("chem_phys", False): {
        "stimulus_text": "Carbonic anhydrase (CA) is a zinc metalloenzyme that catalyzes the reversible hydration of carbon dioxide: CO2 + H2O ⇌ H2CO3 ⇌ H+ + HCO3-. This equilibrium is critical for maintaining systemic arterial blood pH at 7.40 ± 0.02. In renal proximal convoluted tubule (PCT) cells, apical membrane-bound CA-IV facilitates bicarbonate reabsorption by converting luminal bicarbonate into carbon dioxide, which readily diffuses across the hydrophobic apical lipid bilayer. Once inside the cytoplasm, soluble CA-II regenerates bicarbonate and protons; bicarbonate is subsequently transported into the peritubular capillaries via the basolateral Na+/HCO3- cotransporter (NBCe1).\n\nTo evaluate the pharmacology of a novel non-competitive sulfonamide inhibitor (Compound X), investigators measured renal tubular CA-II activity across increasing substrate (CO2) concentrations in the absence and presence of 10 μM Compound X at physiological pH. Kinetic analysis revealed that Compound X reduced the apparent maximal reaction velocity (Vmax) from 1.4 × 10^5 μmol/(mg·min) to 0.6 × 10^5 μmol/(mg·min), while the Michaelis constant (Km) remained unchanged at 12.0 mM CO2.",
        "question_stem": "Based on the kinetic data described in the passage, how does the addition of Compound X alter a Lineweaver-Burk (double-reciprocal) plot of CA-II catalytic activity?",
        "options": [
            {
                "id": "A",
                "text": "The y-intercept increases while the x-intercept remains identical.",
            },
            {
                "id": "B",
                "text": "The x-intercept shifts rightward closer to zero while the y-intercept remains identical.",
            },
            {
                "id": "C",
                "text": "Both the x-intercept and the y-intercept shift to significantly higher absolute values.",
            },
            {
                "id": "D",
                "text": "The slope of the Lineweaver-Burk line decreases while the y-intercept increases.",
            },
        ],
        "correct_answer_id": "A",
        "explanation": "Core Intuition:\nA non-competitive inhibitor binds with equal affinity to both the free enzyme (E) and the enzyme-substrate complex (ES) at an allosteric site. Consequently, it lowers Vmax without altering substrate binding affinity (Km remains constant).\n\nWhy Option A is Correct:\nIn a Lineweaver-Burk double-reciprocal transformation (1/v0 = (Km/Vmax)(1/[S]) + 1/Vmax):\n1. The y-intercept represents 1/Vmax. Because Compound X decreases Vmax, 1/Vmax increases (shifts upward along the y-axis).\n2. The x-intercept represents -1/Km. Because Km is unchanged by non-competitive inhibition, the x-intercept remains identical.\n3. The slope equals Km/Vmax; because Vmax decreases and Km is unchanged, the slope increases.\nThus, Option A accurately and definitively describes the graphical transformation.\n\nWhy Other Options are Incorrect (Distractor & Trap Breakdown):\n- Option B is INCORRECT (Distortion / Competitive Trap): A rightward shift in the x-intercept with an unchanged y-intercept describes competitive inhibition (Km increases, Vmax unchanged).\n- Option C is INCORRECT (Uncompetitive Trap): Parallel shifts in both intercepts characterize uncompetitive inhibition, where both Km and Vmax decrease proportionally.\n- Option D is INCORRECT (Mathematical Slip): The slope is Km/Vmax. Because Vmax decreases in the denominator, the slope MUST increase, not decrease.",
        "image_needed": False,
        "primary_trap": "Distortion_Opposite",
        "aamc_skill": "Skill_2",
    },
    ("chem_phys", True): {
        "stimulus_text": "",
        "question_stem": "A researcher measures the rate of an enzymatic reaction catalyzed by alkaline phosphatase at 37°C. When the substrate concentration is equal to three times the Michaelis constant (3 Km), what fraction of the maximal velocity (Vmax) is the observed reaction velocity?",
        "options": [
            {
                "id": "A",
                "text": "0.25 Vmax",
            },
            {
                "id": "B",
                "text": "0.50 Vmax",
            },
            {
                "id": "C",
                "text": "0.75 Vmax",
            },
            {
                "id": "D",
                "text": "0.90 Vmax",
            },
        ],
        "correct_answer_id": "C",
        "explanation": "Core Intuition:\nThe relationship between reaction velocity (v0), maximal velocity (Vmax), substrate concentration [S], and the Michaelis constant (Km) is governed by the Michaelis-Menten equation: v0 = (Vmax * [S]) / (Km + [S]).\n\nWhy Option C is Correct:\nSubstitute [S] = 3 Km into the Michaelis-Menten rate law:\nv0 = (Vmax * 3 Km) / (Km + 3 Km) = (3 * Vmax * Km) / (4 Km) = 3/4 Vmax = 0.75 Vmax.\nTherefore, at [S] = 3 Km, the enzyme operates at exactly 75% of its maximal catalytic capacity.\n\nWhy Other Options are Incorrect (Distractor & Trap Breakdown):\n- Option A is INCORRECT (Calculation / Inversion Trap): 0.25 Vmax corresponds to [S] = 1/3 Km, resulting from inverting the numerator and denominator coefficients.\n- Option B is INCORRECT (Formula Misapplication): 0.50 Vmax occurs when [S] = Km by definition of the Michaelis constant.\n- Option D is INCORRECT (Distortion Trap): 0.90 Vmax requires [S] = 9 Km, representing an enzyme operating much closer to complete active site saturation.",
        "image_needed": False,
        "primary_trap": "Calculation_Formula_Trap",
        "aamc_skill": "Skill_1",
    },
    ("cars", False): {
        "stimulus_text": "The philosophical justification of aesthetic value has long struggled to reconcile subjective sensory experience with the demand for objective critical consensus. In his Critique of Judgment, Immanuel Kant attempted to bridge this chasm by positing the 'sensus communis' - a shared subjective capacity that enables individuals to expect universal agreement for their aesthetic appraisals without relying on empirical concepts. To Kant, an authentic judgment of beauty must remain disinterested, detached from both sensory gratification and practical utility. When one declares a cathedral or a sonata beautiful, one speaks with a 'universal voice,' imputing the same contemplative satisfaction to all rational observers.\n\nHowever, contemporary sociological critique, most notably articulated by Pierre Bourdieu, dismisses this Kantian autonomy as a bourgeois illusion. Bourdieu argues that aesthetic dispositions do not reflect pure, disinterested cognition; rather, they are socially conditioned markers of class distinction, or 'cultural capital.' The ability to appreciate abstract painting or avant-garde composition presupposes prolonged exposure and educational privilege, subtly legitimizing social hierarchies under the guise of natural refined taste. In this view, disinterested aesthetic contemplation serves primarily to demarcate elite status from the necessity-driven preferences of the working classes.\n\nYet to reduce all aesthetic appraisal to socio-economic positioning is to ignore the transformative phenomenology of art itself. If aesthetic appreciation were merely an arbitrary exercise in social signaling, it would fail to explain the profound emotional resonance and cognitive disequilibrium that art frequently elicits across diverse cultural strata. Genuine aesthetic encounters routinely disrupt habitual perception, unsettling entrenched beliefs rather than reinforcing social complacency. The enduring power of artistic expression lies neither in absolute Kantian universality nor in reductive sociological determinism, but in its capacity to stage an open-ended dialogue between individual subjectivity and the collective imagination.",
        "question_stem": "Based on the author's argument in the passage, with which of the following statements would the author most likely agree regarding Pierre Bourdieu's critique of Kantian aesthetics?",
        "options": [
            {
                "id": "A",
                "text": "Bourdieu correctly demonstrates that aesthetic value is strictly determined by innate neurobiological reward circuitry.",
            },
            {
                "id": "B",
                "text": "Bourdieu accurately identifies the social conditioning of taste, but improperly diminishes the disruptive psychological power of art.",
            },
            {
                "id": "C",
                "text": "Bourdieu's analysis completely validates Kant's assertion of a universal, disinterested aesthetic consensus.",
            },
            {
                "id": "D",
                "text": "Bourdieu's doctrine of cultural capital is inapplicable to modern fine arts due to widespread democratizing digital access.",
            },
        ],
        "correct_answer_id": "B",
        "explanation": "Core Intuition:\nThe author introduces Kant's concept of universal disinterested beauty, presents Bourdieu's sociological counterargument that taste is socialized class distinction ('cultural capital'), and then qualifies both: while Bourdieu exposes the social conditioning of taste, he goes too far by reducing art to mere social signaling, missing its capacity to elicit cognitive disequilibrium and disrupt habitual perception.\n\nWhy Option B is Correct:\nParagraph 3 begins: 'Yet to reduce all aesthetic appraisal to socio-economic positioning is to ignore the transformative phenomenology of art itself.' The author affirms that genuine encounters with art can unsettle entrenched beliefs across diverse cultural strata, directly supporting the view that Bourdieu's model is valuable yet overly reductive.\n\nWhy Other Options are Incorrect (Distractor & Trap Breakdown):\n- Option A is INCORRECT (Outside Knowledge Trap): The passage never mentions neurobiology or reward circuitry; introducing neurological claims violates strict CARS textual evidence boundaries.\n- Option C is INCORRECT (Opposite / Distortion): Bourdieu explicitly rejects Kantian aesthetics as a 'bourgeois illusion,' the exact antithesis of validating it.\n- Option D is INCORRECT (Out of Scope Trap): The passage makes no mention of digital media, modern internet democratization, or contemporary technology.",
        "image_needed": False,
        "primary_trap": "Distortion_Opposite",
        "aamc_skill": "CARS_Skill_2",
    },
    ("bio_biochem", False): {
        "stimulus_text": "G-protein coupled receptors (GPCRs) represent the largest superfamily of cell-surface signaling receptors in humans. Upon agonist binding, GPCRs catalyze the exchange of GDP for GTP on the Gα subunit of heterotrimeric G proteins, promoting dissociation of Gα from the Gβγ dimer. In cardiac myocytes, β1-adrenergic receptors couple primarily to Gαs, which stimulates adenylyl cyclase (AC) to convert ATP into cyclic adenosine monophosphate (cAMP). Elevated intracellular cAMP allosterically activates protein kinase A (PKA), which phosphorylates L-type Ca2+ channels (Cav1.2) and phospholamban (PLN), enhancing myocardial contractility (inotropy) and relaxation.\n\nTo investigate the pathophysiological mechanism of Vibrio cholerae enterotoxin, researchers exposed cultured intestinal epithelial cells to purified cholera toxin. Cholera toxin is an AB5 subunit enzyme whose catalytic A1 peptide catalyzes the irreversible NAD+-dependent ADP-ribosylation of an arginine residue in the GTPase active site of Gαs. Analysis of membrane lysates by Western blot confirmed sustained adenylyl cyclase activation and persistent elevation of intracellular cAMP (>10-fold baseline) even in the complete absence of extracellular hormone.",
        "question_stem": "Which biochemical consequence directly results from the ADP-ribosylation of the Gαs subunit by cholera toxin?",
        "options": [
            {
                "id": "A",
                "text": "Inhibition of intrinsic Gαs GTPase activity, locking the subunit into a persistently active GTP-bound state.",
            },
            {
                "id": "B",
                "text": "Destabilization of the Gαs-adenylyl cyclase complex, preventing generation of secondary messenger cAMP.",
            },
            {
                "id": "C",
                "text": "Accelerated hydrolysis of GTP to GDP by Gαs, causing premature reassociation of the heterotrimeric complex.",
            },
            {
                "id": "D",
                "text": "Competitive blockade of the β-adrenergic ligand-binding pocket on the extracellular GPCR surface.",
            },
        ],
        "correct_answer_id": "A",
        "explanation": "Core Intuition:\nThe intrinsic GTPase activity of Gαs acts as an internal 'molecular timer' that hydrolyzes GTP to GDP, terminating its stimulation of adenylyl cyclase. By covalently ADP-ribosylating the catalytic arginine residue of Gαs, cholera toxin prevents GTP hydrolysis, locking Gαs permanently into its active, effector-stimulating conformation.\n\nWhy Option A is Correct:\nBecause Gαs cannot hydrolyze its bound GTP, it remains constitutively bound to and activates adenylyl cyclase, producing continuous, uncontrolled cAMP accumulation without requiring upstream receptor stimulation.\n\nWhy Other Options are Incorrect (Distractor & Trap Breakdown):\n- Option B is INCORRECT (Contradicted by Mechanism): Cholera toxin causes sustained activation, not destabilization or inhibition, of adenylyl cyclase.\n- Option C is INCORRECT (Exact Opposite): Cholera toxin inhibits GTP hydrolysis; accelerated hydrolysis would terminate cAMP production rather than causing the observed 10-fold surge.\n- Option D is INCORRECT (Location Misattribution): Cholera toxin acts intracellularly on the Gαs protein in the cytoplasm, not on the extracellular ligand-binding domain of the receptor.",
        "image_needed": False,
        "primary_trap": "Distortion_Opposite",
        "aamc_skill": "Skill_2",
    },
    ("bio_biochem", True): {
        "stimulus_text": "",
        "question_stem": "In the human body, the mitochondrial pyruvate dehydrogenase complex (PDC) catalyzes the irreversible decarboxylation of pyruvate to acetyl-CoA. Which of the following cellular conditions will most effectively INHIBIT the activity of the pyruvate dehydrogenase complex?",
        "options": [
            {
                "id": "A",
                "text": "High intracellular ratio of NAD+ to NADH",
            },
            {
                "id": "B",
                "text": "High intracellular concentration of ADP",
            },
            {
                "id": "C",
                "text": "High intracellular ratio of acetyl-CoA to free CoA",
            },
            {
                "id": "D",
                "text": "Elevated intramitochondrial concentration of free Ca2+",
            },
        ],
        "correct_answer_id": "C",
        "explanation": "Core Intuition:\nPyruvate dehydrogenase (PDC) commits carbohydrate carbon skeletons to the citric acid cycle or fatty acid synthesis. Like most catabolic gateway enzymes, it is allosterically regulated by cellular energy charge: activated by signs of energy depletion (ADP, NAD+, free CoA) and inhibited by products signaling cellular energy abundance (ATP, NADH, acetyl-CoA).\n\nWhy Option C is Correct:\nAcetyl-CoA and NADH are direct enzymatic products of the PDC reaction. A high ratio of acetyl-CoA to free CoA directly exerts allosteric feedback inhibition and activates pyruvate dehydrogenase kinase (PDK), which phosphorylates and inactivates the E1 subunit.\n\nWhy Other Options are Incorrect (Distractor & Trap Breakdown):\n- Option A is INCORRECT (Opposite Distortion): A high NAD+/NADH ratio signals low energy charge and substrate availability, allosterically activating PDC.\n- Option B is INCORRECT (Opposite Distortion): Elevated ADP signals that cellular ATP is depleted, stimulating PDC and citric acid cycle flux.\n- Option D is INCORRECT (Physiological Misconception): Calcium (Ca2+) activates pyruvate dehydrogenase phosphatase (PDP), which dephosphorylates and activates PDC during muscle contraction.",
        "image_needed": False,
        "primary_trap": "Distortion_Opposite",
        "aamc_skill": "Skill_1",
    },
    ("psych_soc", False): {
        "stimulus_text": "Cognitive dissonance theory posits that individuals experience uncomfortable psychological tension when their beliefs, attitudes, or actions are mutually contradictory, motivating them to alter their cognitions or behaviors to restore equilibrium. In a randomized controlled trial investigating medical trainee burnout and institutional adherence, 120 first-year residents were asked to draft an essay advocating for an 80-hour work week policy that they privately opposed. Participants were assigned to either a Low-Incentive Condition ($5 honorarium) or a High-Incentive Condition ($50 honorarium).\n\nPost-experiment psychological evaluations revealed that residents in the Low-Incentive Condition experienced significant dissonance, exhibiting a substantial positive shift in their actual personal attitudes toward the policy compared to baseline (p < 0.01). In contrast, residents in the High-Incentive Condition demonstrated negligible attitude change toward the policy, maintaining their pre-experimental opposition. Researchers concluded that external financial justification attenuated perceived dissonance in the high-incentive cohort.",
        "question_stem": "According to cognitive dissonance theory, why did residents in the Low-Incentive Condition exhibit a greater attitude change than residents in the High-Incentive Condition?",
        "options": [
            {
                "id": "A",
                "text": "Lacking sufficient external justification, low-incentive residents resolved internal tension by aligning their personal attitudes with their counter-attitudinal behavior.",
            },
            {
                "id": "B",
                "text": "The $5 incentive was perceived as insulting, causing residents to develop psychological reactance and reject the experimental premise.",
            },
            {
                "id": "C",
                "text": "High-incentive residents experienced cognitive overload due to monetary distraction, preventing cognitive dissonance resolution.",
            },
            {
                "id": "D",
                "text": "Residents in the low-incentive condition experienced greater intrinsic social desirability bias when interacting with senior evaluators.",
            },
        ],
        "correct_answer_id": "A",
        "explanation": "Core Intuition:\nWhen individuals perform counter-attitudinal behavior under minimal external reward (insufficient justification), they cannot rationalize their action as having been done 'for the money.' To eliminate the resulting cognitive dissonance, they psychologically reconcile the discrepancy by genuinely shifting their internal attitudes toward the behavior.\n\nWhy Option A is Correct:\nResidents in the High-Incentive cohort had strong external justification ($50), allowing them to attribute their essay to the reward without experiencing dissonance. The Low-Incentive cohort ($5) lacked sufficient external justification, forcing internal attitude modification to alleviate psychological tension.\n\nWhy Other Options are Incorrect (Distractor & Trap Breakdown):\n- Option B is INCORRECT (Misapplied Concept): Psychological reactance would lead participants to rebel against the advocated position, not adopt it.\n- Option C is INCORRECT (Out of Scope Trap): Cognitive overload was neither measured nor supported by the theory of cognitive dissonance.\n- Option D is INCORRECT (Distortion Trap): Social desirability bias was controlled by anonymized evaluations and does not account for the incentive discrepancy.",
        "image_needed": False,
        "primary_trap": "Scope_Shift",
        "aamc_skill": "Skill_2",
    },
    ("psych_soc", True): {
        "stimulus_text": "",
        "question_stem": "A patient diagnosed with major depressive disorder reports that although they successfully secured a prestigious clinical promotion, they attribute the success entirely to 'sheer luck and an easy interview panel.' However, when their manuscript was recently rejected, they concluded that they are 'fundamentally incompetent and doomed to fail.' Which cognitive attributional pattern does this patient demonstrate?",
        "options": [
            {
                "id": "A",
                "text": "Actor-observer asymmetry",
            },
            {
                "id": "B",
                "text": "Depressive attributional style (internalizing failure, externalizing success)",
            },
            {
                "id": "C",
                "text": "Self-serving bias (externalizing failure, internalizing success)",
            },
            {
                "id": "D",
                "text": "Fundamental attribution error regarding group members",
            },
        ],
        "correct_answer_id": "B",
        "explanation": "Core Intuition:\nAttribution theory categorizes causes of behavior as internal (dispositional) or external (situational). In healthy individuals, the self-serving bias protects self-esteem by attributing successes to internal factors and failures to external factors. In depression, this pattern is characteristically inverted.\n\nWhy Option B is Correct:\nA depressive attributional style involves attributing negative outcomes to internal, global, and stable factors ('I am incompetent'), while attributing positive outcomes to external, unstable factors ('sheer luck'). This matches the patient's behavior precisely.\n\nWhy Other Options are Incorrect (Distractor & Trap Breakdown):\n- Option C is INCORRECT (Exact Opposite): Self-serving bias is the reverse pattern (crediting oneself for success and blaming external circumstances for failure).\n- Option A is INCORRECT (Misapplied Concept): Actor-observer bias refers to attributing one's own actions to situational causes while attributing others' actions to dispositional traits.\n- Option D is INCORRECT (Misapplied Concept): The fundamental attribution error is the tendency to overestimate dispositional influences when evaluating another individual's behavior.",
        "image_needed": False,
        "primary_trap": "Distortion_Opposite",
        "aamc_skill": "Skill_1",
    },
}
