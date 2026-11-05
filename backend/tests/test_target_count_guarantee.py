import uuid
from datetime import UTC, datetime

import pytest
from app.repositories import (
    get_questions,
    refresh_batch_aggregates,
    save_batch,
    save_job,
    save_question,
)
from app.schemas import (
    Difficulty,
    GenerationBatch,
    GenerationJob,
    GenerationRequest,
    MCATSection,
    Question,
)
from app.services import (
    auto_resolve_batch_and_refill,
    launch_background_batch,
)

pytestmark = pytest.mark.requires_db


async def test_dynamic_job_allocation_in_batch_runner():
    """Verifies that launch_background_batch dynamically scales jobs and target quotas."""
    # Test 5 questions -> 1 job of 5
    req_5 = GenerationRequest(
        section=MCATSection.BIO_BIOCHEM,
        difficulty=Difficulty.MEDIUM,
        questions_to_generate=5,
    )
    b5, jobs5 = await launch_background_batch(req_5)
    assert b5.target_count == 5
    assert len(jobs5) == 1
    assert jobs5[0].target_count == 5

    # Test 50 questions -> 10 jobs of 5
    req_50 = GenerationRequest(
        section=MCATSection.CHEM_PHYS,
        difficulty=Difficulty.HIGH,
        questions_to_generate=50,
    )
    b50, jobs50 = await launch_background_batch(req_50)
    assert b50.target_count == 50
    assert len(jobs50) == 10
    assert all(j.target_count == 5 for j in jobs50)

    # Test 12 questions -> 3 jobs (5, 5, 2)
    req_12 = GenerationRequest(
        section=MCATSection.PSYCH_SOC,
        difficulty=Difficulty.MEDIUM,
        questions_to_generate=12,
    )
    b12, jobs12 = await launch_background_batch(req_12)
    assert b12.target_count == 12
    assert len(jobs12) == 3
    assert jobs12[0].target_count == 5
    assert jobs12[1].target_count == 5
    assert jobs12[2].target_count == 2


async def test_auto_resolve_caps_excess_to_exact_target():
    """
    Verifies that when a buffered refill generates more questions than target_count,
    auto_resolve_batch_and_refill archives the lowest-scoring excess questions to guarantee
    the user receives the exact requested count.
    """
    batch_id = str(uuid.uuid4())
    now_iso = datetime.now(UTC).isoformat()
    target_count = 5

    batch = GenerationBatch(
        id=batch_id,
        section="chem_phys",
        subtopic="Kinetics",
        difficulty="medium",
        passage_mode="independent",
        target_count=target_count,
        actual_count=0,
        total_jobs=1,
        completed_jobs=1,
        failed_jobs=0,
        status="in_progress",
        created_at=now_iso,
    )
    await save_batch(batch)

    # Create 7 distinct questions (2 excess buffer questions)
    scores = [96, 92, 89, 87, 85, 82, 78]
    common_kwargs = {
        "section_label": "Chemical and Physical Foundations of Biological Systems",
        "subtopic": "Kinetics",
        "difficulty": "medium",
        "correct_answer_id": "A",
        "explanation": "Valid test explanation",
    }

    distinct_stems = [
        "What is the rate law for a reaction where doubling reactant A quadruples reaction velocity?",
        "Explain how transition state stabilization lowers activation energy according to Arrhenius theory.",
        "Calculate the half-life of a first-order radioactive decay process with rate constant k = 0.05 s^-1.",
        "How does temperature elevation influence the Maxwell-Boltzmann kinetic energy distribution of gas particles?",
        "A competitive inhibitor is added to an enzymatic pathway. Describe the effect on Km and Vmax.",
        "In zero-order enzyme kinetics, why does increasing substrate concentration fail to increase velocity?",
        "Compare the collision frequency factor between bimolecular elementary gas-phase reactions and unimolecular decays.",
    ]

    for idx, (stem, score) in enumerate(zip(distinct_stems, scores, strict=False)):
        q = Question(
            id=f"cap-q-{idx}-{batch_id[:6]}",
            batch_id=batch_id,
            section="chem_phys",
            question_stem=stem,
            options=[
                {"id": "A", "text": "Option A"},
                {"id": "B", "text": "Option B"},
                {"id": "C", "text": "Option C"},
                {"id": "D", "text": "Option D"},
            ],
            status="ai_validated",
            final_score=score,
            **common_kwargs,
        )
        await save_question(q)

    # Run auto_resolve_batch_and_refill
    res = await auto_resolve_batch_and_refill(batch_id, current_cycle=1, max_cycles=5)
    assert res["resolved"] is True
    assert res["remaining_active"] == target_count  # Strictly capped at 5!

    # Verify questions in database
    active_qs = [
        q
        for q in (await get_questions(batch_id=batch_id))
        if q.status not in ("discarded", "rejected_below_threshold", "error", "failed")
    ]
    assert len(active_qs) == 5

    # Check that the 5 highest scoring questions (96, 92, 89, 87, 85) were kept
    active_scores = {q.final_score for q in active_qs}
    assert active_scores == {96, 92, 89, 87, 85}

    # Check that lowest 2 (82, 78) are discarded
    discarded_qs = [q for q in (await get_questions(batch_id=batch_id)) if q.status == "discarded"]
    assert len(discarded_qs) == 2
    discarded_scores = {q.final_score for q in discarded_qs}
    assert discarded_scores == {82, 78}


