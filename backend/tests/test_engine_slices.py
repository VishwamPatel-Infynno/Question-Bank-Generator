"""Unit tests for the pure, closure-free pieces sliced out of ``workflow.engine``."""

from app.core.config import config
from app.workflow.engine import (
    RunLayout,
    SlotLedger,
    _build_diversity_context,
    _complete_message,
    _drafting_message,
    _initial_attempt_state,
    _is_sibling_collision,
    _make_event_factory,
    _resolve_passing_threshold,
    _resolve_run_layout,
    _shared_passage_payload,
)
from app.workflow.passage_prep import SharedPassageState
from tests.factories import make_request


def _layout(**overrides) -> RunLayout:
    fields = {
        "total_qty": 5,
        "batch_id": "b1",
        "job_id": "j1",
        "is_standalone_live_run": True,
        "is_single_passage_set": True,
        "shared_passage_id": "p1",
    }
    fields.update(overrides)
    return RunLayout(**fields)


# --- run layout -------------------------------------------------------------------------------


def test_layout_defaults_to_five_linked_questions_with_generated_ids():
    layout = _resolve_run_layout(make_request())
    assert layout.total_qty == 5
    assert layout.is_single_passage_set
    assert layout.effective_passage_count == 5
    assert layout.independent_count == 0
    assert layout.passage_mode == "single_passage"
    assert layout.is_standalone_live_run
    assert layout.batch_id and layout.job_id and layout.shared_passage_id


def test_layout_independent_mode_has_no_shared_passage():
    layout = _resolve_run_layout(make_request(passage_mode="independent", questions_to_generate=3))
    assert not layout.is_single_passage_set
    assert (layout.effective_passage_count, layout.independent_count) == (0, 3)
    assert layout.passage_mode == "independent"
    assert layout.shared_passage_id is None


def test_layout_passage_required_no_means_independent_except_for_cars():
    assert not _resolve_run_layout(make_request(passage_required="no")).is_single_passage_set
    cars = _resolve_run_layout(make_request(section="CARS", passage_required="no"))
    assert cars.is_single_passage_set


def test_layout_keeps_caller_ids_and_marks_batch_jobs_as_not_standalone():
    layout = _resolve_run_layout(
        make_request(batch_id="B", job_id="J", passage_id="P", questions_to_generate=1)
    )
    assert (layout.batch_id, layout.job_id, layout.shared_passage_id) == ("B", "J", "P")
    assert not layout.is_standalone_live_run
    assert layout.total_qty == 1


# --- slot ledger ------------------------------------------------------------------------------


def test_ledger_folds_each_attempt_and_sums_with_the_passage_spend():
    ledger = SlotLedger.for_slots(2)
    ledger.fold(0, None)  # an attempt that never built its state adds nothing
    ledger.fold(
        0,
        {
            "total_tokens": 10,
            "total_prompt_tokens": 7,
            "total_completion_tokens": 3,
            "total_cost_usd": 0.001,
            "agent_usage_breakdown": [{"agent": "writer", "total_tokens": 10}],
        },
    )
    ledger.fold(1, {"total_tokens": 5, "total_cost_usd": 0.0005, "agent_usage_breakdown": []})
    assert ledger.tokens == [10, 5]
    assert ledger.all_usage() == [{"agent": "writer", "total_tokens": 10}]
    passage = SharedPassageState(tokens=100, prompt_tokens=60, completion_tokens=40, cost=0.01)
    assert ledger.cumulative(passage) == {
        "total_tokens": 115,
        "total_prompt_tokens": 67,
        "total_completion_tokens": 43,
        "total_cost_usd": 0.0115,
    }
    assert ledger.cumulative()["total_tokens"] == 15


def test_ledger_budget_counts_llm_calls_and_a_zero_limit_disables_the_cap():
    ledger = SlotLedger.for_slots(1)
    # mock/heuristic entries record no calls and never count against the budget
    ledger.fold(0, {"agent_usage_breakdown": [{"calls": 1}, {"calls": 1}, {"agent": "mock"}]})
    assert ledger.calls[0] == 2
    assert ledger.budget_spent(0, 2)
    assert not ledger.budget_spent(0, 3)
    assert not ledger.budget_spent(0, 0)


# --- per-attempt helpers ----------------------------------------------------------------------


