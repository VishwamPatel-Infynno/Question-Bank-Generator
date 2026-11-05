"""Duplicate detection, passage lifecycle, CORS and health endpoints."""

import uuid

import pytest
from app.core.config import config
from app.db.session import init_db
from app.repositories import (
    delete_question,
    save_question,
)
from app.schemas import (
    DuplicateCheckRequest,
    OptionChoice,
    Question,
)

pytestmark = pytest.mark.requires_db


@pytest.mark.asyncio
async def test_deduplication_and_override_api():
    from app.api.v1.questions import (
        check_question_duplicate_endpoint,
        override_question_duplicate_endpoint,
    )
    from app.schemas import DuplicateInfo

    await init_db()

    # 1. Seed original question
    orig_id = f"test-orig-{uuid.uuid4().hex[:8]}"
    orig_q = Question(
        id=orig_id,
        section="bio_biochem",
        section_label="Biological and Biochemical Foundations",
        subtopic="Enzyme Kinetics",
        difficulty="medium",
        stimulus_text="",
        question_stem="How does an uncompetitive inhibitor affect the apparent Km and Vmax of an enzyme?",
        options=[
            OptionChoice(id="A", text="Decreases apparent Km and decreases Vmax"),
            OptionChoice(id="B", text="Increases apparent Km and decreases Vmax"),
            OptionChoice(id="C", text="Increases apparent Km and increases Vmax"),
            OptionChoice(id="D", text="Leaves apparent Km unchanged"),
        ],
        correct_answer_id="A",
        explanation="Uncompetitive inhibitors bind to the enzyme-substrate complex, decreasing both Km and Vmax in equal ratio.",
        final_score=95,
        status="in_bank",
    )
    await save_question(orig_q)

    # 2. Test check_question_duplicate_endpoint with duplicate payload
    dup_payload = {
        "section": "bio_biochem",
        "subtopic": "Enzyme Kinetics",
        "question_stem": "How does an uncompetitive inhibitor alter the apparent Km and Vmax of an enzyme?",
        "options": [
            {"id": "A", "text": "Decreases apparent Km and decreases Vmax"},
            {"id": "B", "text": "Increases apparent Km and decreases Vmax"},
            {"id": "C", "text": "Increases apparent Km and increases Vmax"},
            {"id": "D", "text": "Leaves apparent Km unchanged"},
        ],
    }
    check_res = await check_question_duplicate_endpoint(DuplicateCheckRequest(**dup_payload))
    assert check_res["success"] is True
    dup_info = check_res["duplicate_check"]
    assert dup_info["is_duplicate"] is True
    assert dup_info["similarity_score"] >= 0.80
    assert dup_info["matched_question_id"] == orig_id

    # 3. Test saving a duplicate candidate and overriding it
    cand_id = f"test-cand-{uuid.uuid4().hex[:8]}"
    cand_q = Question(
        id=cand_id,
        section="bio_biochem",
        section_label="Biological and Biochemical Foundations",
        subtopic="Enzyme Kinetics",
        difficulty="medium",
        stimulus_text="",
        question_stem="How does an uncompetitive inhibitor alter the apparent Km and Vmax of an enzyme?",
        options=orig_q.options,
        correct_answer_id="A",
        explanation=orig_q.explanation,
        final_score=93,
        status="ai_validated",
        duplicate_info=DuplicateInfo(
            is_duplicate=True,
            similarity_score=dup_info["similarity_score"],
            matched_question_id=orig_id,
            matched_question_stem=orig_q.question_stem,
            match_reason="Conceptual collision",
        ),
        is_duplicate_override=False,
    )
    await save_question(cand_q)

    # 4. Invoke override endpoint
    override_res = await override_question_duplicate_endpoint(cand_id)
    assert override_res["success"] is True
    updated = override_res["question"]
    assert updated["is_duplicate_override"] is True
    assert updated["duplicate_info"]["is_overridden"] is True
    assert updated["status"] == "in_bank"

    # Cleanup
    await delete_question(orig_id)
    await delete_question(cand_id)