async def test_refresh_batch_aggregates_reflects_active_questions():
    """Verifies that refresh_batch_aggregates counts active questions correctly."""
    batch_id = str(uuid.uuid4())
    now_iso = datetime.now(UTC).isoformat()

    batch = GenerationBatch(
        id=batch_id,
        section="bio_biochem",
        subtopic="Metabolism",
        difficulty="medium",
        passage_mode="independent",
        target_count=5,
        actual_count=0,
        total_jobs=1,
        completed_jobs=1,
        failed_jobs=0,
        status="in_progress",
        created_at=now_iso,
    )
    await save_batch(batch)

    job = GenerationJob(
        id=str(uuid.uuid4()),
        batch_id=batch_id,
        job_number=1,
        status="completed",
        target_count=5,
        actual_count=5,
        created_at=now_iso,
    )
    await save_job(job)

    common_kwargs = {
        "section_label": "Biological and Biochemical Foundations of Living Systems",
        "subtopic": "Metabolism",
        "difficulty": "medium",
        "correct_answer_id": "A",
        "explanation": "Valid test explanation",
    }

    # 4 approved questions, 1 discarded question
    for idx in range(4):
        q = Question(
            id=f"agg-q-{idx}-{batch_id[:6]}",
            batch_id=batch_id,
            section="bio_biochem",
            question_stem=f"Metabolism Question Stem #{idx}",
            options=[{"id": "A", "text": "A"}],
            status="ai_validated",
            final_score=90,
            **common_kwargs,
        )
        await save_question(q)

    discarded_q = Question(
        id=f"agg-q-disc-{batch_id[:6]}",
        batch_id=batch_id,
        section="bio_biochem",
        question_stem="Discarded Question Stem",
        options=[{"id": "A", "text": "A"}],
        status="discarded",
        final_score=70,
        **common_kwargs,
    )
    await save_question(discarded_q)

    refreshed = await refresh_batch_aggregates(batch_id)
    assert refreshed is not None
    # actual_count should be exactly 4 (only the active ones)
    assert refreshed.actual_count == 4


async def test_interactive_slot_replenishment_recovers_from_quality_rejection(monkeypatch):
    """
    Verifies that when a question fails quality audit on initial attempt,
    the in-place self-healing loop automatically replenishes the slot
    and completes with exactly the requested 5 questions.
    """
    import json

    import app.workflow.engine as engine_mod
    from app.core.config import config
    from app.workflow.engine import run_workflow_stream

    monkeypatch.setattr(config, "DEEPINFRA_API_KEY", "")
    monkeypatch.delenv("DEEPINFRA_API_KEY", raising=False)

    original_review_loop = engine_mod._run_question_review_loop
    attempt_tracker = {"slot_0_calls": 0}

    async def flaky_review_loop(
        state, idx, total_qty, item_run_id, event_queue, make_event, **kwargs
    ):
        if idx == 0:
            attempt_tracker["slot_0_calls"] += 1
            if attempt_tracker["slot_0_calls"] == 1:
                # First attempt fails review
                return False
        return await original_review_loop(
            state, idx, total_qty, item_run_id, event_queue, make_event, **kwargs
        )

    monkeypatch.setattr(engine_mod, "_run_question_review_loop", flaky_review_loop)

    req = GenerationRequest(
        section=MCATSection.BIO_BIOCHEM,
        subtopic="Cellular Respiration",
        difficulty=Difficulty.MEDIUM,
        questions_to_generate=5,
    )

    events = []
    async for chunk in run_workflow_stream(req):
        line = chunk.strip()
        if line.startswith("data: "):
            events.append(json.loads(line[6:]))

    # Verify that slot 0 retried and recovered
    assert attempt_tracker["slot_0_calls"] >= 2

    # Verify that exactly 5 questions were generated and completed
    complete_evts = [e for e in events if e["event_type"] == "workflow_complete"]
    assert len(complete_evts) == 1
    staged_qs = complete_evts[0]["data"]["questions"]
    assert len(staged_qs) == 5
