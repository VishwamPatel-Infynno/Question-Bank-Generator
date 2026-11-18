"""
test_modular_cleanup.py - Verification of decomposed modules: thematic_angles, csv_export, readability.
"""

from __future__ import annotations

from app.data.thematic_angles import (
    BIO_BIOCHEM_THEMATIC_ANGLES,
    CARS_THEMATIC_ANGLES,
    CHEM_PHYS_THEMATIC_ANGLES,
    PSYCH_SOC_THEMATIC_ANGLES,
    batch_thematic_angle,
)
from app.schemas import GenerationRequest, MCATSection, OptionChoice, Question
from app.services.csv_export import build_csv_headers, build_csv_row, generate_questions_csv
from app.services.readability import audit_passage_text, count_syllables


def test_thematic_angles_rotations():
    """Validates section-aware thematic angle selection across all 4 MCAT sections."""
    req_cars = GenerationRequest(section=MCATSection.CARS, subtopic="Epistemology")
    req_bio = GenerationRequest(section=MCATSection.BIO_BIOCHEM, subtopic="Enzymology")
    req_chem = GenerationRequest(section=MCATSection.CHEM_PHYS, subtopic="Kinetics")
    req_psych = GenerationRequest(section=MCATSection.PSYCH_SOC, subtopic="Conditioning")

    angle_cars_1 = batch_thematic_angle(1, req_cars)
    assert CARS_THEMATIC_ANGLES[0] in angle_cars_1
    assert "Set #1:" in angle_cars_1

    angle_bio_2 = batch_thematic_angle(2, req_bio)
    assert BIO_BIOCHEM_THEMATIC_ANGLES[1] in angle_bio_2

    angle_chem_3 = batch_thematic_angle(3, req_chem)
    assert CHEM_PHYS_THEMATIC_ANGLES[2] in angle_chem_3

    angle_psych_4 = batch_thematic_angle(4, req_psych)
    assert PSYCH_SOC_THEMATIC_ANGLES[3] in angle_psych_4


def test_csv_export_builders():
    """Validates CSV headers, row formatting, and full in-memory CSV generation."""
    headers = build_csv_headers()
    assert "ID" in headers
    assert "Question Stem" in headers
    assert "Correct Answer" in headers
    assert "Option A" in headers
    assert len(headers) == 28

    q = Question(
        id="q-test-123",
        section="bio_biochem",
        section_label="Biological Foundations",
        subtopic="Enzymes",
        difficulty="medium",
        question_stem="What is the role of competitive inhibitors?",
        options=[
            OptionChoice(id="A", text="Increase Km"),
            OptionChoice(id="B", text="Decrease Km"),
            OptionChoice(id="C", text="Increase Vmax"),
            OptionChoice(id="D", text="Decrease Vmax"),
        ],
        correct_answer_id="A",
        explanation="Competitive inhibitors compete with substrate for active site.",
        final_score=95,
        status="in_bank",
    )

    row = build_csv_row(q)
    assert row[0] == "q-test-123"
    assert row[18] == "What is the role of competitive inhibitors?"
    assert row[19] == "Increase Km"
    assert row[23] == "A"

    csv_text = generate_questions_csv([q])
    assert "What is the role of competitive inhibitors?" in csv_text
    assert "Increase Km" in csv_text
    lines = csv_text.strip().split("\r\n") if "\r\n" in csv_text else csv_text.strip().split("\n")
    assert len(lines) == 2  # 1 header + 1 question row


def test_readability_and_syllable_counting():
    """Validates syllable counting and passage readability metrics."""
    assert count_syllables("enzyme") == 2
    assert count_syllables("catalysis") >= 3
    assert count_syllables("") == 1

    sample_passage = (
        "Enzymes are biological catalysts that increase the rate of chemical reactions "
        "without themselves undergoing permanent chemical change. In competitive inhibition, "
        "an inhibitor molecule binds directly to the active site of the enzyme, preventing "
        "the native substrate from binding. Kinetic analyses typically measure the initial velocity "
        "as a function of substrate concentration. The concentration of inhibitor at 50 mM "
        "shifts the apparent Michaelis constant Km to higher values, while the maximal velocity Vmax "
        "remains constant at 120 umol/min. This behavior can be described using standard "
        "Lineweaver-Burk double reciprocal plots."
    )

    res = audit_passage_text(sample_passage)
    assert res["word_count"] > 50
    assert res["sentence_count"] >= 4
    assert res["flesch_kincaid_grade"] > 8.0
    assert res["empirical_density_score"] >= 1
    assert "diagnostics" in res
