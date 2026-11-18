from app.agents.prompt_builder import _build_generator_user_prompt
from app.schemas import GenerationRequest, MCATSection
from app.services.deduplication import compute_question_similarity, evaluate_duplicate
from app.workflow.passage_prep import (
    CARS_PASSAGE_SET_BLUEPRINTS,
    SCIENCE_PASSAGE_SET_BLUEPRINTS,
    _build_batch_worker_request,
)


def test_cars_passage_set_blueprints_assignment():
    req = GenerationRequest(
        section=MCATSection.CARS,
        passage_mode="single_passage",
        questions_to_generate=5,
    )
    passage_text = "Sample humanities reading passage text with multiple paragraphs for CARS."
    passage_id = "test-passage-cars-uuid"

    slot_archetypes = []
    slot_skills = []

    for idx in range(5):
        item_req, _run_id, is_passage, _interaction = _build_batch_worker_request(
            req=req,
            idx=idx,
            total_qty=5,
            batch_id="batch-cars",
            effective_passage_count=5,
            shared_passage_id=passage_id,
            shared_passage_text=passage_text,
        )
        assert is_passage is True
        assert item_req.passage_id == passage_id
        assert item_req.shared_stimulus == passage_text
        assert item_req.question_type == CARS_PASSAGE_SET_BLUEPRINTS[idx]["archetype"]
        assert item_req.aamc_skill == CARS_PASSAGE_SET_BLUEPRINTS[idx]["skill"]
        assert "SLOT" in item_req.thematic_angle
        slot_archetypes.append(item_req.question_type)
        slot_skills.append(item_req.aamc_skill)

    # Verify all 5 slot archetypes are unique
    assert len(set(slot_archetypes)) == 5
    assert "Central Claim / Main Thesis" in slot_archetypes
    assert "Local Detail & Passage Evidence" in slot_archetypes
    assert "Rhetorical Function / Author's Stance" in slot_archetypes
    assert "Reasoning Beyond the Text: Novel Scenario Application" in slot_archetypes
    assert "Reasoning Beyond the Text: Challenge / Weaken Assumptions" in slot_archetypes


def test_science_passage_set_blueprints_assignment():
    req = GenerationRequest(
        section=MCATSection.BIO_BIOCHEM,
        passage_mode="single_passage",
        questions_to_generate=5,
    )
    passage_text = "Sample biochemistry experimental passage text."
    passage_id = "test-passage-bio-uuid"

    slot_archetypes = []
    for idx in range(5):
        item_req, _run_id, _is_passage, _interaction = _build_batch_worker_request(
            req=req,
            idx=idx,
            total_qty=5,
            batch_id="batch-bio",
            effective_passage_count=5,
            shared_passage_id=passage_id,
            shared_passage_text=passage_text,
        )
        assert item_req.question_type == SCIENCE_PASSAGE_SET_BLUEPRINTS[idx]["archetype"]
        slot_archetypes.append(item_req.question_type)

    assert len(set(slot_archetypes)) == 5
    assert "Scientific Concept & Principle Foundation" in slot_archetypes
    assert "Data, Figure & Graph Interpretation" in slot_archetypes
    assert "Experimental Design & Methodological Rationale" in slot_archetypes


def test_prompt_builder_includes_slot_specialization_directive():
    req = GenerationRequest(
        section=MCATSection.CARS,
        passage_mode="single_passage",
        shared_stimulus="Pre-existing passage content.",
        thematic_angle="SLOT 3 FOCUS: Test rhetorical function of a specific metaphor.",
        question_type="Rhetorical Function / Author's Stance",
    )
    prompt = _build_generator_user_prompt(req)
    assert "Question Type Format: Rhetorical Function / Author's Stance" in prompt
    assert "MANDATORY SLOT SPECIALIZATION:" in prompt
    assert "SLOT 3 FOCUS" in prompt
    assert "Pre-existing passage content." in prompt


