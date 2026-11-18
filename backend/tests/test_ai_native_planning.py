"""
Unit tests for AI-Native dynamic batch planning and passage blueprinting.
"""

from unittest.mock import AsyncMock, patch

import pytest
from app.agents.batch_planner import (
    _BATCH_THEMATIC_CACHE,
    _build_deterministic_angles,
    brainstorm_batch_thematic_angles,
    resolve_batch_thematic_angle,
)
from app.core.config import config
from app.schemas import GenerationRequest, MCATSection
from app.schemas.token import TokenUsage
from app.workflow.passage_prep import (
    CARS_PASSAGE_SET_BLUEPRINTS,
    SCIENCE_PASSAGE_SET_BLUEPRINTS,
    _build_batch_worker_request,
    extract_passage_slot_blueprints,
)


@pytest.fixture(autouse=True)
def clear_batch_thematic_cache():
    _BATCH_THEMATIC_CACHE.clear()
    yield
    _BATCH_THEMATIC_CACHE.clear()


def test_build_deterministic_angles_with_topic():
    req = GenerationRequest(
        section=MCATSection.CHEM_PHYS,
        topic="Organic Chemistry",
        subtopic="Aldol Condensation",
        questions_to_generate=5,
    )
    angles = _build_deterministic_angles(req, 5)
    assert len(angles) == 5
    for i, a in enumerate(angles):
        assert f"Set #{i + 1}:" in a
        assert "Aldol Condensation" in a
        assert "—" in a


def test_build_deterministic_angles_cars():
    req = GenerationRequest(
        section=MCATSection.CARS,
        subtopic="Philosophy of Science",
        questions_to_generate=3,
    )
    angles = _build_deterministic_angles(req, 3)
    assert len(angles) == 3
    assert "Set #1:" in angles[0]
    assert "Philosophy of Science" in angles[0]
    assert "Set #2:" in angles[1]


@pytest.mark.asyncio
async def test_brainstorm_batch_thematic_angles_offline(monkeypatch):
    monkeypatch.setattr(config, "OFFLINE_MODE", True)
    req = GenerationRequest(
        section=MCATSection.BIO_BIOCHEM,
        topic="Renal Physiology",
        subtopic="Countercurrent Multiplier",
        questions_to_generate=4,
    )
    angles = await brainstorm_batch_thematic_angles(req, 4)
    assert len(angles) == 4
    assert all("Countercurrent Multiplier" in a for a in angles)


@pytest.mark.asyncio
async def test_brainstorm_batch_thematic_angles_live_success(monkeypatch):
    monkeypatch.setattr(config, "OFFLINE_MODE", False)
    req = GenerationRequest(
        section=MCATSection.BIO_BIOCHEM,
        topic="Enzymology",
        subtopic="Competitive Inhibition",
        questions_to_generate=2,
    )

    mock_llm_response = '["Lineweaver-Burk Kinetic Deviations", "Allosteric Substrate Competition"]'
    mock_usage = TokenUsage(prompt_tokens=50, completion_tokens=30, total_tokens=80)

    with patch(
        "app.agents.batch_planner.call_llm",
        new=AsyncMock(return_value=(mock_llm_response, mock_usage)),
    ):
        angles = await brainstorm_batch_thematic_angles(req, 2)
        assert len(angles) == 2
        assert angles[0] == "Set #1: Lineweaver-Burk Kinetic Deviations"
        assert angles[1] == "Set #2: Allosteric Substrate Competition"


@pytest.mark.asyncio
async def test_brainstorm_batch_thematic_angles_live_fallback_on_error(monkeypatch):
    monkeypatch.setattr(config, "OFFLINE_MODE", False)
    req = GenerationRequest(
        section=MCATSection.PSYCH_SOC,
        subtopic="Cognitive Dissonance",
        questions_to_generate=3,
    )

    with patch("app.agents.batch_planner.call_llm", side_effect=RuntimeError("API error")):
        angles = await brainstorm_batch_thematic_angles(req, 3)
        assert len(angles) == 3
        assert "Cognitive Dissonance" in angles[0]


