"""
Unit tests verifying the CQRS decomposition of question_repository into
question_queries and question_mutations.
"""

from __future__ import annotations

import app.repositories as repos
import app.repositories.question_mutations as q_mut
import app.repositories.question_queries as q_queries
import app.repositories.question_repository as q_repo
import pytest


def test_facade_reexports_all_expected_symbols():
    """All 19 DAL functions, classes, and constants must be available via app.repositories.question_repository."""
    expected = {
        "QuestionHead",
        "_VISIBLE_STATUSES",
        "batch_update_question_status",
        "count_questions",
        "delete_question",
        "delete_questions_batch",
        "get_active_batch_questions",
        "get_active_job_question_heads",
        "get_question_by_id",
        "get_question_status_counts",
        "get_questions",
        "get_repository_metrics",
        "get_subtopic_reference_questions",
        "hard_delete_question",
        "hard_delete_questions_batch",
        "override_question_duplicate",
        "restore_question",
        "save_question",
        "save_questions_batch",
        "update_question_status",
    }
    assert set(q_repo.__all__) == expected
    for name in expected:
        assert hasattr(q_repo, name), f"question_repository missing symbol {name}"


def test_queries_module_contains_expected_symbols():
    """question_queries owns all read and aggregation routines."""
    expected_queries = {
        "QuestionHead",
        "count_questions",
        "get_active_batch_questions",
        "get_active_job_question_heads",
        "get_question_by_id",
        "get_question_status_counts",
        "get_questions",
        "get_repository_metrics",
        "get_subtopic_reference_questions",
    }
    for name in expected_queries:
        assert hasattr(q_queries, name), f"question_queries missing symbol {name}"


def test_mutations_module_contains_expected_symbols():
    """question_mutations owns all write, update, deletion, and lifecycle routines."""
    expected_mutations = {
        "_VISIBLE_STATUSES",
        "batch_update_question_status",
        "delete_question",
        "delete_questions_batch",
        "hard_delete_question",
        "hard_delete_questions_batch",
        "override_question_duplicate",
        "restore_question",
        "save_question",
        "save_questions_batch",
        "update_question_status",
    }
    for name in expected_mutations:
        assert hasattr(q_mut, name), f"question_mutations missing symbol {name}"


def test_facade_symbols_are_identical_objects():
    """Symbols in question_repository facade must match their child module implementations exactly."""
    assert q_repo.QuestionHead is q_queries.QuestionHead
    assert q_repo.count_questions is q_queries.count_questions
    assert q_repo.get_questions is q_queries.get_questions
    assert q_repo.get_question_by_id is q_queries.get_question_by_id
    assert q_repo.get_active_batch_questions is q_queries.get_active_batch_questions
    assert q_repo.get_active_job_question_heads is q_queries.get_active_job_question_heads
    assert q_repo.get_question_status_counts is q_queries.get_question_status_counts
    assert q_repo.get_repository_metrics is q_queries.get_repository_metrics
    assert q_repo.get_subtopic_reference_questions is q_queries.get_subtopic_reference_questions

    assert q_repo._VISIBLE_STATUSES is q_mut._VISIBLE_STATUSES
    assert q_repo.save_question is q_mut.save_question
    assert q_repo.save_questions_batch is q_mut.save_questions_batch
    assert q_repo.delete_question is q_mut.delete_question
    assert q_repo.delete_questions_batch is q_mut.delete_questions_batch
    assert q_repo.hard_delete_question is q_mut.hard_delete_question
    assert q_repo.hard_delete_questions_batch is q_mut.hard_delete_questions_batch
    assert q_repo.restore_question is q_mut.restore_question
    assert q_repo.update_question_status is q_mut.update_question_status
    assert q_repo.batch_update_question_status is q_mut.batch_update_question_status
    assert q_repo.override_question_duplicate is q_mut.override_question_duplicate


def test_repositories_package_reexports_match():
    """app.repositories top-level re-exports must also match identical object definitions."""
    assert repos.get_questions is q_queries.get_questions
    assert repos.save_question is q_mut.save_question
    assert repos.get_active_job_question_heads is q_queries.get_active_job_question_heads
    assert repos.hard_delete_question is q_mut.hard_delete_question


def test_question_head_dataclass():
    """QuestionHead frozen dataclass must hold expected fields and enforce immutability."""
    head = q_queries.QuestionHead(
        id="q_100",
        status="in_bank",
        stimulus_text="Enzyme kinetics stem...",
        passage_id="p_50",
    )
    assert head.id == "q_100"
    assert head.status == "in_bank"
    assert head.stimulus_text == "Enzyme kinetics stem..."
    assert head.passage_id == "p_50"

    with pytest.raises(AttributeError):
        head.status = "discarded"  # type: ignore


def test_session_parameter_support_across_repositories():
    """All DAL mutation, query, and passage functions must support session: AsyncSession | None = None."""
    import inspect

    import app.repositories.passage_repository as p_repo

    functions_to_check = [
        # Queries
        q_queries.get_questions,
        q_queries.count_questions,
        q_queries.get_question_by_id,
        q_queries.get_repository_metrics,
        # Mutations
        q_mut.save_question,
        q_mut.save_questions_batch,
        q_mut.delete_question,
        q_mut.delete_questions_batch,
        q_mut.restore_question,
        q_mut.update_question_status,
        q_mut.batch_update_question_status,
        q_mut.override_question_duplicate,
        # Passages
        p_repo.get_passages,
        p_repo.count_passages,
        p_repo.get_passage_by_id,
        p_repo.save_passage,
        p_repo.delete_passage,
        p_repo.restore_passage,
    ]
    for fn in functions_to_check:
        sig = inspect.signature(fn)
        assert "session" in sig.parameters, (
            f"Function {fn.__name__} does not accept session parameter"
        )
        param = sig.parameters["session"]
        assert param.default is None, f"Function {fn.__name__} session default should be None"
