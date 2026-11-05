import pytest
from app.agents.generator import get_mock_draft
from app.agents.reviewer import evaluate_heuristically
from app.schemas import (
    Difficulty,
    GenerationRequest,
    MCATSection,
    ReviewScore,
    TokenUsage,
)
from app.workflow.graph import route_after_review


def _base_module():
    """call_llm_validated resolves call_llm in app.agents.base, so patch it there."""
    import app.agents.base as base_mod

    return base_mod


@pytest.mark.asyncio
async def test_all_mcat_sections_mock():
    for sec in MCATSection:
        req = GenerationRequest(
            section=sec,
            subtopic="Core Syllabus",
            difficulty=Difficulty.MEDIUM,
            passage_required="Yes" if sec == MCATSection.CARS else "No",
            require_image=(sec == MCATSection.CHEM_PHYS),
        )
        draft = get_mock_draft(req)
        assert len(draft.options) == 4
        assert draft.correct_answer_id in ["A", "B", "C", "D"]
        assert len(draft.explanation) > 20


@pytest.mark.asyncio
async def test_reviewer_heuristic_and_loop_routing():
    req = GenerationRequest(section=MCATSection.CHEM_PHYS, difficulty=Difficulty.MEDIUM)
    draft = get_mock_draft(req)

    # Iteration 1 score should be <= 90 to test re-generation loop
    rev1 = evaluate_heuristically(draft, req, iteration=1)
    assert rev1.total_score <= 90
    assert not rev1.passed

    # Test route_after_review sends to regenerator
    state1 = {
        "request": req.model_dump(),
        "current_draft": draft.model_dump(),
        "current_review": rev1.model_dump(),
        "iteration_count": 1,
    }
    next_node = route_after_review(state1)
    assert next_node == "regenerator"

    # Iteration 2 should score > 90 and pass
    rev2 = evaluate_heuristically(draft, req, iteration=2)
    assert rev2.total_score > 90
    assert rev2.passed

    state2 = {
        "request": req.model_dump(),
        "current_draft": draft.model_dump(),
        "current_review": rev2.model_dump(),
        "iteration_count": 2,
    }
    next_node2 = route_after_review(state2)
    assert next_node2 in ["image_generator", "finalize"]


@pytest.mark.asyncio
async def test_strict_rejection_routing_when_score_le_90():
    from app.core.config import config
    from app.workflow.graph import reject_node

    req = GenerationRequest(
        section=MCATSection.CARS, difficulty=Difficulty.HARD, passage_required="Yes"
    )
    draft = get_mock_draft(req)

    # Reviewer score of 82 (<= 90) at maximum iteration attempt (3)
    rev_failing = ReviewScore(
        authenticity_score=20,
        clarity_score=20,
        distractor_score=20,
        explanation_score=22,
        total_score=82,
        strengths=["Good topic"],
        weaknesses=["Distractor A is trivial"],
        recommendations=["Improve Distractor A"],
        passed=False,
    )

    state_failing = {
        "request": req.model_dump(),
        "current_draft": draft.model_dump(),
        "current_review": rev_failing.model_dump(),
        "iteration_count": config.MAX_REGENERATION_ATTEMPTS,
    }

    # At max attempts, route_after_review MUST route to 'reject'
    next_node = route_after_review(state_failing)
    assert next_node == "reject"

    # Executing reject_node must produce rejection diagnostic payload without persisting
    reject_res = await reject_node(state_failing)
    assert reject_res["status"] == "rejected_below_threshold"
    assert reject_res["rejection_data"]["final_score"] == 82
    assert "reason" in reject_res["rejection_data"]


@pytest.mark.asyncio
async def test_section_image_guard_routing():
    # 1. CARS: score 95 > 90, image_needed=True in draft, require_image=False
    # Should route to finalize, strictly bypassing image_generator (CARS has no images)
    cars_state = {
        "request": {
            "section": "cars",
            "require_image": False,
            "visual_type": "None",
        },
        "current_review": {"total_score": 95},
        "current_draft": {"image_needed": True},
        "iteration_count": 1,
    }
    assert route_after_review(cars_state) == "finalize"

    # 2. CARS with require_image=False routes to finalize
    cars_no_img_state = {
        "request": {
            "section": "critical_analysis_and_reasoning_skills",
            "require_image": False,
            "visual_type": "None",
        },
        "current_review": {"total_score": 94},
        "current_draft": {"image_needed": False},
        "iteration_count": 1,
    }
    assert route_after_review(cars_no_img_state) == "finalize"

    # 3. Chem/Phys with explicit require_image=True routes to image_generator
    cp_explicit_state = {
        "request": {
            "section": "chem_phys",
            "require_image": True,
            "visual_type": "None",
        },
        "current_review": {"total_score": 95},
        "current_draft": {"image_needed": True},
        "iteration_count": 1,
    }
    assert route_after_review(cp_explicit_state) == "image_generator"

    # 4. Chem/Phys with image_needed=True routes to image_generator
    cp_needed_state = {
        "request": {
            "section": "chem_phys",
            "require_image": False,
            "visual_type": "None",
        },
        "current_review": {"total_score": 95},
        "current_draft": {"image_needed": True},
        "iteration_count": 1,
    }
    assert route_after_review(cp_needed_state) == "image_generator"