@pytest.mark.asyncio
async def test_resolve_batch_thematic_angle_cache_consistency():
    req = GenerationRequest(
        section=MCATSection.CHEM_PHYS,
        topic="Electrochemistry",
        subtopic="Galvanic Cells",
        questions_to_generate=5,
    )
    batch_id = "test-batch-uuid-123"

    angle1 = await resolve_batch_thematic_angle(1, 5, req, batch_id=batch_id)
    angle2 = await resolve_batch_thematic_angle(2, 5, req, batch_id=batch_id)
    # Refill or retry of job 1 should get identical angle from cache
    angle1_retry = await resolve_batch_thematic_angle(1, 5, req, batch_id=batch_id)

    assert angle1 == angle1_retry
    assert angle1 != angle2
    assert "Galvanic Cells" in angle1
    assert "Set #1:" in angle1
    assert "Set #2:" in angle2


@pytest.mark.asyncio
async def test_extract_passage_slot_blueprints_cars_deterministic(monkeypatch):
    monkeypatch.setattr(config, "OFFLINE_MODE", True)
    passage = (
        "Paragraph 1 establishes that historical narratives are constructed through selective archival preservation.\n\n"
        "Paragraph 2 provides empirical evidence from 19th-century colonial registries demonstrating demographic omissions.\n\n"
        "Paragraph 3 uses the metaphor of an acoustic echo chamber to explain why consensus solidified around the official record.\n\n"
        "Paragraph 4 explores the ethical dilemma of retroactively revising school curricula.\n\n"
        "Paragraph 5 concludes that historical objectivity is an asymptote rather than an achievable terminus."
    )
    req = GenerationRequest(section=MCATSection.CARS, questions_to_generate=5)
    blueprints = await extract_passage_slot_blueprints(passage, req)

    assert len(blueprints) == 5
    assert blueprints[0]["archetype"] == CARS_PASSAGE_SET_BLUEPRINTS[0]["archetype"]
    assert "Textual anchor:" in blueprints[0]["directive"]
    assert "historical narratives" in blueprints[0]["directive"]
    assert "acoustic echo chamber" in blueprints[2]["directive"]
    assert "historical objectivity is an asymptote" in blueprints[4]["directive"]


@pytest.mark.asyncio
async def test_extract_passage_slot_blueprints_science_deterministic(monkeypatch):
    monkeypatch.setattr(config, "OFFLINE_MODE", True)
    passage = (
        "Researchers investigated the catalytic activity of alkaline phosphatase in the presence of varying zinc concentrations.\n\n"
        "Spectrophotometric assays at 405 nm showed an initial linear velocity of 12.4 umol/min that plateaued at 5 mM substrate.\n\n"
        "Site-directed mutagenesis of residue His-331 was conducted to confirm zinc coordination in the active site.\n\n"
        "Downstream phosphorylation cascades in osteoblast cultures were monitored via Western blot analysis.\n\n"
        "The authors hypothesized that competitive inhibition by inorganic phosphate regulates bone mineralization rates."
    )
    req = GenerationRequest(section=MCATSection.BIO_BIOCHEM, questions_to_generate=5)
    blueprints = await extract_passage_slot_blueprints(passage, req)

    assert len(blueprints) == 5
    assert blueprints[0]["archetype"] == SCIENCE_PASSAGE_SET_BLUEPRINTS[0]["archetype"]
    assert "alkaline phosphatase" in blueprints[0]["directive"]
    assert "Spectrophotometric assays" in blueprints[1]["directive"]
    assert "His-331" in blueprints[2]["directive"]


def test_build_batch_worker_request_with_dynamic_blueprints():
    req = GenerationRequest(
        section=MCATSection.BIO_BIOCHEM,
        passage_mode="single_passage",
        questions_to_generate=5,
    )
    custom_blueprints = [
        {"skill": "Skill_1", "archetype": "Foundation", "directive": "Custom Slot 1 Directive"},
        {
            "skill": "Skill_4",
            "archetype": "Data Interpretation",
            "directive": "Custom Slot 2 Directive",
        },
        {"skill": "Skill_3", "archetype": "Methodology", "directive": "Custom Slot 3 Directive"},
        {"skill": "Skill_2", "archetype": "Mechanism", "directive": "Custom Slot 4 Directive"},
        {"skill": "Skill_2", "archetype": "Hypothesis", "directive": "Custom Slot 5 Directive"},
    ]

    item_req, _run_id, is_passage, _interaction = _build_batch_worker_request(
        req=req,
        idx=2,
        total_qty=5,
        batch_id="batch-test",
        effective_passage_count=5,
        shared_passage_id="p-123",
        shared_passage_text="Passage text",
        passage_blueprints=custom_blueprints,
    )

    assert is_passage is True
    assert item_req.question_type == "Methodology"
    assert "Custom Slot 3 Directive" in item_req.thematic_angle
