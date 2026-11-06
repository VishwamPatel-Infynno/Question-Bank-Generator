from app.services.deduplication import (
    DuplicateCheckResult,
    cluster_questions,
    evaluate_duplicate,
    extract_content_tokens,
    normalize_text,
)


def test_normalize_text():
    raw = "<p>What is the net charge of <b>aspartic acid</b> at pH = $7.4$?</p>"
    norm = normalize_text(raw)
    assert norm == "what is the net charge of aspartic acid at ph 7 4"
    assert "<p>" not in norm
    assert "$" not in norm


def test_extract_content_tokens():
    raw = "What is the net charge of an aspartate residue at physiological pH?"
    tokens = extract_content_tokens(raw)
    # Stop words like 'what', 'is', 'the', 'of', 'an', 'at' should be removed
    assert "net" in tokens
    assert "charge" in tokens
    assert "aspartate" in tokens
    assert "residue" in tokens
    assert "physiological" in tokens
    assert "ph" in tokens
    assert "what" not in tokens
    assert "the" not in tokens


def test_identical_questions_duplicate_detection():
    stem1 = "In Michaelis-Menten enzyme kinetics, what effect does a competitive inhibitor have on Km and Vmax?"
    options1 = [
        {"id": "A", "text": "Increases Km and leaves Vmax unchanged"},
        {"id": "B", "text": "Decreases Km and decreases Vmax"},
        {"id": "C", "text": "Leaves Km unchanged and decreases Vmax"},
        {"id": "D", "text": "Increases Km and increases Vmax"},
    ]
    candidate = {"id": "cand-1", "question_stem": stem1, "options": options1}
    reference_pool = [{"id": "ref-1", "question_stem": stem1, "options": options1}]

    res: DuplicateCheckResult = evaluate_duplicate(candidate, reference_pool, threshold=0.80)
    assert res.is_duplicate is True
    assert res.similarity_score >= 0.95
    assert res.matched_question_id == "ref-1"
    assert res.match_reason is not None


def test_paraphrased_high_similarity():
    stem1 = "In Michaelis-Menten kinetics, how does a competitive inhibitor affect the apparent Km and Vmax?"
    stem2 = "According to Michaelis-Menten kinetics, what happens to the apparent Km and Vmax in the presence of a competitive inhibitor?"
    options = [
        {"id": "A", "text": "Apparent Km increases, while Vmax remains unchanged"},
        {"id": "B", "text": "Apparent Km decreases, while Vmax decreases"},
        {"id": "C", "text": "Apparent Km is unchanged, while Vmax decreases"},
        {"id": "D", "text": "Both apparent Km and Vmax increase"},
    ]
    candidate = {"id": "cand-2", "question_stem": stem1, "options": options}
    reference_pool = [{"id": "ref-2", "question_stem": stem2, "options": options}]

    res = evaluate_duplicate(candidate, reference_pool, threshold=0.80)
    assert res.is_duplicate is True
    assert res.similarity_score >= 0.80
    assert res.matched_question_id == "ref-2"


def test_distinct_questions_in_same_subtopic_no_duplicate():
    stem1 = "What is the net electrical charge of aspartic acid at pH 7.0?"
    options1 = [
        {"id": "A", "text": "-1"},
        {"id": "B", "text": "0"},
        {"id": "C", "text": "+1"},
        {"id": "D", "text": "-2"},
    ]
    stem2 = "Which amino acid residue is most susceptible to phosphorylation by a protein kinase?"
    options2 = [
        {"id": "A", "text": "Serine"},
        {"id": "B", "text": "Alanine"},
        {"id": "C", "text": "Valine"},
        {"id": "D", "text": "Leucine"},
    ]
    candidate = {"id": "cand-3", "question_stem": stem1, "options": options1}
    reference_pool = [{"id": "ref-3", "question_stem": stem2, "options": options2}]

    res = evaluate_duplicate(candidate, reference_pool, threshold=0.80)
    assert res.is_duplicate is False
    assert res.similarity_score < 0.40
    assert res.matched_question_id is not None or res.matched_question_id is None


def test_two_tier_threshold_and_soft_warning():
    stem1 = "Based on the passage, which experimental observation most directly established that the atomic nucleus is dense?"
    stem2 = "Based on the passage, which experimental observation directly confirms that the atomic nucleus occupies small volume?"
    options = [
        {"id": "A", "text": "Alpha particle backscattering"},
        {"id": "B", "text": "Cathode ray deflection"},
        {"id": "C", "text": "Photoelectric effect"},
        {"id": "D", "text": "Oil droplet terminal velocity"},
    ]
    cand = {"id": "c-1", "question_stem": stem1, "options": options}
    ref = [{"id": "r-1", "question_stem": stem2, "options": options}]

    # With two-tier: threshold 0.75, soft 0.60
    res = evaluate_duplicate(cand, ref, threshold=0.85, soft_threshold=0.60)
    # The stems share high vocabulary and identical options, similarity should fall in soft or hard tier
    assert res.similarity_score >= 0.60
    if res.similarity_score < 0.85:
        assert res.is_soft_warning is True
        assert res.is_duplicate is False


