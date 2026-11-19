"""
Unit tests verifying the decomposition of workflow nodes into specialized modules
across generator, reviewer, and finalize stages.
"""

from __future__ import annotations

import app.workflow.node_finalize as nf
import app.workflow.node_generator as ng
import app.workflow.node_reviewer as nr
import pytest
from app.schemas import (
    GenerationRequest,
    MCATSection,
    QuestionDraft,
    ReviewScore,
    TokenUsage,
)
from app.workflow import nodes
from app.workflow.state import AgentWorkflowState


def test_nodes_facade_reexports_all_expected_symbols():
    """All 14 node and lifecycle functions/classes must be available via app.workflow.nodes."""
    expected = {
        "ReviewAndSolveOutcome",
        "_record_agent_usage",
        "agent_usage_entry",
        "blind_solver_node",
        "build_review_update",
        "build_solver_update",
        "build_usage_only_update",
        "finalize_node",
        "fused_generator_node",
        "image_node",
        "regenerator_node",
        "reject_node",
        "reviewer_node",
        "run_review_and_solve",
    }
    assert expected.issubset(set(nodes.__all__))
    for name in expected:
        assert hasattr(nodes, name), f"app.workflow.nodes missing {name}"


def test_specialized_modules_contain_respective_symbols():
    """Each decomposed module owns its specific domain logic."""
    # Generator module
    assert hasattr(ng, "fused_generator_node")
    assert hasattr(ng, "agent_usage_entry")
    assert hasattr(ng, "_record_agent_usage")

    # Reviewer module
    assert hasattr(nr, "reviewer_node")
    assert hasattr(nr, "build_review_update")
    assert hasattr(nr, "ReviewAndSolveOutcome")
    assert hasattr(nr, "run_review_and_solve")
    assert hasattr(nr, "build_usage_only_update")
    assert hasattr(nr, "build_solver_update")
    assert hasattr(nr, "blind_solver_node")
    assert hasattr(nr, "regenerator_node")

    # Finalize module
    assert hasattr(nf, "reject_node")
    assert hasattr(nf, "image_node")
    assert hasattr(nf, "finalize_node")


def test_facade_reexports_are_identical_objects():
    """Facade symbols must be reference-identical to their decomposed module definitions."""
    assert nodes.fused_generator_node is ng.fused_generator_node
    assert nodes.agent_usage_entry is ng.agent_usage_entry
    assert nodes._record_agent_usage is ng._record_agent_usage

    assert nodes.reviewer_node is nr.reviewer_node
    assert nodes.build_review_update is nr.build_review_update
    assert nodes.ReviewAndSolveOutcome is nr.ReviewAndSolveOutcome
    assert nodes.run_review_and_solve is nr.run_review_and_solve
    assert nodes.build_usage_only_update is nr.build_usage_only_update
    assert nodes.build_solver_update is nr.build_solver_update
    assert nodes.blind_solver_node is nr.blind_solver_node
    assert nodes.regenerator_node is nr.regenerator_node

    assert nodes.reject_node is nf.reject_node
    assert nodes.image_node is nf.image_node
    assert nodes.finalize_node is nf.finalize_node


def test_facade_monkeypatch_synchronization(monkeypatch):
    """Setting attributes on nodes facade dynamically synchronizes them to child modules."""
    mock_sentinel = object()
    monkeypatch.setattr(nodes, "review_question", mock_sentinel)
    assert nr.review_question is mock_sentinel

    mock_gen_sentinel = object()
    monkeypatch.setattr(nodes, "generate_image_stimulus", mock_gen_sentinel)
    assert nf.generate_image_stimulus is mock_gen_sentinel


