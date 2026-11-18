"""
test_dedup_decomposition.py - Verifies CQRS & structural decomposition of the deduplication engine.
"""

from __future__ import annotations

import pytest
from app.services import dedup_clustering, dedup_metrics, deduplication


def test_facade_reexports_exact_object_identities():
    """All symbols re-exported by deduplication must be the identical objects from submodules."""
    assert deduplication.DuplicateCheckResult is dedup_metrics.DuplicateCheckResult
    assert deduplication.DuplicateCluster is dedup_metrics.DuplicateCluster
    assert deduplication.DuplicateMember is dedup_metrics.DuplicateMember
    assert deduplication.normalize_text is dedup_metrics.normalize_text
    assert deduplication.extract_content_tokens is dedup_metrics.extract_content_tokens
    assert deduplication.normalize_token_stem is dedup_metrics.normalize_token_stem
    assert deduplication.extract_normalized_stem_set is dedup_metrics.extract_normalized_stem_set
    assert deduplication.get_or_create_stem_tokens is dedup_metrics.get_or_create_stem_tokens
    assert deduplication.compute_sequence_ratio is dedup_metrics.compute_sequence_ratio
    assert deduplication.compute_stem_similarity is dedup_metrics.compute_stem_similarity
    assert deduplication.compute_options_overlap is dedup_metrics.compute_options_overlap
    assert deduplication.compute_question_similarity is dedup_metrics.compute_question_similarity
    assert deduplication.cluster_questions is dedup_clustering.cluster_questions
    assert deduplication.STOP_WORDS is dedup_metrics.STOP_WORDS


def test_metric_calculations_match_across_submodule_and_facade():
    """Calculations called via dedup_metrics or deduplication must yield identical results."""
    t1 = "A competitive inhibitor increases apparent Km without changing Vmax."
    t2 = "Competitive enzyme inhibitors increase apparent Km while leaving Vmax unaltered."

    sim_facade = deduplication.compute_stem_similarity(t1, t2)
    sim_submodule = dedup_metrics.compute_stem_similarity(t1, t2)
    assert sim_facade == sim_submodule
    assert sim_facade > 0.50

    ratio_facade = deduplication.compute_sequence_ratio(t1, t2)
    ratio_submodule = dedup_metrics.compute_sequence_ratio(t1, t2)
    assert ratio_facade == ratio_submodule
    assert deduplication._STEM_TOKEN_CACHE is dedup_metrics._STEM_TOKEN_CACHE


def test_clustering_equivalence_across_facade():
    """cluster_questions yields identical cluster groups regardless of import path."""
    questions = [
        {
            "id": "q1",
            "question_stem": "What is the primary action of competitive inhibitors?",
            "options": [{"id": "A", "text": "Increases Km"}, {"id": "B", "text": "Decreases Km"}],
            "final_score": 90,
        },
        {
            "id": "q2",
            "question_stem": "What is the main action of competitive inhibitors?",
            "options": [{"id": "A", "text": "Increases Km"}, {"id": "B", "text": "Decreases Km"}],
            "final_score": 85,
        },
        {
            "id": "q3",
            "question_stem": "Describe the physiological function of the glomerulus in renal filtration.",
            "options": [{"id": "A", "text": "Filtration"}, {"id": "B", "text": "Secretion"}],
            "final_score": 92,
        },
    ]

    clusters_facade = deduplication.cluster_questions(questions, threshold=0.70)
    clusters_submodule = dedup_clustering.cluster_questions(questions, threshold=0.70)

    assert len(clusters_facade) == 1
    assert len(clusters_submodule) == 1
    assert clusters_facade[0]["leader_question"]["id"] == "q1"
    assert clusters_facade[0]["duplicates"][0]["question"]["id"] == "q2"
    assert clusters_facade == clusters_submodule


def test_evaluate_duplicate_uses_metrics_properly():
    """evaluate_duplicate coordinates metrics to classify collision states."""
    cand = {
        "id": "cand-1",
        "question_stem": "How does competitive inhibition alter enzyme kinetics?",
        "options": [{"id": "A", "text": "Increases apparent Km"}],
    }
    pool = [
        {
            "id": "ref-1",
            "question_stem": "How does competitive inhibition affect enzyme kinetics?",
            "options": [{"id": "A", "text": "Increases apparent Km"}],
        }
    ]
    res = deduplication.evaluate_duplicate(cand, pool, threshold=0.70)
    assert isinstance(res, deduplication.DuplicateCheckResult)
    assert res.is_duplicate is True
    assert res.matched_question_id == "ref-1"
    assert res.similarity_score > 0.70


@pytest.mark.asyncio
async def test_judge_semantic_duplicate_offline_boundary():
    """judge_semantic_duplicate falls back to score heuristics cleanly in offline mode."""
    q_cand = {"question_stem": "Question about enzyme rate", "explanation": "Km increases"}
    q_ref = {"question_stem": "Question regarding enzyme speed", "explanation": "Km rises"}

    is_dup, score, reason = await deduplication.judge_semantic_duplicate(q_cand, q_ref)
    assert isinstance(is_dup, bool)
    assert isinstance(score, float)
    assert isinstance(reason, str)
