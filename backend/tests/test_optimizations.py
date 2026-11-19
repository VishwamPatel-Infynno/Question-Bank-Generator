"""Tests for end-to-end optimizations: query pipelining, count_batches, passage pagination and concurrency."""

import uuid

import pytest
from app.main import app
from app.repositories import (
    count_batches,
    count_passages,
    get_passages,
    save_batch,
    save_job,
    save_passage,
    save_question,
)
from app.schemas import (
    BatchStatus,
    GenerationBatch,
    GenerationJob,
    OptionChoice,
    Passage,
    Question,
)
from httpx import ASGITransport, AsyncClient

pytestmark = pytest.mark.requires_db


@pytest.fixture
def anyio_backend():
    return "asyncio"


async def test_count_batches_sql_aggregation():
    """Verify that count_batches performs native SQL aggregation correctly."""
    unique_suffix = uuid.uuid4().hex[:6]
    sec = f"chem_phys_{unique_suffix}"

    count_before = await count_batches(section=sec)
    assert count_before == 0

    batch1 = GenerationBatch(
        id=f"batch-opt-1-{unique_suffix}",
        section=sec,
        subtopic="Thermodynamics",
        difficulty="medium",
        passage_mode="independent",
        target_count=5,
        status=BatchStatus.IN_PROGRESS,
    )
    batch2 = GenerationBatch(
        id=f"batch-opt-2-{unique_suffix}",
        section=sec,
        subtopic="Electrochemistry",
        difficulty="hard",
        passage_mode="single_passage",
        target_count=50,
        status=BatchStatus.COMPLETED,
    )
    await save_batch(batch1)
    await save_batch(batch2)

    total_sec = await count_batches(section=sec)
    assert total_sec == 2

    in_progress_count = await count_batches(section=sec, status=BatchStatus.IN_PROGRESS)
    assert in_progress_count == 1

    completed_count = await count_batches(section=sec, status=BatchStatus.COMPLETED)
    assert completed_count == 1


async def test_passage_pagination_and_counting():
    """Verify that get_passages respects limit and offset, and count_passages aggregates correctly."""
    unique_suffix = uuid.uuid4().hex[:6]
    sec = f"cars_{unique_suffix}"

    p1 = Passage(
        id=f"pass-1-{unique_suffix}",
        title="Passage One",
        text="Sample humanities text on epistemic modesty and scientific revolutions.",
        section=sec,
        subtopic="Philosophy of Science",
    )
    p2 = Passage(
        id=f"pass-2-{unique_suffix}",
        title="Passage Two",
        text="Sample text on the evolution of 19th century literary realism.",
        section=sec,
        subtopic="Literary Criticism",
    )
    p3 = Passage(
        id=f"pass-3-{unique_suffix}",
        title="Passage Three",
        text="Sample text on urban sociology and architectural democracy.",
        section=sec,
        subtopic="Sociology",
    )
    await save_passage(p1)
    await save_passage(p2)
    await save_passage(p3)

    count_all = await count_passages(section=sec)
    assert count_all == 3

    # Limit = 2
    p_limit2 = await get_passages(section=sec, limit=2, offset=0)
    assert len(p_limit2) == 2

    # Offset = 2, Limit = 2
    p_offset2 = await get_passages(section=sec, limit=2, offset=2)
    assert len(p_offset2) == 1

    # Search filter count
    count_search = await count_passages(section=sec, search="epistemic")
    assert count_search == 1


async def test_pipelined_list_questions_endpoint():
    """Verify that the GET /api/questions endpoint correctly returns pipelined results."""
    unique_suffix = uuid.uuid4().hex[:6]
    sec = f"bio_biochem_{unique_suffix}"

    q1 = Question(
        id=f"q-piped-1-{unique_suffix}",
        section=sec,
        section_label="Biological Foundations",
        subtopic="Molecular Genetics",
        difficulty="medium",
        question_stem="Which enzyme catalyzes the unwinding of double-stranded DNA during replication?",
        options=[
            OptionChoice(id="A", text="DNA Helicase"),
            OptionChoice(id="B", text="DNA Topoisomerase"),
            OptionChoice(id="C", text="DNA Ligase"),
            OptionChoice(id="D", text="DNA Polymerase III"),
        ],
        correct_answer_id="A",
        explanation="DNA helicase disrupts hydrogen bonds between complementary base pairs to unwind the helix.",
        final_score=94,
        status="in_bank",
    )
    await save_question(q1)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get(f"/api/questions?section={sec}&status=in_bank")
        assert resp.status_code == 200
        data = resp.json()
        assert "questions" in data
        assert "total_count" in data
        assert "bank_total_count" in data
        assert data["total_count"] >= 1
        assert len(data["questions"]) >= 1
        assert data["questions"][0]["id"] == q1.id