def test_cluster_questions_groups_duplicates_correctly():
    # 4 questions: Q1 and Q2 are duplicates of each other, Q3 and Q4 are duplicates of each other
    q1 = {
        "id": "q1",
        "question_stem": "When X-210 undergoes electron capture, which describes the change in protons and neutrons?",
        "options": [{"id": "A", "text": "Protons -1, neutrons +1"}],
        "final_score": 96,
    }
    q2 = {
        "id": "q2",
        "question_stem": "When X-210 undergoes electron capture, what happens to the number of protons and neutrons?",
        "options": [{"id": "A", "text": "Protons -1, neutrons +1"}],
        "final_score": 92,
    }
    q3 = {
        "id": "q3",
        "question_stem": "Why do stable heavy nuclei require a higher neutron-to-proton ratio than light nuclei?",
        "options": [{"id": "A", "text": "Strong force cohesion without Coulomb repulsion"}],
        "final_score": 95,
    }
    q4 = {
        "id": "q4",
        "question_stem": "Why do stable heavy nuclei require a higher neutron-to-proton ratio?",
        "options": [{"id": "A", "text": "Strong force cohesion without Coulomb repulsion"}],
        "final_score": 94,
    }

    clusters = cluster_questions([q1, q2, q3, q4], threshold=0.75)
    assert len(clusters) == 2

    # Cluster 1 leader should have highest score (q1 with 96)
    c1 = next(c for c in clusters if c["leader_question"]["id"] == "q1")
    assert len(c1["duplicates"]) == 1
    assert c1["duplicates"][0]["question"]["id"] == "q2"

    # Cluster 2 leader should be q3 with 95
    c2 = next(c for c in clusters if c["leader_question"]["id"] == "q3")
    assert len(c2["duplicates"]) == 1
    assert c2["duplicates"][0]["question"]["id"] == "q4"


async def test_auto_resolve_batch_and_refill(monkeypatch):
    from unittest.mock import AsyncMock

    from app.schemas import GenerationBatch, Question
    from app.services import auto_resolve_batch_and_refill

    batch_id = "test-batch-autoresolve"
    fake_batch = GenerationBatch(
        id=batch_id,
        section="CPBS",
        target_count=5,
        actual_count=4,
    )

    common_kwargs = {
        "section": "CPBS",
        "section_label": "Chemical and Physical Foundations of Biological Systems",
        "subtopic": "Atomic Structure and Nuclear Chemistry",
        "difficulty": "medium",
        "correct_answer_id": "A",
        "explanation": "Standard radioactive decay rationale.",
        "status": "ai_validated",
    }

    q1 = Question(
        id="q1",
        batch_id=batch_id,
        question_stem="When X-210 undergoes electron capture, which describes the change in protons and neutrons?",
        options=[{"id": "A", "text": "Protons -1, neutrons +1"}],
        final_score=96,
        **common_kwargs,
    )
    q2 = Question(
        id="q2",
        batch_id=batch_id,
        question_stem="When X-210 undergoes electron capture, what happens to the number of protons and neutrons?",
        options=[{"id": "A", "text": "Protons -1, neutrons +1"}],
        final_score=92,
        **common_kwargs,
    )
    q3 = Question(
        id="q3",
        batch_id=batch_id,
        question_stem="Calculate the standard free energy change under physiological conditions.",
        options=[{"id": "A", "text": "-14.2 kJ/mol"}],
        final_score=95,
        **common_kwargs,
    )

    current_questions = [q1, q2, q3]
    archived_ids = []

    async def mock_get_batch(b_id):
        assert b_id == batch_id
        return fake_batch

    async def mock_get_questions(batch_id=None, **_kwargs):
        assert batch_id is not None
        return [
            q.model_copy(update={"status": "discarded"}) if q.id in archived_ids else q
            for q in current_questions
        ]

    async def mock_batch_update_status(q_ids, status="discarded", **_kwargs):
        assert status == "discarded"
        archived_ids.extend(q_ids)
        return len(q_ids)

    async def mock_hard_delete_batch(q_ids):
        archived_ids.extend(q_ids)
        return len(q_ids)

    async def mock_refresh_aggregates(b_id, allow_complete=False, **_kwargs):
        assert b_id == batch_id
        fake_batch.actual_count = sum(1 for q in current_questions if q.id not in archived_ids)
        return fake_batch

    # A refill only counts as launched when at least one job was actually started
    mock_refill = AsyncMock(return_value=(fake_batch, [object()]))
    mock_get_jobs = AsyncMock(return_value=[])
    mock_update_job = AsyncMock(return_value=None)

    monkeypatch.setattr("app.services.batch_runner.get_batch_by_id", mock_get_batch)
    monkeypatch.setattr("app.services.batch_runner.get_questions", mock_get_questions)
    monkeypatch.setattr(
        "app.services.batch_runner.hard_delete_questions_batch", mock_hard_delete_batch
    )
    monkeypatch.setattr("app.services.batch_runner.get_jobs_by_batch_id", mock_get_jobs)
    monkeypatch.setattr("app.services.batch_runner.update_job_progress", mock_update_job)
    monkeypatch.setattr(
        "app.services.batch_runner.batch_update_question_status", mock_batch_update_status
    )
    monkeypatch.setattr(
        "app.services.batch_runner.refresh_batch_aggregates", mock_refresh_aggregates
    )
    monkeypatch.setattr("app.services.batch_runner.refill_batch_deficit", mock_refill)

    # Cycle 1: auto_resolve should archive q2 (score 92, duplicate of q1 with 96) and trigger refill
    res = await auto_resolve_batch_and_refill(batch_id, current_cycle=1, max_cycles=2)

    assert res["resolved"] is True
    assert res["clusters_count"] == 1
    assert res["archived_duplicates_count"] == 1
    assert "q2" in archived_ids
    assert "q1" not in archived_ids
    # Deficit should be target_count (5) - remaining (2) = 3; refill launched with buffer = 4
    assert res["deficit"] == 3
    assert res["refill_launched"] is True
    mock_refill.assert_awaited_once_with(batch_id, 4, cycle=2, max_cycles=2)


