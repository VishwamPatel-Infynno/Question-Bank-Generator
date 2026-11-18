"""
Unit tests for passage_blueprints decomposition and backward compatibility with passage_prep.
"""

from __future__ import annotations

import pytest
from app.core.config import config
from app.schemas import GenerationRequest, MCATSection
from app.workflow.passage_blueprints import (
    CARS_PASSAGE_SET_BLUEPRINTS,
    CARS_SLOT4_APPLICATION_DOMAINS,
    MODALITY_ROTATION_BY_SECTION,
    SCIENCE_PASSAGE_SET_BLUEPRINTS,
    SCIENCE_SLOT5_EXPERIMENTAL_CONDITIONS,
    extract_passage_slot_blueprints,
    resolve_slot_domain_index,
)
from app.workflow.passage_prep import (
    CARS_PASSAGE_SET_BLUEPRINTS as PP_CARS_BLUEPRINTS,
)
from app.workflow.passage_prep import (
    CARS_SLOT4_APPLICATION_DOMAINS as PP_CARS_SLOT4_DOMAINS,
)
from app.workflow.passage_prep import (
    MODALITY_ROTATION_BY_SECTION as PP_MODALITY_ROTATION,
)
from app.workflow.passage_prep import (
    SCIENCE_PASSAGE_SET_BLUEPRINTS as PP_SCIENCE_BLUEPRINTS,
)
from app.workflow.passage_prep import (
    SCIENCE_SLOT5_EXPERIMENTAL_CONDITIONS as PP_SCIENCE_SLOT5_CONDITIONS,
)
from app.workflow.passage_prep import (
    extract_passage_slot_blueprints as pp_extract_passage_slot_blueprints,
)
from app.workflow.passage_prep import (
    resolve_slot_domain_index as pp_resolve_slot_domain_index,
)


def test_passage_blueprints_structure():
    """Verify that both CARS and Science passage blueprints contain exactly 5 well-formed slot specs."""
    assert len(CARS_PASSAGE_SET_BLUEPRINTS) == 5
    assert len(SCIENCE_PASSAGE_SET_BLUEPRINTS) == 5

    cars_skills = {bp["skill"] for bp in CARS_PASSAGE_SET_BLUEPRINTS}
    assert cars_skills <= {"CARS1", "CARS2", "CARS3"}

    science_skills = {bp["skill"] for bp in SCIENCE_PASSAGE_SET_BLUEPRINTS}
    assert science_skills <= {"Skill_1", "Skill_2", "Skill_3", "Skill_4"}

    for bp in CARS_PASSAGE_SET_BLUEPRINTS + SCIENCE_PASSAGE_SET_BLUEPRINTS:
        assert bp["archetype"].strip()
        assert bp["directive"].strip()


def test_domain_index_resolution():
    """Verify deterministic domain index extraction from thematic angles and request metadata."""
    req_angle_1 = GenerationRequest(
        section=MCATSection.CARS,
        thematic_angle="Set #1: Epistemology",
    )
    assert resolve_slot_domain_index(req_angle_1) == 0

    req_angle_5 = GenerationRequest(
        section=MCATSection.BIO_BIOCHEM,
        thematic_angle="Job #5: Enzyme Kinetics",
    )
    assert resolve_slot_domain_index(req_angle_5) == 4

    req_angle_11 = GenerationRequest(
        section=MCATSection.CHEM_PHYS,
        thematic_angle="Set #11: Thermodynamics",
    )
    assert resolve_slot_domain_index(req_angle_11) == 0  # 11 - 1 = 10 % 10 == 0

    # Deterministic fallback when no angle is present
    req_no_angle = GenerationRequest(section=MCATSection.PSYCH_SOC, run_id="static-test-seed")
    idx = resolve_slot_domain_index(req_no_angle)
    assert 0 <= idx < 10

    # Verify attempt rotation for slot replenishment
    assert resolve_slot_domain_index(req_angle_1, attempt=1) == 1
    assert resolve_slot_domain_index(req_angle_1, attempt=2) == 2