def test_diversity_context_only_for_sets_or_retries():
    assert _build_diversity_context(0, 1, 0, [], []) is None
    first = _build_diversity_context(1, 5, 0, ["t1", "t2", "t3", "t4", "t5"], ["m1"])
    assert first.startswith("Item 2 of 5")
    assert "t2, t3, t4, t5" in first and "t1" not in first  # only the last four traps
    assert "m1" in first
    retry = _build_diversity_context(0, 1, 1, ["t1"], [])
    assert "REPLENISHMENT ATTEMPT 2" in retry and "t1" not in retry


def test_drafting_message_variants():
    assert _drafting_message(0, 5, 1, True, "single_choice").startswith("[1/5] Calibrating")
    assert "linked Single Choice question" in _drafting_message(1, 5, 0, True, "single_choice")
    assert "independent Single Choice question" in _drafting_message(
        1, 5, 0, False, "single_choice"
    )


def test_passing_threshold_precedence(monkeypatch):
    item, run = make_request(passing_threshold=70), make_request(passing_threshold=80)
    assert _resolve_passing_threshold(item, run) == 70
    assert _resolve_passing_threshold(make_request(), run) == 80
    assert (
        _resolve_passing_threshold(make_request(), make_request()) == config.PASSING_SCORE_THRESHOLD
    )


def test_initial_attempt_state_marks_offline_runs(monkeypatch):
    req = make_request()
    monkeypatch.setattr(config, "OFFLINE_MODE", True)
    state = _initial_attempt_state(req, "run-1", "b1", "ctx", 85, slot_prior_calls=2)
    assert state["stage_outcomes"] == {"offline_mode": True}
    assert (state["run_id"], state["batch_id"], state["slot_prior_calls"]) == ("run-1", "b1", 2)
    assert state["request"]["subtopic"] == "Kinetics"
    monkeypatch.setattr(config, "OFFLINE_MODE", False)
    assert _initial_attempt_state(req, "r", "b", None, 85, 0)["stage_outcomes"] == {}


def test_sibling_collision_matches_staged_or_in_flight_siblings():
    staged = [{"id": "q-a"}, None]
    assert _is_sibling_collision({"is_duplicate": True, "matched_question_id": "q-a"}, staged)
    assert _is_sibling_collision(
        {"is_duplicate": True, "matched_question_id": "in_flight_b1_2"}, staged
    )
    assert not _is_sibling_collision({"is_duplicate": True, "matched_question_id": "db-q"}, staged)
    assert not _is_sibling_collision({"is_duplicate": False, "matched_question_id": "q-a"}, staged)


# --- events -----------------------------------------------------------------------------------


def test_event_factory_stamps_ids_without_overriding_them():
    make_event = _make_event_factory(make_request(run_id="run-x"), "b1", "j1")
    evt = make_event("agent_start", "System", "hi")
    assert (evt.run_id, evt.batch_id) == ("run-x", "b1")
    assert evt.data == {"batch_id": "b1", "job_id": "j1"}
    kept = make_event("x", "S", "m", data={"job_id": "other"}, run_id="item-run")
    assert kept.data["job_id"] == "other" and kept.run_id == "item-run"


def test_shared_passage_payload_is_blank_for_independent_runs():
    passage = SharedPassageState(
        passage_text="text", image_url="u", image_svg="<svg/>", image_desc="d"
    )
    linked = _shared_passage_payload(_layout(), passage)
    assert linked["shared_passage"] == "text" and linked["shared_passage_image_svg"] == "<svg/>"
    assert linked["passage_question_count"] == 5
    independent = _shared_passage_payload(_layout(is_single_passage_set=False), passage)
    assert independent["passage_mode"] == "independent"
    assert independent["independent_question_count"] == 5
    assert all(independent[k] is None for k in independent if k.startswith("shared_passage"))


def test_complete_message_variants():
    usage = {"total_tokens": 42, "total_cost_usd": 0.00123}
    assert _complete_message(_layout(), [{}, {}], usage).startswith(
        "Passage Set generated! 2 questions"
    )
    batch = _complete_message(_layout(is_single_passage_set=False), [{}], usage)
    assert "1 of 5 questions" in batch and "42 tokens ($0.00123)" in batch
    single = _complete_message(_layout(total_qty=1), [{"final_score": 91}], usage)
    assert "scored 91/100" in single
    assert "scored 95/100" in _complete_message(_layout(total_qty=1), [], usage)