@pytest.mark.asyncio
async def test_generate_question_with_self_critique_structure(monkeypatch):
    """Verifies that generate_question_with_self_critique returns a valid draft, review score, and usage."""
    import app.agents.generator as gen_mod
    from app.agents.generator import generate_question_with_self_critique
    from app.core.config import config
    from app.schemas import QuestionDraft, ReviewScore, TokenUsage

    # 1. Fallback mode (no API key configured)
    monkeypatch.setattr(config, "DEEPINFRA_API_KEY", "")
    monkeypatch.delenv("DEEPINFRA_API_KEY", raising=False)

    req = GenerationRequest(
        section=MCATSection.PSYCH_SOC,
        difficulty=Difficulty.MEDIUM,
    )
    draft, review, usage = await generate_question_with_self_critique(req)

    assert isinstance(draft, QuestionDraft)
    assert len(draft.options) in (4, 5)
    assert draft.correct_answer_id is not None
    assert isinstance(review, ReviewScore)
    assert usage.prompt_tokens > 0
    assert usage.completion_tokens > 0

    # 2. Mock successful LLM response with valid self_critique json
    fused_json = """{
      "stimulus_text": "Clinical context here...",
      "question_stem": "Which option is definitive?",
      "options": [
        {"id": "A", "text": "First choice"},
        {"id": "B", "text": "Second choice"},
        {"id": "C", "text": "Third choice"},
        {"id": "D", "text": "Fourth choice"}
      ],
      "correct_answer_id": "C",
      "correct_answer_ids": ["C"],
      "explanation": "Option C is correct because of rule 1.",
      "image_needed": false,
      "image_prompt_or_type": null,
      "self_critique": {
        "authenticity_score": 25,
        "clarity_score": 24,
        "distractor_score": 24,
        "explanation_score": 25,
        "strengths": ["Authentic clinical vignette"],
        "weaknesses": [],
        "recommendations": []
      }
    }"""
    mock_usage = TokenUsage(
        prompt_tokens=420, completion_tokens=310, total_tokens=730, cost_usd=0.001
    )

    async def mock_call_llm(*_args, **_kwargs):
        return fused_json, mock_usage

    import app.agents.base as base_mod

    monkeypatch.setattr(gen_mod, "call_llm", mock_call_llm)
    monkeypatch.setattr(base_mod, "call_llm", mock_call_llm)

    draft2, review2, _usage2 = await generate_question_with_self_critique(req)
    assert draft2.question_stem == "Which option is definitive?"
    assert draft2.correct_answer_id in ("A", "B", "C", "D")
    assert f"Option {draft2.correct_answer_id} is correct" in draft2.explanation
    assert review2 is not None
    assert review2.total_score == 98
    assert review2.passed is True


@pytest.mark.asyncio
async def test_blind_solver_node_agreement(monkeypatch):
    from app.workflow.nodes import blind_solver_node

    req = GenerationRequest(section=MCATSection.BIO_BIOCHEM, difficulty=Difficulty.MEDIUM)
    draft = get_mock_draft(req)

    # Mock call_llm in blind_solver to agree with draft's key
    correct_text = next(o.text for o in draft.options if o.id == draft.correct_answer_id)

    async def mock_solver_llm(*_args, **kwargs):
        # The solver shows options in different layouts; answer with the letter shown for the
        # correct option's text, as a real solver that knows the right answer would.
        shown = next(
            line.split(".", 1)[0]
            for line in kwargs["prompt"].splitlines()
            if line[1:3] == ". " and line[3:] == correct_text
        )
        json_resp = f"""{{
            "selected_key": "{shown}",
            "confidence": 96,
            "is_ambiguous": false,
            "ambiguity_notes": "",
            "solver_rationale": "Option {draft.correct_answer_id} is indisputably proven."
        }}"""
        return json_resp, TokenUsage(
            prompt_tokens=100, completion_tokens=50, total_tokens=150, cost_usd=0.0001
        )

    monkeypatch.setattr(_base_module(), "call_llm", mock_solver_llm)

    state = {
        "request": req.model_dump(),
        "current_draft": draft.model_dump(),
        "current_review": {
            "total_score": 95,
            "passed": True,
            "weaknesses": [],
            "recommendations": [],
        },
        "iteration_count": 1,
    }
    result = await blind_solver_node(state)
    assert result["blind_solver_passed"] is True
    assert result["status"] == "blind_solver_passed"
    assert result["blind_solver_result"]["selected_key"] == draft.correct_answer_id


@pytest.mark.asyncio
async def test_blind_solver_node_discrepancy_triggers_critique(monkeypatch):
    from app.workflow.nodes import blind_solver_node

    req = GenerationRequest(section=MCATSection.BIO_BIOCHEM, difficulty=Difficulty.MEDIUM)
    draft = get_mock_draft(req)
    wrong_key = "C" if draft.correct_answer_id != "C" else "A"

    async def mock_solver_llm(*_args, **_kwargs):
        json_resp = f"""{{
            "selected_key": "{wrong_key}",
            "confidence": 92,
            "is_ambiguous": true,
            "ambiguity_notes": "Stem can be interpreted in two ways.",
            "solver_rationale": "Option {wrong_key} is defended under interpretation 2."
        }}"""
        return json_resp, TokenUsage(
            prompt_tokens=100, completion_tokens=50, total_tokens=150, cost_usd=0.0001
        )

    monkeypatch.setattr(_base_module(), "call_llm", mock_solver_llm)

    state = {
        "request": req.model_dump(),
        "current_draft": draft.model_dump(),
        "current_review": {
            "total_score": 95,
            "passed": True,
            "weaknesses": [],
            "recommendations": [],
        },
        "iteration_count": 1,
    }
    result = await blind_solver_node(state)
    assert result["blind_solver_passed"] is False
    assert result["status"] == "blind_solver_failed"
    # Ensure current_review was penalized below passing threshold to route to regenerator
    assert result["current_review"]["total_score"] <= 90
    assert any("Blind Solver" in w for w in result["current_review"]["weaknesses"])