def test_agent_usage_accounting_helper():
    """agent_usage_entry and _record_agent_usage correctly accumulate tokens and cost."""
    usage = TokenUsage(
        prompt_tokens=150,
        completion_tokens=50,
        total_tokens=200,
        cost_usd=0.00045,
        calls=1,
        duration_ms=320,
    )
    entry = nodes.agent_usage_entry("Test Agent", usage, iteration=1)
    assert entry["agent"] == "Test Agent"
    assert entry["prompt_tokens"] == 150
    assert entry["completion_tokens"] == 50
    assert entry["total_tokens"] == 200
    assert entry["cost_usd"] == 0.00045
    assert entry["duration_ms"] == 320

    initial_state: AgentWorkflowState = {
        "request": {},
        "total_tokens": 100,
        "total_prompt_tokens": 80,
        "total_completion_tokens": 20,
        "total_cost_usd": 0.0002,
        "agent_usage_breakdown": [],
    }  # type: ignore

    update = nodes._record_agent_usage(initial_state, "Test Agent", usage, iteration=1)
    assert update["total_tokens"] == 300
    assert update["total_prompt_tokens"] == 230
    assert update["total_completion_tokens"] == 70
    assert update["total_cost_usd"] == pytest.approx(0.00065)
    assert len(update["agent_usage_breakdown"]) == 1


@pytest.mark.asyncio
async def test_reject_node_behavior():
    """reject_node creates the expected rejection_payload when score is below threshold."""
    req = GenerationRequest(
        section=MCATSection.BIO_BIOCHEM,
        difficulty="Hard",
        subtopic="Enzyme Kinetics",
    )
    draft = QuestionDraft(
        stimulus_text="",
        question_stem="Which parameter determines enzyme affinity?",
        options=[
            {"id": "A", "text": "Km"},
            {"id": "B", "text": "Vmax"},
            {"id": "C", "text": "kcat"},
            {"id": "D", "text": "kcat/Km"},
        ],
        correct_answer_id="A",
        explanation="Option A is correct because Km measures affinity. B is wrong. C is wrong. D is catalytic efficiency.",
    )
    review = ReviewScore(
        authenticity_score=18,
        clarity_score=18,
        distractor_score=18,
        explanation_score=18,
        total_score=72,
        passed=False,
        strengths=["Clear stem"],
        weaknesses=["Distractors need more nuance"],
        recommendations=["Refine option D explanation"],
    )

    state: AgentWorkflowState = {
        "request": req.model_dump(),
        "current_draft": draft.model_dump(),
        "current_review": review.model_dump(),
        "iteration_count": 3,
        "passing_threshold": 80,
        "total_tokens": 1200,
        "total_cost_usd": 0.0025,
    }  # type: ignore

    result = await nodes.reject_node(state)
    assert result["status"] == "rejected_below_threshold"
    assert result["active_agent"] == "Quality Gate"
    payload = result["rejection_data"]
    assert payload["final_score"] == 72
    assert payload["threshold"] == 80
    assert payload["iteration_count"] == 3


@pytest.mark.asyncio
async def test_finalize_node_behavior():
    """finalize_node builds a complete Question object from a passing draft."""
    req = GenerationRequest(
        section=MCATSection.PSYCH_SOC,
        difficulty="Medium",
        subtopic="Attribution Theory",
        auto_save=False,
    )
    draft = QuestionDraft(
        stimulus_text="",
        question_stem="Which bias describes attributing others' failures to internal flaws?",
        options=[
            {"id": "A", "text": "Fundamental attribution error"},
            {"id": "B", "text": "Self-serving bias"},
            {"id": "C", "text": "Actor-observer bias"},
            {"id": "D", "text": "Confirmation bias"},
        ],
        correct_answer_id="A",
        explanation="Option A is correct because FAE overemphasizes dispositional factors. B is wrong. C is wrong. D is wrong.",
    )
    review = ReviewScore(
        authenticity_score=24,
        clarity_score=23,
        distractor_score=24,
        explanation_score=23,
        total_score=94,
        passed=True,
        strengths=["High discriminative value"],
        weaknesses=[],
        recommendations=[],
    )

    state: AgentWorkflowState = {
        "request": req.model_dump(),
        "current_draft": draft.model_dump(),
        "current_review": review.model_dump(),
        "iteration_count": 1,
        "total_tokens": 1500,
        "total_prompt_tokens": 1000,
        "total_completion_tokens": 500,
        "total_cost_usd": 0.003,
        "agent_usage_breakdown": [],
    }  # type: ignore

    result = await nodes.finalize_node(state)
    assert result["status"] == "completed"
    assert result["active_agent"] == "Completed"
    final_q = result["final_question"]
    assert final_q["final_score"] == 94
    assert final_q["correct_answer_id"] == "A"
    assert final_q["status"] == "ai_validated"