def test_passage_blueprints_backward_compatibility():
    """Verify that re-exports from passage_prep.py point to the exact same objects in passage_blueprints.py."""
    assert PP_CARS_BLUEPRINTS is CARS_PASSAGE_SET_BLUEPRINTS
    assert PP_SCIENCE_BLUEPRINTS is SCIENCE_PASSAGE_SET_BLUEPRINTS
    assert PP_CARS_SLOT4_DOMAINS is CARS_SLOT4_APPLICATION_DOMAINS
    assert PP_SCIENCE_SLOT5_CONDITIONS is SCIENCE_SLOT5_EXPERIMENTAL_CONDITIONS
    assert PP_MODALITY_ROTATION is MODALITY_ROTATION_BY_SECTION
    assert pp_resolve_slot_domain_index is resolve_slot_domain_index
    assert pp_extract_passage_slot_blueprints is extract_passage_slot_blueprints


@pytest.mark.asyncio
async def test_extract_passage_slot_blueprints_deterministic(monkeypatch):
    """Verify that offline deterministic claim extraction yields 5 grounded slot targets."""
    monkeypatch.setattr(config, "OFFLINE_MODE", True)

    passage = (
        "Paragraph 1: Background on cardiac electrophysiology and ion channels.\n\n"
        "Paragraph 2: Methodology using patch-clamp recordings on ventricular myocytes.\n\n"
        "Paragraph 3: Observed 40% reduction in peak sodium current under hypoxia.\n\n"
        "Paragraph 4: Mechanistic role of phosphorylation in channel inactivation.\n\n"
        "Paragraph 5: Clinical implications for anti-arrhythmic pharmacotherapy."
    )

    req_science = GenerationRequest(
        section=MCATSection.BIO_BIOCHEM,
        topic="Cardiovascular Physiology",
        thematic_angle="Set #1: Electrophysiology",
    )
    blueprints_science = await extract_passage_slot_blueprints(passage, req_science)
    assert len(blueprints_science) == 5
    assert "SLOT 1 FOCUS" in blueprints_science[0]["directive"]
    assert "SLOT 5 FOCUS" in blueprints_science[4]["directive"]

    req_cars = GenerationRequest(
        section=MCATSection.CARS,
        thematic_angle="Set #2: Moral Philosophy",
    )
    blueprints_cars = await extract_passage_slot_blueprints(passage, req_cars)
    assert len(blueprints_cars) == 5
    assert "SLOT 1 FOCUS" in blueprints_cars[0]["directive"]
    assert "SLOT 4 FOCUS" in blueprints_cars[3]["directive"]
    # Verify strict non-overlapping paragraph assignments and premise excerpts
    for bp in blueprints_cars + blueprints_science:
        assert "premise_excerpt" in bp
        assert len(bp["premise_excerpt"]) > 0


@pytest.mark.asyncio
async def test_in_flight_semantic_duplicate_cosine_detection(monkeypatch):
    """Verify that in-flight deduplication detects semantic sibling collisions via vector embeddings."""
    monkeypatch.setattr(config, "ENABLE_PGVECTOR_RAG", True)
    from app.services.embeddings import deterministic_unit_vector
    from app.workflow.dedup_inflight import _evaluate_duplicate_async

    # Lexically distinct stems that test the identical conceptual proposition
    stem_a = "The author discusses whether parameter invariance across multiple perturbations can establish a unique causal account."
    stem_b = "Which conclusion is best supported about a reader who infers exactly one underlying cause from a parameter remaining unchanged across experiments?"

    # Shared or closely aligned unit vector
    vec = deterministic_unit_vector("parameter invariance unique causal account")

    cand_draft = {
        "id": "in_flight_draft_slot_1",
        "question_stem": stem_a,
        "embedding": vec,
        "options": [{"id": "A", "text": "Opt A"}, {"id": "B", "text": "Opt B"}],
    }

    ref_sibling = {
        "id": "in_flight_draft_slot_2",
        "question_stem": stem_b,
        "embedding": vec,
        "options": [{"id": "A", "text": "Opt A"}, {"id": "B", "text": "Opt B"}],
    }

    result = await _evaluate_duplicate_async(
        cand_draft,
        [ref_sibling],
        threshold=0.75,
        soft_threshold=0.60,
    )

    assert result.is_duplicate is True
    assert result.similarity_score >= 0.80
    assert "In-Flight Sibling Collision" in (result.match_reason or "")
