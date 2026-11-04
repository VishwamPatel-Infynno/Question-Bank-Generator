import asyncio
import logging

from app.db.session import init_db
from app.repositories import save_question
from app.schemas import OptionChoice, Question

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


async def seed():
    """Seeds publication-grade authentic AAMC MCAT questions across all 4 sections with complete relational linkage."""
    await init_db()

    batch_id = "batch-seed-mcat-2026"

    q1 = Question(
        id="q-seed-chem-phys-01",
        section="chem_phys",
        section_label="Chemical and Physical Foundations of Biological Systems",
        subtopic="Thermodynamics & Kinetics (Enthalpy, Entropy & Reaction Rates)",
        difficulty="Medium",
        passage_id="passage-seed-chem-phys-01",
        passage_mode="single_passage",
        batch_id=batch_id,
        mcat_scaled_score=130,
        aamc_skill="Skill_1_Knowledge_of_Scientific_Concepts",
        subject="Biochemistry",
        unit="Enzymology & Bioenergetics",
        topic="Enzyme Kinetics & Inhibition",
        subskill="Interpretation of Lineweaver-Burk Plots",
        likely_mistake_pattern="Inverting reciprocal x-axis intercepts when evaluating competitive vs noncompetitive inhibition",
        stimulus_text=(
            "Lactate dehydrogenase (LDH) catalyzes the reversible conversion of pyruvate to L-lactate with "
            "concomitant oxidation of NADH to NAD+. In an enzymatic study evaluating metabolic regulation, "
            "researchers characterized the kinetic inhibition of mammalian LDH by oxamate, a structural analog "
            "of pyruvate. Lineweaver-Burk double-reciprocal plots revealed that in the presence of increasing "
            "oxamate concentrations, the y-intercept remained identical to the uninhibited control, while the "
            "x-intercept shifted progressively closer to the origin."
        ),
        question_stem="Based on the Lineweaver-Burk kinetic data presented, what effect does oxamate exert on the kinetic parameters of lactate dehydrogenase?",
        options=[
            OptionChoice(
                id="A",
                text="Increases the apparent Km while leaving Vmax unchanged.",
            ),
            OptionChoice(
                id="B",
                text="Decreases the apparent Km while leaving Vmax unchanged.",
            ),
            OptionChoice(
                id="C",
                text="Decreases Vmax while leaving the apparent Km unchanged.",
            ),
            OptionChoice(
                id="D",
                text="Decreases both apparent Km and Vmax proportionally.",
            ),
        ],
        correct_answer_id="A",
        correct_answer_ids=["A"],
        primary_trap="Calculation_Formula_Trap",
        explanation=(
            "Why Option A is Correct:\n"
            "In a Lineweaver-Burk double-reciprocal plot, the y-intercept represents 1/Vmax and the x-intercept "
            "represents -1/Km. Identical y-intercepts confirm that Vmax is unchanged. An x-intercept shifting closer "
            "to the origin indicates that -1/Km becomes less negative (smaller magnitude), which corresponds to a "
            "larger numerical Km. This pattern definitively characterizes competitive inhibition, where oxamate "
            "competes reversibly with pyruvate for the active site, increasing apparent Km while Vmax remains reachable at saturating substrate.\n\n"
            "Why Other Options are Incorrect:\n"
            "- Option B: Incorrect (Formula Inversion). Confuses the reciprocal magnitude: shifting -1/Km toward zero reflects an increased Km, not a decrease.\n"
            "- Option C: Incorrect. A decreased Vmax with constant Km defines noncompetitive inhibition, which would alter the y-intercept.\n"
            "- Option D: Incorrect. Proportional decreases in both Km and Vmax describe uncompetitive inhibition, producing parallel Lineweaver-Burk slopes.\n\n"
            "Primary Cognitive Trap Spotlight:\n"
            "- Trap: Calculation / Formula Inversion\n"
            "- Error Mechanism: Candidates often misinterpret double-reciprocal axes, forgetting that moving rightward toward zero on the negative x-axis means 1/Km is smaller, and therefore Km is larger.\n"
            "- Student Defense Strategy: Always write out 1/Vmax (y-intercept) and -1/Km (x-intercept) explicitly before interpreting double-reciprocal graphs."
        ),
        cognitive_trap="Calculation / Formula Inversion",
        final_score=96,
        status="in_bank",
        iteration_count=1,
    )

    q2 = Question(
        id="q-seed-cars-01",
        section="cars",
        section_label="Critical Analysis and Reasoning Skills",
        subtopic="Foundations of Comprehension (Direct Inferences & Thesis Extraction)",
        difficulty="Hard",
        passage_id="passage-seed-cars-01",
        passage_mode="single_passage",
        batch_id=batch_id,
        mcat_scaled_score=131,
        aamc_skill="Skill_2_Reasoning_About_The_Text",
        subject="Humanities",
        unit="Historiography & Media History",
        topic="Print Culture & Social Control",
        subskill="Evaluating Arguments Against Technological Determinism",
        likely_mistake_pattern="Selecting absolute unhedged claims or overlooking sociological institutional mediation",
        stimulus_text=(
            "Technological deterministic historiography frequently credits Johannes Gutenberg's movable type "
            "with single-handedly dismantling scholastic dogma and midwifing European modernity. Yet this tidy "
            "teleology neglects the complex social matrix that governed early typography. The expansion of printing "
            "presses in Nuremberg, Venice, and Lyon did not occur in a commercial vacuum; rather, it was heavily "
            "underwritten by municipal oligarchies and ecclesiastical patrons who recognized print as an unprecedented "
            "instrument of surveillance and doctrinal consolidation. Rather than spontaneously liberalizing discourse, "
            "early print shops operated under strict guild patents and pre-publication censorship boards that effectively "
            "standardized orthodoxy across sprawling territories before radical broadsides could achieve widespread distribution."
        ),
        question_stem="Which of the following assertions from the passage provides the strongest counterargument to technological determinism?",
        options=[
            OptionChoice(
                id="A",
                text="Municipal oligarchies and ecclesiastical boards actively shaped the adoption and regulatory oversight of print production.",
            ),
            OptionChoice(
                id="B",
                text="Movable type failed to improve the typographical legibility of vernacular manuscripts in urban centres.",
            ),
            OptionChoice(
                id="C",
                text="Ecclesiastical patrons unanimously banned the operation of movable type printing presses across Europe.",
            ),
            OptionChoice(
                id="D",
                text="Radical broadsides achieved greater cultural impact than authorized theological treatises.",
            ),
        ],
        correct_answer_id="A",
        correct_answer_ids=["A"],
        primary_trap="Extreme_Language",
        explanation=(
            "Why Option A is Correct:\n"
            "The author explicitly argues against technological determinism (the view that technology alone causes social change) "
            "by demonstrating that political and ecclesiastical institutions mediated, financed, and regulated print shops "
            "to enforce ideological control, proving that social and institutional factors determined the medium's trajectory.\n\n"
            "Why Other Options are Incorrect:\n"
            "- Option B: Incorrect (Out of Scope). The text makes no reference to typographical legibility or manuscript aesthetics.\n"
            "- Option C: Incorrect (Extreme Language Trap). The passage notes that patrons 'underwrote' and used print for consolidation, rather than 'unanimously banning' it.\n"
            "- Option D: Incorrect (Distortion). The author indicates censorship prevented radical broadsides from achieving widespread distribution before orthodoxy was standardized.\n\n"
            "Primary Cognitive Trap Spotlight:\n"
            "- Trap: Extreme Language Trap\n"
            "- Error Mechanism: Option C uses the unhedged absolute 'unanimously banned', which directly contradicts the passage evidence that patrons funded and utilized the printing press.\n"
            "- Student Defense Strategy: In CARS, eliminate choices with extreme quantifiers ('unanimously', 'all', 'never') unless explicitly supported verbatim by the text."
        ),
        cognitive_trap="Extreme Language Trap",
        final_score=98,
        status="in_bank",
        iteration_count=1,
    )

    q3 = Question(
        id="q-seed-bio-biochem-01",
        section="bio_biochem",
        section_label="Biological and Biochemical Foundations of Living Systems",
        subtopic="Metabolic Pathways & Cellular Bioenergetics (Glycolysis, Krebs, OxPhos)",
        difficulty="Medium",
        passage_id="passage-seed-bio-biochem-01",
        passage_mode="single_passage",
        batch_id=batch_id,
        mcat_scaled_score=130,
        aamc_skill="Skill_2_Scientific_Reasoning_and_Problem_Solving",
        subject="Cell Biology",
        unit="Cellular Metabolism",
        topic="Oxidative Phosphorylation & Chemiosmosis",
        subskill="Predicting Effects of Chemical Uncouplers vs Inhibitors",
        likely_mistake_pattern="Assuming decoupling ATP synthesis must halt oxygen consumption",
        stimulus_text=(
            "Mitochondrial oxidative phosphorylation couples the exergonic transfer of electrons through the electron "
            "transport chain (ETC) to the endergonic synthesis of ATP via an electrochemical proton gradient across "
            "the inner mitochondrial membrane. In an experimental assay, isolated murine hepatocytes were exposed to "
            "2,4-dinitrophenol (DNP), a lipophilic weak acid capable of freely diffusing across mitochondrial lipid bilayers "
            "while transporting protons from the intermembrane space into the matrix, effectively dissipating the proton motive force."
        ),
        question_stem="What immediate biochemical consequence is observed in the hepatocytes following the addition of 2,4-dinitrophenol?",
        options=[
            OptionChoice(
                id="A",
                text="Oxygen consumption persists or increases while mitochondrial ATP synthesis drops precipitously.",
            ),
            OptionChoice(
                id="B",
                text="Both electron transport chain electron flux and oxygen consumption cease completely.",
            ),
            OptionChoice(
                id="C",
                text="ATP synthase activity accelerates to compensate for the reduction in matrix proton concentration.",
            ),
            OptionChoice(
                id="D",
                text="The citric acid cycle halts due to allosteric inhibition of isocitrate dehydrogenase by ATP.",
            ),
        ],
        correct_answer_id="A",
        correct_answer_ids=["A"],
        primary_trap="Distortion_Opposite",
        explanation=(
            "Why Option A is Correct:\n"
            "DNP uncouples electron transport from ATP synthesis. By dissipating the transmembrane proton gradient, "
            "DNP relieves proton back-pressure on the ETC complexes. Consequently, electron transport and oxygen "
            "consumption proceed at maximal or uninhibited rates, but without a proton gradient, ATP synthase cannot "
            "phosphorylate ADP, causing ATP production to collapse and energy to be released as heat.\n\n"
            "Why Other Options are Incorrect:\n"
            "- Option B: Incorrect (Distortion / Opposite Trap). Electron flux and oxygen consumption do not cease; they increase or continue unhindered because the proton motive force resistance is abolished.\n"
            "- Option C: Incorrect. ATP synthase requires a transmembrane proton motive force to drive gamma-subunit rotation; dissipating the gradient eliminates synthase activity.\n"
            "- Option D: Incorrect. Since ATP levels fall and ADP/AMP levels rise, isocitrate dehydrogenase and the Krebs cycle are stimulated rather than allosterically inhibited.\n\n"
            "Primary Cognitive Trap Spotlight:\n"
            "- Trap: Distortion / Opposite Trap\n"
            "- Error Mechanism: Option B reverses the biological relationship by assuming that shutting down ATP production must also shut down electron transport and oxygen consumption.\n"
            "- Student Defense Strategy: Distinguish uncouplers (which dissipate the gradient while leaving ETC intact) from ETC inhibitors (such as cyanide or CO, which halt both electron flow and oxygen consumption)."
        ),
        cognitive_trap="Distortion / Opposite Trap",
        final_score=96,
        status="in_bank",
        iteration_count=1,
    )

    q4 = Question(
        id="q-seed-psych-soc-01",
        section="psych_soc",
        section_label="Psychological, Social, and Biological Foundations of Behavior",
        subtopic="Social Psychology, Social Cognition & Group Dynamics",
        difficulty="Medium",
        passage_id="passage-seed-psych-soc-01",
        passage_mode="single_passage",
        batch_id=batch_id,
        mcat_scaled_score=129,
        aamc_skill="Skill_1_Knowledge_of_Scientific_Concepts",
        subject="Sociology & Psychology",
        unit="Social Processes & Interaction",
        topic="Group Influence & Decision Making",
        subskill="Differentiating Group Polarization from Conformity and Facilitation",
        likely_mistake_pattern="Conflating group polarization with social facilitation or deindividuation",
        stimulus_text=(
            "A social psychology study investigated decision-making dynamics in civil jury simulations. Participants "
            "were pre-screened and categorized based on their initial attitudes regarding punitive damages in corporate "
            "malpractice cases. Groups composed entirely of individuals who initially favored moderate punitive damages "
            "were instructed to deliberate for 45 minutes to reach a consensus verdict. Following group discussion, "
            "the consensus damage awards recommended by these groups were significantly more punitive and severe than "
            "the mathematical mean of the members' individual pre-deliberation recommendations."
        ),
        question_stem="Which socio-psychological phenomenon best accounts for the shift toward more extreme punitive verdicts observed post-deliberation?",
        options=[
            OptionChoice(
                id="A",
                text="Group polarization",
            ),
            OptionChoice(
                id="B",
                text="Social facilitation",
            ),
            OptionChoice(
                id="C",
                text="Deindividuation",
            ),
            OptionChoice(
                id="D",
                text="The bystander effect",
            ),
        ],
        correct_answer_id="A",
        correct_answer_ids=["A"],
        primary_trap="Scope_Shift",
        explanation=(
            "Why Option A is Correct:\n"
            "Group polarization occurs when deliberation among like-minded individuals intensifies their pre-existing shared "
            "tendencies, shifting the group's collective judgment toward a more extreme position than any individual held "
            "prior to discussion. Because participants initially favored moderate punitive damages, deliberation produced "
            "an outcome that was far more punitive.\n\n"
            "Why Other Options are Incorrect:\n"
            "- Option B: Incorrect. Social facilitation refers to improved performance on simple or well-rehearsed tasks in the presence of others.\n"
            "- Option C: Incorrect. Deindividuation involves the loss of self-awareness and individual accountability in large crowds or anonymous groups.\n"
            "- Option D: Incorrect. The bystander effect describes the decreased likelihood of an individual offering assistance when other observers are present.\n\n"
            "Primary Cognitive Trap Spotlight:\n"
            "- Trap: Scope Shift Trap\n"
            "- Error Mechanism: Confusing distinct social psychology constructs that each describe group influence on individuals.\n"
            "- Student Defense Strategy: Identify the core variable being measured. When the outcome is an attitude or decision shift toward an extreme following discussion among like-minded peers, the construct is group polarization."
        ),
        cognitive_trap="Scope Shift Trap",
        final_score=97,
        status="in_bank",
        iteration_count=1,
    )

    for q in [q1, q2, q3, q4]:
        saved = await save_question(q)
        logger.info(
            "Seeded MCAT Question: %s [%s - %s]", saved.id, saved.section, saved.section_label
        )


if __name__ == "__main__":
    asyncio.run(seed())
