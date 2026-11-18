"""
test_prompt_builder_blocks.py - Unit tests for decomposed prompt builder sub-blocks.
"""

from __future__ import annotations

from app.agents.prompt_builder import (
    _build_generator_user_prompt,
    _build_mandates_and_critique_block,
    _build_mistake_pattern_directive,
    _build_pedagogy_and_trap_block,
    _build_primary_trap_directive,
    _build_stimulus_context_block,
    _build_visual_stimulus_block,
)
from app.schemas import Difficulty, GenerationRequest, MCATSection


def test_build_pedagogy_and_trap_block_automatic():
    req = GenerationRequest(
        section=MCATSection.BIO_BIOCHEM,
        difficulty=Difficulty.HARD,
        subject="Biochemistry",
        topic="Enzymes",
        subtopic="Michaelis-Menten Kinetics",
        likely_mistake_pattern="Automatic",
        primary_trap="Automatic",
    )
    block = _build_pedagogy_and_trap_block(
        req, diversity_context="Previously used: CONCEPT_CONFUSION"
    )
    assert "Section: Biological and Biochemical Foundations of Living Systems" in block
    assert "Subject: Biochemistry" in block
    assert "Topic: Enzymes" in block
    assert "Target Difficulty: high" in block
    assert "Target Student Misconception / Mistake Pattern: Automatic" in block
    assert "Primary Distractor Trap: Automatic" in block
    assert "CROSS-ITEM VARIETY CALIBRATION: Previously used: CONCEPT_CONFUSION" in block


def test_build_pedagogy_and_trap_block_explicit():
    req = GenerationRequest(
        section=MCATSection.CHEM_PHYS,
        difficulty=Difficulty.MEDIUM,
        aamc_skill="Skill 1",
        subskill="1A",
        likely_mistake_pattern="INVERTS_FRACTION",
        primary_trap="FORMULA_MISAPPLICATION",
    )
    block = _build_pedagogy_and_trap_block(req)
    assert "AAMC Reasoning Skill: Skill 1" in block
    assert "Granular Subskill Focus: 1A" in block
    assert "Target Student Misconception / Mistake Pattern: INVERTS_FRACTION" in block
    assert "Primary Distractor Trap to Emphasize: FORMULA_MISAPPLICATION" in block

    # Verify dedicated directive builders directly
    mistake_dir = _build_mistake_pattern_directive(req)
    assert "Target Student Misconception / Mistake Pattern: INVERTS_FRACTION" in mistake_dir
    trap_dir = _build_primary_trap_directive(req)
    assert "Primary Distractor Trap to Emphasize: FORMULA_MISAPPLICATION" in trap_dir


def test_build_stimulus_context_shared_passage():
    passage = "A group of researchers evaluated the inhibitory kinetics of Compound X on recombinant human..."
    req = GenerationRequest(
        section=MCATSection.BIO_BIOCHEM,
        difficulty=Difficulty.MEDIUM,
        shared_stimulus=passage,
        thematic_angle="Slot 3: Author Stance & Experimental Methodology",
    )
    block = _build_stimulus_context_block(req)
    assert "CRITICAL PASSAGE INSTRUCTION:" in block
    assert "MANDATORY SLOT SPECIALIZATION:" in block
    assert "Slot 3: Author Stance & Experimental Methodology" in block
    assert passage in block


def test_build_stimulus_context_discrete():
    req = GenerationRequest(
        section=MCATSection.CHEM_PHYS,
        difficulty=Difficulty.LOW,
        passage_required=False,
    )
    block = _build_stimulus_context_block(req)
    assert "Passage Required: No - Standalone discrete question ONLY." in block
    assert 'Leave stimulus_text strictly as an empty string ("")' in block


def test_build_stimulus_context_cars():
    req = GenerationRequest(
        section=MCATSection.CARS,
        difficulty=Difficulty.HARD,
        is_passage_active=True,
    )
    block = _build_stimulus_context_block(req)
    assert (
        "CRITICAL CARS RULE: Strictly test ONLY what is justified directly by the passage text."
        in block
    )
    assert "500-600 word humanities/social sciences essay for CARS" in block


def test_build_visual_stimulus_block_disabled():
    req = GenerationRequest(
        section=MCATSection.CARS,  # CARS never allows visuals
        difficulty=Difficulty.MEDIUM,
        allow_ai_images=False,
    )
    block = _build_visual_stimulus_block(req)
    assert "VISUAL STIMULUS STATUS:" in block
    assert "Visual stimuli are disabled for this item" in block


def test_build_visual_stimulus_block_mandatory():
    req = GenerationRequest(
        section=MCATSection.BIO_BIOCHEM,
        difficulty=Difficulty.MEDIUM,
        require_image=True,
    )
    block = _build_visual_stimulus_block(req)
    assert "MANDATORY VISUAL STIMULUS & MEDICAL IMAGING REQUIREMENT:" in block
    assert "Diagnostic Radiology" in block
    assert "Histopathology" in block
    assert "Gross Anatomy" in block
    assert "Physiological Traces" in block


def test_build_mandates_and_critique_fused():
    mandate_standard = _build_mandates_and_critique_block(fused=False)
    assert "ANTI-GUESSABILITY & OPTION SYMMETRY MANDATE:" in mandate_standard
    assert "EXPLANATION & DISTRACTOR MANDATE:" in mandate_standard
    assert "SELF-CRITIQUE INSTRUCTION:" not in mandate_standard

    mandate_fused = _build_mandates_and_critique_block(fused=True)
    assert "SELF-CRITIQUE INSTRUCTION:" in mandate_fused
    assert "Score each pillar from 0-25" in mandate_fused


def test_build_generator_user_prompt_full_assembly():
    req = GenerationRequest(
        section=MCATSection.PSYCH_SOC,
        difficulty=Difficulty.MEDIUM,
        subject="Psychology",
        topic="Learning and Memory",
        subtopic="Operant Conditioning",
        additional_instructions="Include a reference to B.F. Skinner schedules of reinforcement.",
    )
    prompt = _build_generator_user_prompt(req, fused=True)
    assert "Generate an official-caliber AAMC MCAT Multiple Choice Question" in prompt
    assert "Subject: Psychology" in prompt
    assert "Topic: Learning and Memory" in prompt
    assert "CRITICAL EDUCATOR INSTRUCTION (HIGH FIDELITY MANDATE):" in prompt
    assert "Include a reference to B.F. Skinner schedules of reinforcement." in prompt
    assert "SELF-CRITIQUE INSTRUCTION:" in prompt
