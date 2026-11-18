"""
thematic_angles.py - Curated AAMC pedagogical rotation angles across MCAT sections.

Provides standardized thematic curricula and rotational angle selectors used to ensure
thematic diversity and prevent cognitive repetition across batch generation jobs.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.schemas import is_cars

if TYPE_CHECKING:
    from app.schemas import GenerationRequest

CARS_THEMATIC_ANGLES: list[str] = [
    "Epistemology, Philosophy of Mind & Theory of Knowledge (e.g., perception vs reality, limits of empiricism, conceptual frameworks)",
    "Moral Philosophy, Normative Ethics & Justice (e.g., consequentialism vs deontology, distributive justice, bioethical dilemmas)",
    "Aesthetics, Art History & Literary Criticism (e.g., representation vs abstraction, authorship intention, narrative authority)",
    "Historiography, Collective Memory & Historical Methodology (e.g., archival bias, revisionist narratives, oral histories vs written records)",
    "Political Philosophy, Institutional Power & Rights (e.g., democratic legitimacy, social contract theory, individual liberty vs state authority)",
    "Cultural Anthropology, Rituals & Semiotics (e.g., symbolic systems, cultural relativism, structuralism, social cohesion)",
    "Sociology of Science, Technology & Public Sphere (e.g., scientific consensus formation, public trust, paradigm shifts, technological determinism)",
    "Linguistics, Rhetoric & Translation Theory (e.g., linguistic relativity, meaning and context, metaphor in discourse, translatability)",
    "Environmental Philosophy, Nature & Wilderness Ethics (e.g., anthropocentrism vs biocentrism, preservationist debate, commons governance)",
    "Philosophy of Law & Jurisprudence (e.g., textualism vs living constitution, legal realism, paternalism and individual autonomy)",
]

BIO_BIOCHEM_THEMATIC_ANGLES: list[str] = [
    "Enzyme Kinetics, Allosteric Regulation & Catalytic Mechanisms (e.g., transition-state stabilization, competitive/noncompetitive inhibition)",
    "Cellular Respiration, Bioenergetics & Metabolic Flux (e.g., oxidative phosphorylation, Krebs cycle intermediates, glycolysis regulation)",
    "Molecular Genetics, DNA Replication & Repair Pathways (e.g., mismatch repair, homologous recombination, replication fork dynamics)",
    "Transcription, RNA Processing & Epigenetic Regulation (e.g., chromatin remodeling, alternative splicing, histone post-translational modifications)",
    "Membrane Biology, Transport Dynamics & Cell Signaling (e.g., GPCR pathways, receptor tyrosine kinases, ion gradients, vesicle trafficking)",
    "Immunology, Antigen Processing & Pathogen Defense (e.g., B/T-cell activation, MHC-I/II presentation, innate immune signaling)",
    "Endocrinology, Hormone Signaling & Homeostatic Feedback (e.g., hypothalamic-pituitary axes, peptide vs steroid hormones, calcium homeostasis)",
    "Developmental Biology, Cell Differentiation & Stem Cell Potency (e.g., morphogen gradients, apoptosis regulation, lineage commitment)",
    "Microbiology, Virology & Antimicrobial Resistance (e.g., viral replication cycles, horizontal gene transfer, bacterial cell wall synthesis)",
    "Renal & Circulatory Physiology (e.g., nephron countercurrent multiplier, Starling forces, hemodynamics, blood gas transport)",
]

CHEM_PHYS_THEMATIC_ANGLES: list[str] = [
    "Reaction Kinetics, Collision Theory & Transition States (e.g., rate laws, activation energy, Arrhenius equation, catalysis)",
    "Chemical Thermodynamics, Enthalpy & Spontaneity (e.g., Gibbs free energy, entropy changes, Hess's law, calorimetry)",
    "Acid-Base Equilibria, Buffers & Titrations (e.g., polyprotic titrations, Henderson-Hasselbalch, solubility product Ksp, common ion effect)",
    "Electrochemistry, Galvanic/Electrolytic Cells & Redox (e.g., Nernst equation, standard reduction potentials, battery dynamics)",
    "Fluid Dynamics, Hydrostatics & Circulatory Hemodynamics (e.g., Bernoulli's equation, Poiseuille's law, continuity equation, viscosity)",
    "Atomic Structure, Periodic Trends & Electronic Transitions (e.g., quantum numbers, photon emission, ionization energy, electronegativity)",
    "Organic Reaction Mechanisms & Stereochemistry (e.g., SN1/SN2 kinetics, electrophilic addition, chiral centers, optical activity)",
    "Optics, Wave Interference & Diagnostic Instrumentation (e.g., Snell's law, thin lenses, diffraction, Doppler effect in ultrasound)",
    "Electric Circuits, Capacitance & Membrane Potentials (e.g., Ohm's law, Kirchhoff's rules, RC circuits, dielectric constants)",
    "Thermodynamic Phase Transitions & Gas Laws (e.g., ideal vs real gases, phase diagrams, latent heats of vaporization/fusion)",
]

PSYCH_SOC_THEMATIC_ANGLES: list[str] = [
    "Cognitive Processes, Memory Architecture & Problem Solving (e.g., working memory, dual-process theory, heuristic biases, retrieval cues)",
    "Sensory Perception, Psychophysics & Signal Detection (e.g., Weber's law, feature detection, bottom-up vs top-down processing)",
    "Learning Theories, Conditioning & Behavioral Modification (e.g., operant reinforcement schedules, classical conditioning extinction)",
    "Emotion, Physiological Arousal & Stress Response (e.g., James-Lange vs Cannon-Bard vs Schachter-Singer, HPA axis, appraisal theory)",
    "Developmental Psychology, Attachment & Identity Formation (e.g., Piagetian stages, Erikson psychosocial crises, Kohlberg moral development)",
    "Social Psychology, Group Dynamics & Conformity (e.g., bystander effect, groupthink, social loafing, normative vs informational influence)",
    "Sociological Theories & Structural Inequality (e.g., structural functionalism, conflict theory, symbolic interactionism, social mobility)",
    "Social Stratification, Health Disparities & Intersectionality (e.g., social determinants of health, racial/economic disparities, gentrification)",
    "Demographic Shifts, Urbanization & Population Dynamics (e.g., demographic transition model, fertility/mortality shifts, migration patterns)",
    "Social Institutions, Medicalization & Stigma (e.g., sick role, institutional discrimination, labeling theory, cultural capital)",
]


def batch_thematic_angle(job_number: int, req: GenerationRequest) -> str:
    """The pedagogical angle a job gets by its position in the batch (rotates through the section list)."""
    if is_cars(req.section):
        angles = CARS_THEMATIC_ANGLES
    else:
        sec_str = str(req.section).lower()
        if "bio" in sec_str:
            angles = BIO_BIOCHEM_THEMATIC_ANGLES
        elif "psych" in sec_str or "soc" in sec_str:
            angles = PSYCH_SOC_THEMATIC_ANGLES
        else:
            angles = CHEM_PHYS_THEMATIC_ANGLES
    selected = angles[(job_number - 1) % len(angles)]
    return f"Set #{job_number}: {selected}"