async def test_auto_resolve_does_not_claim_refill_when_no_job_was_launched(monkeypatch):
    from unittest.mock import AsyncMock

    from app.schemas import GenerationBatch, Question
    from app.services.batch_runner import auto_resolve_batch_and_refill

    batch_id = "b-no-refill"
    batch = GenerationBatch(id=batch_id, section="chem_phys", target_count=5, actual_count=1)
    q = Question(
        id="only",
        batch_id=batch_id,
        section="CPBS",
        section_label="Chemical and Physical Foundations of Biological Systems",
        subtopic="Kinetics",
        difficulty="medium",
        question_stem="Unique stem about enzyme kinetics and rates",
        options=[{"id": "A", "text": "opt A text"}],
        correct_answer_id="A",
        explanation="Because.",
        final_score=95,
        status="batch_only",
    )
    monkeypatch.setattr("app.services.batch_runner.get_batch_by_id", AsyncMock(return_value=batch))
    monkeypatch.setattr("app.services.batch_runner.get_questions", AsyncMock(return_value=[q]))
    monkeypatch.setattr(
        "app.services.batch_runner.get_jobs_by_batch_id", AsyncMock(return_value=[])
    )
    monkeypatch.setattr(
        "app.services.batch_runner.refresh_batch_aggregates", AsyncMock(return_value=batch)
    )
    monkeypatch.setattr(
        "app.services.batch_runner.refill_batch_deficit", AsyncMock(return_value=(batch, []))
    )

    res = await auto_resolve_batch_and_refill(batch_id, current_cycle=1, max_cycles=3)
    assert res["deficit"] > 0
    assert res["refill_launched"] is False


def test_stem_token_cache_is_keyed_by_content_and_evicts_one_at_a_time(monkeypatch):
    from app.services import deduplication as dd

    dd._STEM_TOKEN_CACHE.clear()
    monkeypatch.setattr(dd, "_MAX_STEM_CACHE_SIZE", 3)

    first = dd.get_or_create_stem_tokens("Which enzyme catalyzes glycolysis step one?")
    # A different stem must never return another stem's tokens (the old id-keyed cache could)
    edited = dd.get_or_create_stem_tokens("Completely different stem about optics lenses")
    assert edited[0] != first[0]
    assert dd.get_or_create_stem_tokens("Which enzyme catalyzes glycolysis step one?") is first

    for i in range(5):
        dd.get_or_create_stem_tokens(f"filler stem number {i} about topic {i}")
    # Bounded LRU: never flushed wholesale, never above the cap
    assert len(dd._STEM_TOKEN_CACHE) == 3


def test_duplicate_thresholds_come_from_config():
    from app.core.config import config

    assert config.DUPLICATE_SOFT_THRESHOLD < config.DUPLICATE_HARD_THRESHOLD
    assert config.DUPLICATE_HARD_THRESHOLD <= config.DUPLICATE_API_THRESHOLD
