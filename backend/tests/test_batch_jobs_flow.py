import pytest
from app.db.session import init_db
from app.main import app
from app.services import cancel_all_background_batches
from httpx import ASGITransport, AsyncClient

pytestmark = pytest.mark.requires_db


@pytest.fixture(autouse=True)
async def ensure_db():
    await init_db()
    yield
    await cancel_all_background_batches()


@pytest.mark.asyncio
async def test_batch_and_jobs_lifecycle(monkeypatch):
    # Mock background execution to test REST/DB lifecycle without spawning live generation workers
    async def mock_execute(b_id, req):
        pass

    monkeypatch.setattr("app.services.batch_runner._execute_batch_workflow", mock_execute)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # 1. Start a 50-question background batch
        req_payload = {
            "section": "chem_phys",
            "subtopic": "Translational Motion",
            "difficulty": "medium",
            "questions_to_generate": 50,
            "passage_mode": "single_passage",
            "passage_required": "Yes",
        }

        resp = await ac.post("/api/batches/start", json=req_payload)
        assert resp.status_code == 202
        data = resp.json()
        assert data["success"] is True
        batch_id = data["batch"]["id"]
        assert data["batch"]["target_count"] == 50
        assert data["batch"]["total_jobs"] == 10
        assert len(data["jobs"]) == 10

        # Verify job numbers are 1 through 10
        job_numbers = [j["job_number"] for j in data["jobs"]]
        assert job_numbers == list(range(1, 11))
        for j in data["jobs"]:
            assert j["target_count"] == 5
            assert j["batch_id"] == batch_id
            assert j["status"] in ("pending", "running")

        # 2. Query batch list
        list_resp = await ac.get("/api/batches")
        assert list_resp.status_code == 200
        list_data = list_resp.json()
        assert "batches" in list_data
        matching = [b for b in list_data["batches"] if b["id"] == batch_id]
        assert len(matching) == 1
        assert matching[0]["total_jobs"] == 10

        # 3. Query single batch detail with jobs
        detail_resp = await ac.get(f"/api/batches/{batch_id}")
        assert detail_resp.status_code == 200
        detail_data = detail_resp.json()
        assert detail_data["batch"]["id"] == batch_id
        assert len(detail_data["jobs"]) == 10
        assert "questions" in detail_data

        # 4. Delete the batch
        del_resp = await ac.delete(f"/api/batches/{batch_id}")
        assert del_resp.status_code == 200

        # 5. Verify batch is gone
        get_again = await ac.get(f"/api/batches/{batch_id}")
        assert get_again.status_code == 404


@pytest.mark.asyncio
async def test_mini_batch_lifecycle(monkeypatch):
    """Verifies that launching a 5-question batch creates exactly 1 job (5 questions target) in background pool."""

    async def mock_execute(b_id, req):
        pass

    monkeypatch.setattr("app.services.batch_runner._execute_batch_workflow", mock_execute)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # 1. Start a 5-question Mini-Batch
        req_payload = {
            "section": "bio_biochem",
            "subtopic": "Enzyme Kinetics",
            "difficulty": "medium",
            "questions_to_generate": 5,
            "passage_mode": "single_passage",
            "passage_required": "Yes",
        }

        resp = await ac.post("/api/batches/start", json=req_payload)
        assert resp.status_code == 202
        data = resp.json()
        assert data["success"] is True
        batch_id = data["batch"]["id"]
        assert data["batch"]["target_count"] == 5
        assert data["batch"]["total_jobs"] == 1
        assert len(data["jobs"]) == 1

        # Verify single job attributes
        single_job = data["jobs"][0]
        assert single_job["job_number"] == 1
        assert single_job["target_count"] == 5
        assert single_job["batch_id"] == batch_id
        assert single_job["status"] in ("pending", "running")

        # 2. Query batch list and verify total_jobs == 1
        list_resp = await ac.get("/api/batches")
        assert list_resp.status_code == 200
        list_data = list_resp.json()
        matching = [b for b in list_data["batches"] if b["id"] == batch_id]
        assert len(matching) == 1
        assert matching[0]["total_jobs"] == 1
        assert matching[0]["target_count"] == 5

        # 3. Query single batch detail with job
        detail_resp = await ac.get(f"/api/batches/{batch_id}")
        assert detail_resp.status_code == 200
        detail_data = detail_resp.json()
        assert detail_data["batch"]["id"] == batch_id
        assert len(detail_data["jobs"]) == 1
        assert detail_data["jobs"][0]["job_number"] == 1

        # 4. Clean up batch
        del_resp = await ac.delete(f"/api/batches/{batch_id}")
        assert del_resp.status_code == 200