def test_same_passage_deduplication_catches_semantic_clones():
    # Two questions on the same passage with synonymous answer keys
    q1 = {
        "id": "q1",
        "passage_id": "passage-common-789",
        "question_stem": "What is the author's primary attitude toward the lock-and-key model?",
        "options": [
            {
                "id": "A",
                "text": "Defending it as a simplified model useful despite its limitations",
            },
            {"id": "B", "text": "Rejecting it entirely as misleading"},
        ],
        "correct_answer_id": "A",
    }
    q2 = {
        "id": "q2",
        "passage_id": "passage-common-789",
        "question_stem": "According to the author, the traditional lock and key metaphor is best viewed as:",
        "options": [
            {"id": "A", "text": "Completely invalid in modern biochemistry"},
            {"id": "B", "text": "Remaining useful as a simplified model despite its limitations"},
        ],
        "correct_answer_id": "B",
    }

    sim, reason = compute_question_similarity(q1, q2)
    assert sim >= 0.75
    assert "Same-passage" in reason

    res = evaluate_duplicate(q2, [q1], threshold=0.75)
    assert res.is_duplicate is True


def test_section_aware_batch_thematic_angles():
    from app.services.batch_worker import (
        BIO_BIOCHEM_THEMATIC_ANGLES,
        CARS_THEMATIC_ANGLES,
        CHEM_PHYS_THEMATIC_ANGLES,
        PSYCH_SOC_THEMATIC_ANGLES,
        _batch_thematic_angle,
    )

    req_cars = GenerationRequest(section=MCATSection.CARS, questions_to_generate=5)
    req_bio = GenerationRequest(section=MCATSection.BIO_BIOCHEM, questions_to_generate=5)
    req_cp = GenerationRequest(section=MCATSection.CHEM_PHYS, questions_to_generate=5)
    req_ps = GenerationRequest(section=MCATSection.PSYCH_SOC, questions_to_generate=5)

    # Verify CARS gets CARS angles
    angle_cars_1 = _batch_thematic_angle(1, req_cars)
    assert "Set #1:" in angle_cars_1
    assert CARS_THEMATIC_ANGLES[0] in angle_cars_1

    # Verify Bio/Biochem gets Bio angles
    angle_bio_1 = _batch_thematic_angle(1, req_bio)
    assert "Set #1:" in angle_bio_1
    assert BIO_BIOCHEM_THEMATIC_ANGLES[0] in angle_bio_1

    # Verify Chem/Phys gets Chem/Phys angles
    angle_cp_1 = _batch_thematic_angle(1, req_cp)
    assert "Set #1:" in angle_cp_1
    assert CHEM_PHYS_THEMATIC_ANGLES[0] in angle_cp_1

    # Verify Psych/Soc gets Psych/Soc angles
    angle_ps_1 = _batch_thematic_angle(1, req_ps)
    assert "Set #1:" in angle_ps_1
    assert PSYCH_SOC_THEMATIC_ANGLES[0] in angle_ps_1

    # Rotation across jobs
    angle_cars_2 = _batch_thematic_angle(2, req_cars)
    assert CARS_THEMATIC_ANGLES[1] in angle_cars_2
    assert angle_cars_1 != angle_cars_2


def test_cars_slot4_domain_rotation():
    from app.workflow.passage_prep import (
        CARS_SLOT4_APPLICATION_DOMAINS,
        _build_batch_worker_request,
    )

    domains_seen = []
    for set_num in range(1, 4):
        req = GenerationRequest(
            section=MCATSection.CARS,
            passage_mode="single_passage",
            questions_to_generate=5,
            thematic_angle=f"Set #{set_num}: Epistemology",
        )
        item_req, _, _, _ = _build_batch_worker_request(
            req=req,
            idx=3,  # Slot 4 (0-indexed 3)
            total_qty=5,
            batch_id=f"batch-cars-{set_num}",
            effective_passage_count=5,
            shared_passage_id=f"passage-{set_num}",
            shared_passage_text="Passage text...",
        )
        assert "MANDATORY APPLICATION DOMAIN:" in item_req.thematic_angle
        assert "Forbid using screening instruments" in item_req.thematic_angle
        expected_domain = CARS_SLOT4_APPLICATION_DOMAINS[set_num - 1]
        assert expected_domain in item_req.thematic_angle
        domains_seen.append(expected_domain)

    # Verify distinct domains across sets
    assert len(set(domains_seen)) == 3
