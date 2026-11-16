from __future__ import annotations

from datetime import UTC, datetime

from app.models.question import QuestionModel
from app.repositories.mappers import model_to_schema, schema_to_model
from app.repositories.query_builders import (
    DIFFICULTY_ALIASES,
    SLIM_DEFER,
    build_question_filters,
)
from app.schemas.question import OptionChoice, Question, ReviewScore


def _sample_review_rubric_dict() -> dict:
    return {
        "authenticity_score": 23,
        "clarity_score": 23,
        "distractor_score": 23,
        "explanation_score": 23,
        "total_score": 92,
        "strengths": ["Clear stem", "Authentic style"],
        "weaknesses": [],
        "recommendations": [],
        "passed": True,
    }


def test_slim_defer_structure():
    assert len(SLIM_DEFER) == 3


def test_difficulty_aliases_coverage():
    assert "low" in DIFFICULTY_ALIASES
    assert "easy" in DIFFICULTY_ALIASES
    assert "medium" in DIFFICULTY_ALIASES
    assert "standard" in DIFFICULTY_ALIASES
    assert "high" in DIFFICULTY_ALIASES
    assert "hard" in DIFFICULTY_ALIASES
    assert "easy" in [x.lower() for x in DIFFICULTY_ALIASES["low"]]
    assert "standard" in [x.lower() for x in DIFFICULTY_ALIASES["medium"]]
    assert "hard" in [x.lower() for x in DIFFICULTY_ALIASES["high"]]


def test_model_to_schema_full_and_slim():
    now = datetime.now(UTC)
    model = QuestionModel(
        id="q-test-123",
        run_id="run-1",
        batch_id="batch-1",
        job_id="job-1",
        status="in_bank",
        section="CPBS",
        section_label="Chemical and Physical Foundations",
        subtopic="Thermodynamics",
        difficulty="hard",
        stimulus_text="Passage text here",
        question_stem="What is the free energy change?",
        options=[
            {"id": "A", "text": "Positive", "is_correct": False},
            {"id": "B", "text": "Negative", "is_correct": True},
        ],
        correct_answer_id="B",
        correct_answer_ids=["B"],
        explanation="Negative Delta G indicates spontaneity.",
        final_score=92,
        review_rubric=_sample_review_rubric_dict(),
        iteration_count=2,
        iterations_history=[{"iteration": 1, "score": 75}, {"iteration": 2, "score": 92}],
        created_at=now,
        updated_at=now,
        total_tokens=1200,
        prompt_tokens=800,
        completion_tokens=400,
        cost_usd=0.0054,
        token_usage_details=[{"call": "draft", "tokens": 600}],
        stage_outcomes={"planner": "success", "reviewer": "approved"},
    )

    # Full conversion
    full_schema = model_to_schema(model, slim=False)
    assert full_schema.id == "q-test-123"
    assert full_schema.final_score == 92
    assert len(full_schema.options) == 2
    assert full_schema.review_rubric is not None
    assert full_schema.review_rubric.total_score == 92
    assert full_schema.review_rubric.passed is True
    assert "Clear stem" in full_schema.review_rubric.strengths
    assert len(full_schema.iterations_history) == 2
    assert len(full_schema.token_usage_details) == 1
    assert full_schema.stage_outcomes["reviewer"] == "approved"

    # Slim conversion
    slim_schema = model_to_schema(model, slim=True)
    assert slim_schema.id == "q-test-123"
    assert slim_schema.iterations_history == []
    assert slim_schema.token_usage_details == []
    assert slim_schema.stage_outcomes == {}


def test_model_to_schema_csv_answer_ids_fallback():
    model = QuestionModel(
        id="q-csv-ans",
        correct_answer_id="a, c",
        correct_answer_ids=None,
        options=[{"id": "A", "text": "A"}, {"id": "C", "text": "C"}],
        question_stem="Stem",
        explanation="Exp",
        section="CARS",
        section_label="Critical Analysis and Reasoning Skills",
        subtopic="Humanities",
        difficulty="medium",
        final_score=85,
    )
    schema = model_to_schema(model)
    assert schema.correct_answer_ids == ["A", "C"]


def test_schema_to_model_round_trip():
    rubric = ReviewScore(
        authenticity_score=22,
        clarity_score=22,
        distractor_score=22,
        explanation_score=22,
        total_score=88,
        strengths=["Solid scientific style"],
    )
    q = Question(
        id="q-roundtrip",
        run_id="run-rt",
        section="BBLS",
        section_label="Biological and Biochemical Foundations",
        subtopic="Enzymes",
        difficulty="medium",
        stimulus_text="Enzyme kinetics text",
        question_stem="What happens at Vmax?",
        options=[
            OptionChoice(id="A", text="Active sites saturated", is_correct=True),
            OptionChoice(id="B", text="Substrate depleted", is_correct=False),
        ],
        correct_answer_id="A",
        correct_answer_ids=["A"],
        explanation="Enzyme active sites are saturated at Vmax.",
        final_score=88,
        review_rubric=rubric,
        stage_outcomes={"validator": "passed"},
    )

    model = schema_to_model(q)
    assert model.id == "q-roundtrip"
    assert model.section == "BBLS"
    assert len(model.options) == 2
    assert model.options[0]["id"] == "A"
    assert model.review_rubric["total_score"] == 88
    assert model.review_rubric["strengths"] == ["Solid scientific style"]
    assert model.stage_outcomes["validator"] == "passed"


def test_build_question_filters():
    # 1. Default filters include active clause
    filters = build_question_filters()
    assert len(filters) == 1  # active_question_clause

    # 2. include_deleted=True omits active clause
    filters_del = build_question_filters(include_deleted=True)
    assert len(filters_del) == 0

    # 3. Section and difficulty alias filtering
    filters_spec = build_question_filters(section="CPBS", difficulty="easy")
    assert len(filters_spec) >= 3  # active, section, difficulty in aliases

    # 4. Status = ai_validated includes passing score threshold
    filters_validated = build_question_filters(status="ai_validated")
    # should contain active_question_clause, status clause, and passing score and_ condition
    assert len(filters_validated) == 3

    # 5. Search creates hybrid conditions
    filters_search = build_question_filters(search="enzyme kinetics")
    assert any("to_tsvector" in str(f) or "enzyme kinetics" in str(f) for f in filters_search)