@pytest.mark.asyncio
async def test_refill_preserves_job_count_without_adding_sets(monkeypatch):
    """
    Verifies that when a batch has a deficit (e.g. from duplicate resolution),
    refill_batch_deficit replenishes the existing jobs in-place and NEVER creates
    new jobs (e.g. Set #11).
    """
    from app.repositories import get_jobs_by_batch_id, save_batch, save_jobs_bulk, save_question
    from app.schemas import GenerationBatch, GenerationJob, Question
    from app.services import refill_batch_deficit

    batch_id = "test-preserve-10-sets"
    now_iso = "2026-10-30T10:00:00Z"

    # Create 50-question batch with 10 jobs
    batch = GenerationBatch(
        id=batch_id,
        section="chem_phys",
        subtopic="Kinetics",
        difficulty="medium",
        passage_mode="single_passage",
        target_count=50,
        actual_count=49,
        total_jobs=10,
        completed_jobs=9,
        failed_jobs=0,
        status="in_progress",
        created_at=now_iso,
    )
    await save_batch(batch)

    jobs = [
        GenerationJob(
            id=f"job-{idx}",
            batch_id=batch_id,
            job_number=idx,
            target_count=5,
            actual_count=5 if idx != 3 else 4,  # Job 3 lost 1 duplicate question
            status="completed" if idx != 3 else "running",
            created_at=now_iso,
        )
        for idx in range(1, 11)
    ]
    await save_jobs_bulk(jobs)

    # Save 4 questions in Job 3, 5 questions in other jobs
    common_q_kwargs = {
        "section": "chem_phys",
        "section_label": "Chemical and Physical Foundations",
        "subtopic": "Kinetics",
        "difficulty": "medium",
        "options": [{"id": "A", "text": "Opt A"}],
        "correct_answer_id": "A",
        "explanation": "Valid test explanation",
        "status": "ai_validated",
    }
    for job_idx in range(1, 11):
        count_for_job = 4 if job_idx == 3 else 5
        for q_idx in range(count_for_job):
            q = Question(
                id=f"q-job{job_idx}-{q_idx}",
                batch_id=batch_id,
                job_id=f"job-{job_idx}",
                question_stem=f"Question stem {q_idx} for Job {job_idx}",
                **common_q_kwargs,
            )
            await save_question(q)

    # Mock in-set execution so we don't invoke live LLMs
    async def mock_execute_in_set(b_id, req, jobs_to_refill, current_cycle=2, max_cycles=5):
        pass

    monkeypatch.setattr("app.services.batch_runner._execute_in_set_refill", mock_execute_in_set)

    # Refill the deficit of 1
    updated_b, refilled_jobs = await refill_batch_deficit(batch_id, deficit=1)

    assert updated_b is not None
    assert updated_b.total_jobs == 10  # Must strictly remain 10 sets!
    assert len(refilled_jobs) == 1
    assert refilled_jobs[0].id == "job-3"  # Job 3 is targeted in-place!
    assert refilled_jobs[0].job_number == 3

    # Verify database state has strictly 10 jobs and NO Job #11
    db_jobs = await get_jobs_by_batch_id(batch_id)
    assert len(db_jobs) == 10
    job_nums = [j.job_number for j in db_jobs]
    assert job_nums == list(range(1, 11))
    assert 11 not in job_nums


@pytest.mark.asyncio
async def test_reconcile_interrupted_batches_on_startup():
    from app.repositories import (
        get_batch_by_id,
        reconcile_interrupted_batches,
        save_batch,
    )
    from app.schemas import GenerationBatch

    test_b_id = "test-orphan-batch-startup"
    orphan_b = GenerationBatch(
        id=test_b_id,
        section="bio_biochem",
        subtopic="Enzymes",
        difficulty="medium",
        status="in_progress",
        target_count=5,
        actual_count=0,
    )
    await save_batch(orphan_b)

    before = await get_batch_by_id(test_b_id)
    assert before is not None
    assert before.status == "in_progress"

    reconciled_count = await reconcile_interrupted_batches()
    assert reconciled_count >= 1

    after = await get_batch_by_id(test_b_id)
    assert after is not None
    assert after.status == "stopped"
    assert "Server restarted" in (after.error_message or "")