async def test_pipelined_list_batches_endpoint():
    """Verify that GET /api/batches uses concurrent count_batches seamlessly."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/batches?limit=10")
        assert resp.status_code == 200
        data = resp.json()
        assert "batches" in data
        assert "active_running_batches" in data
        assert "concurrency_metrics" in data
        assert isinstance(data["active_running_batches"], int)


async def test_pipelined_passages_endpoints():
    """Verify GET /api/passages with limit/offset and GET /api/passages/{id} concurrent fetch."""
    unique_suffix = uuid.uuid4().hex[:6]
    sec = f"psyc_soc_{unique_suffix}"
    passage_id = f"passage-concurrent-{unique_suffix}"

    p = Passage(
        id=passage_id,
        title="Social Identity Theory",
        text="A study investigating in-group favoritism and out-group derogation in minimal group paradigms.",
        section=sec,
        subtopic="Social Psychology",
    )
    await save_passage(p)

    q = Question(
        id=f"q-linked-{unique_suffix}",
        passage_id=passage_id,
        section=sec,
        section_label="Psychological, Social, and Biological Foundations",
        subtopic="Social Psychology",
        difficulty="medium",
        stimulus_text=p.text,
        question_stem="According to the passage, what process accounts for in-group favoritism in minimal group experiments?",
        options=[
            OptionChoice(id="A", text="Social categorization and self-esteem enhancement"),
            OptionChoice(id="B", text="Realistic conflict over scarce material resources"),
            OptionChoice(id="C", text="Evolutionary altruism toward genetic kin"),
            OptionChoice(id="D", text="Cognitive dissonance reduction"),
        ],
        correct_answer_id="A",
        explanation="Tajfel's social identity theory posits that mere categorization motivates positive in-group distinctiveness to bolster self-esteem.",
        final_score=92,
        status="in_bank",
    )
    await save_question(q)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Test paginated list
        resp = await client.get(f"/api/passages?section={sec}&limit=5&offset=0")
        assert resp.status_code == 200
        data = resp.json()
        assert "passages" in data
        assert "total_count" in data
        assert data["total_count"] >= 1
        assert any(x["id"] == passage_id for x in data["passages"])

        # Test concurrent single passage + questions retrieval
        detail_resp = await client.get(f"/api/passages/{passage_id}")
        assert detail_resp.status_code == 200
        detail_data = detail_resp.json()
        assert "passage" in detail_data
        assert "questions" in detail_data
        assert detail_data["passage"]["id"] == passage_id
        assert len(detail_data["questions"]) >= 1
        assert detail_data["questions"][0]["id"] == q.id


async def test_batch_detail_and_duplicate_clusters_pipelining():
    """Verify concurrent pipelining in GET /api/batches/{id} and duplicate-clusters."""
    unique_suffix = uuid.uuid4().hex[:6]
    batch_id = f"batch-pipe-{unique_suffix}"
    job_id = f"job-pipe-{unique_suffix}"
    sec = f"bio_biochem_{unique_suffix}"

    batch = GenerationBatch(
        id=batch_id,
        section=sec,
        subtopic="Molecular Genetics",
        difficulty="medium",
        passage_mode="independent",
        target_count=5,
        status=BatchStatus.IN_PROGRESS,
    )
    await save_batch(batch)

    job = GenerationJob(
        id=job_id,
        batch_id=batch_id,
        job_number=1,
        status="in_progress",
        target_count=5,
        actual_count=0,
    )
    await save_job(job)

    q1 = Question(
        id=f"q-pipe-1-{unique_suffix}",
        section=sec,
        section_label="Biological Foundations",
        subtopic="Molecular Genetics",
        difficulty="medium",
        batch_id=batch_id,
        job_id=job_id,
        question_stem="What enzyme unwinds the double helix during DNA replication in prokaryotes?",
        options=[
            OptionChoice(id="A", text="DNA Helicase (DnaB)"),
            OptionChoice(id="B", text="DNA Topoisomerase II (DNA Gyrase)"),
            OptionChoice(id="C", text="DNA Polymerase III"),
            OptionChoice(id="D", text="Primase (DnaG)"),
        ],
        correct_answer_id="A",
        explanation="DnaB helicase unwinds the double-stranded DNA at the replication fork.",
        final_score=94,
        status="in_bank",
    )
    q2 = Question(
        id=f"q-pipe-2-{unique_suffix}",
        section=sec,
        section_label="Biological Foundations",
        subtopic="Molecular Genetics",
        difficulty="medium",
        batch_id=batch_id,
        job_id=job_id,
        question_stem="What enzyme relieves torsional strain ahead of the replication fork?",
        options=[
            OptionChoice(id="A", text="DNA Gyrase (Topoisomerase II)"),
            OptionChoice(id="B", text="DNA Ligase"),
            OptionChoice(id="C", text="Single-Stranded Binding Protein"),
            OptionChoice(id="D", text="Telomerase"),
        ],
        correct_answer_id="A",
        explanation="DNA gyrase introduces negative supercoils to relieve strain ahead of the fork.",
        final_score=91,
        status="in_bank",
    )
    await save_question(q1)
    await save_question(q2)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Test concurrent batch detail retrieval
        batch_resp = await client.get(f"/api/batches/{batch_id}")
        assert batch_resp.status_code == 200
        batch_data = batch_resp.json()
        assert "batch" in batch_data
        assert batch_data["batch"]["id"] == batch_id
        assert "jobs" in batch_data
        assert len(batch_data["jobs"]) == 1
        assert batch_data["jobs"][0]["id"] == job_id
        assert batch_data["jobs"][0]["actual_count"] == 2
        assert "questions" in batch_data
        assert len(batch_data["questions"]) == 2

        # Test concurrent batch duplicate clusters retrieval
        cluster_resp = await client.get(f"/api/batches/{batch_id}/duplicate-clusters")
        assert cluster_resp.status_code == 200
        cluster_data = cluster_resp.json()
        assert cluster_data["batch_id"] == batch_id
        assert cluster_data["total_active_questions"] == 2
        assert "clusters" in cluster_data