@pytest.mark.asyncio
async def test_batch_duplicate_clusters_and_resolve_endpoints():
    from app.api.v1.batches import (
        ResolveDuplicatesRequest,
        get_batch_duplicate_clusters,
        resolve_batch_duplicates,
    )
    from app.repositories import delete_batch, save_batch
    from app.schemas import GenerationBatch

    b_id = f"test-b-{uuid.uuid4().hex[:8]}"
    batch = GenerationBatch(
        id=b_id,
        section="chem_phys",
        difficulty="medium",
        subtopic="Test Topic",
        passage_mode="independent",
        target_count=50,
        status="completed",
    )
    await save_batch(batch)

    # Create 3 questions: 2 duplicates + 1 unique
    opts = [OptionChoice(id="A", text="Test")]
    q1 = Question(
        id=f"q1-{uuid.uuid4().hex[:6]}",
        batch_id=b_id,
        section="chem_phys",
        section_label="Chemical and Physical Foundations",
        difficulty="medium",
        subtopic="Test Topic",
        stimulus_text="",
        explanation="Test explanation",
        question_stem="What is the nuclear charge of a proton in the nucleus?",
        options=opts,
        correct_answer_id="A",
        final_score=97,
        status="batch_only",
    )
    q2 = Question(
        id=f"q2-{uuid.uuid4().hex[:6]}",
        batch_id=b_id,
        section="chem_phys",
        section_label="Chemical and Physical Foundations",
        difficulty="medium",
        subtopic="Test Topic",
        stimulus_text="",
        explanation="Test explanation",
        question_stem="What is the nuclear charge of a proton in an atomic nucleus?",
        options=opts,
        correct_answer_id="A",
        final_score=91,
        status="batch_only",
    )
    q3 = Question(
        id=f"q3-{uuid.uuid4().hex[:6]}",
        batch_id=b_id,
        section="chem_phys",
        section_label="Chemical and Physical Foundations",
        difficulty="medium",
        subtopic="Test Topic",
        stimulus_text="",
        explanation="Test explanation",
        question_stem="How does wavelength relate to frequency for light in a vacuum?",
        options=opts,
        correct_answer_id="A",
        final_score=95,
        status="batch_only",
    )
    await save_question(q1)
    await save_question(q2)
    await save_question(q3)

    # 1. Cluster endpoint
    cluster_res = await get_batch_duplicate_clusters(b_id, threshold=0.75)
    assert cluster_res["batch_id"] == b_id
    assert cluster_res["duplicate_clusters_count"] == 1
    assert cluster_res["total_duplicate_questions"] == 1
    assert cluster_res["unique_questions_count"] == 2

    # 2. Resolve duplicates
    resolve_res = await resolve_batch_duplicates(b_id, ResolveDuplicatesRequest(action="archive"))
    assert resolve_res["success"] is True
    assert resolve_res["archived_count"] == 1
    assert resolve_res["remaining_active_questions"] == 2

    # Cleanup
    await delete_batch(b_id)


@pytest.mark.asyncio
async def test_passage_lifecycle_and_restore_api(client):
    """Verify passage creation, retrieval, soft-deletion, and restoration via REST API endpoints."""
    from app.repositories import get_passage_by_id

    pid = f"pas-{uuid.uuid4().hex[:8]}"
    payload = {
        "id": pid,
        "title": "Passage Restoration Test",
        "text": "This is a detailed passage text for evaluating the restore API endpoint.",
        "section": "cars",
        "subtopic": "Philosophy",
    }

    # 1. Create passage
    create_res = await client.post("/api/passages", json=payload)
    assert create_res.status_code == 200
    assert create_res.json()["success"] is True

    # 2. Get single passage
    get_res = await client.get(f"/api/passages/{pid}")
    assert get_res.status_code == 200
    assert get_res.json()["passage"]["id"] == pid

    # 3. Soft-delete passage
    del_res = await client.delete(f"/api/passages/{pid}")
    assert del_res.status_code == 200
    assert del_res.json()["success"] is True

    # 4. Confirm deleted passage is hidden from standard lookup
    p_deleted = await get_passage_by_id(pid, include_deleted=False)
    assert p_deleted is None
    p_with_deleted = await get_passage_by_id(pid, include_deleted=True)
    assert p_with_deleted is not None
    assert p_with_deleted.is_deleted is True

    # 5. Restore passage via new restore endpoint
    restore_res = await client.post(f"/api/passages/{pid}/restore")
    assert restore_res.status_code == 200
    assert restore_res.json()["success"] is True
    assert restore_res.json()["restored_id"] == pid

    # 6. Confirm passage is active again
    p_restored = await get_passage_by_id(pid, include_deleted=False)
    assert p_restored is not None
    assert p_restored.is_deleted is False

    # 7. Non-existent passage restore returns 404
    non_existent = await client.post(f"/api/passages/non-existent-{uuid.uuid4().hex[:6]}/restore")
    assert non_existent.status_code == 404


@pytest.mark.asyncio
async def test_cors_patch_allowed(client):
    """Verify that CORS preflight permits PATCH requests in Access-Control-Allow-Methods."""
    headers = {
        "Origin": "http://localhost:5173",
        "Access-Control-Request-Method": "PATCH",
        "Access-Control-Request-Headers": "content-type",
    }
    response = await client.options("/api/health", headers=headers)
    assert response.status_code == 200
    allow_methods = response.headers.get("access-control-allow-methods", "")
    assert "PATCH" in allow_methods


@pytest.mark.asyncio
async def test_health_admin_key_is_validated_when_configured(client, monkeypatch):

    monkeypatch.setattr(config, "ADMIN_API_KEY", "s3cret")
    masked = (await client.get("/api/health", headers={"x-admin-key": "wrong"})).json()
    assert "default_text_model" not in masked
    full = (await client.get("/api/health", headers={"x-admin-key": "s3cret"})).json()
    assert "default_text_model" in full


@pytest.mark.asyncio
async def test_readiness_probe_reflects_database_state(client, monkeypatch):
    import app.api.v1.health as health_mod

    ok = await client.get("/api/health/ready")
    assert ok.status_code == 200 and ok.json()["status"] == "ready"

    async def down():
        return {"connected": False, "status": "unavailable"}

    monkeypatch.setattr(health_mod, "check_db_health", down)
    bad = await client.get("/api/health/ready")
    assert bad.status_code == 503 and bad.json()["status"] == "not_ready"
    degraded = (await client.get("/api/health")).json()
    assert degraded["status"] == "degraded"
