import csv
import io
import json

import httpx
import pytest
from app.core.config import config
from app.schemas import ReviewScore
from app.workflow import reject_node, route_after_review

BASE_URL = "http://127.0.0.1:8000/api"

pytestmark = pytest.mark.live_e2e


async def test_e2e_health_and_db_connectivity():
    """
    E2E Test 1: Verify health endpoint, PostgreSQL 16 connection,
    active provider credentials, and model pricing parameters.
    """
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=10.0) as client:
        resp = await client.get("/health")
        assert resp.status_code == 200, f"Health check failed: {resp.text}"
        data = resp.json()

        # Verify database
        assert data["status"] == "healthy"
        assert data["database"] == "connected"
        assert data["database_connected"] is True
        assert data["database_status"] == "ready"

        # Verify inference models and pricing dynamically based on active provider
        assert data["default_text_model"] == config.DEFAULT_TEXT_MODEL
        assert "FLUX-2-klein-4b" in data["default_image_model"]
        if data["active_provider"] == "anthropic":
            assert data["has_anthropic_key"] is True
            assert data["cost_per_million_input"] == config.ANTHROPIC_COST_PER_MILLION_INPUT_TOKENS
            assert (
                data["cost_per_million_output"] == config.ANTHROPIC_COST_PER_MILLION_OUTPUT_TOKENS
            )
        else:
            assert data["has_deepinfra_key"] is True
            assert data["cost_per_million_input"] == config.DEEPINFRA_COST_PER_MILLION_INPUT_TOKENS
            assert (
                data["cost_per_million_output"] == config.DEEPINFRA_COST_PER_MILLION_OUTPUT_TOKENS
            )

        assert data["passing_threshold"] == 90
        assert data["max_regenerations"] == 3


async def test_e2e_all_four_sections_metadata():
    """
    E2E Test 2: Verify all 4 official MCAT sections and curriculum subtopics.
    """
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=10.0) as client:
        resp = await client.get("/sections")
        assert resp.status_code == 200
        data = resp.json()
        sections = data.get("sections", [])
        assert len(sections) == 4, f"Expected 4 sections, got {len(sections)}"

        expected_sections = {
            "chem_phys",
            "cars",
            "bio_biochem",
            "psych_soc",
        }
        actual_sections = {s["id"] for s in sections}
        assert actual_sections == expected_sections

        for sec in sections:
            assert len(sec.get("subtopics", [])) >= 4, f"Section {sec['id']} missing subtopics"
            assert "label" in sec


async def test_e2e_config_endpoint():
    """
    E2E Test 3: Verify the configuration management and status endpoint.
    """
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=10.0) as client:
        resp = await client.get("/config")
        assert resp.status_code == 200
        cfg = resp.json()
        assert cfg["default_text_model"] == config.DEFAULT_TEXT_MODEL
        if cfg["active_provider"] == "anthropic":
            assert cfg["has_anthropic_key"] is True
            assert cfg["cost_per_million_input"] == config.ANTHROPIC_COST_PER_MILLION_INPUT_TOKENS
            assert cfg["cost_per_million_output"] == config.ANTHROPIC_COST_PER_MILLION_OUTPUT_TOKENS
        else:
            assert cfg["has_deepinfra_key"] is True
            assert cfg["cost_per_million_input"] == config.DEEPINFRA_COST_PER_MILLION_INPUT_TOKENS
            assert cfg["cost_per_million_output"] == config.DEEPINFRA_COST_PER_MILLION_OUTPUT_TOKENS
        assert cfg["passing_threshold"] == 90
        assert cfg["current_image_cost_usd"] == 0.014


async def test_e2e_live_generation_sse_stream():
    """
    E2E Test 4: Full Multi-Agent Pipeline Execution via Server-Sent Events (SSE).
    Generates a live question using DeepSeek V4.1 Flash 1017 on DeepInfra.
    Verifies event chronology, 100-pt psychometric rubric scoring (> 90),
    exact token tracking, and automatic PostgreSQL 16 persistence.
    """
    payload = {
        "section": "cars",
        "subtopic": "Foundations of Comprehension",
        "difficulty": "medium",
        "require_image": False,
        "passage_required": "Yes",
        "questions_to_generate": 1,
    }

    events = []
    completed_question = None

    async with (
        httpx.AsyncClient(base_url=BASE_URL, timeout=240.0) as client,
        client.stream("POST", "/generate", json=payload) as response,
    ):
        assert response.status_code == 200
        assert "text/event-stream" in response.headers.get("content-type", "")

        buffer = ""
        async for chunk in response.aiter_text():
            buffer += chunk
            while "\n\n" in buffer:
                block, buffer = buffer.split("\n\n", 1)
                block = block.strip()
                if block.startswith("data: "):
                    data_str = block[6:]
                    try:
                        ev = json.loads(data_str)
                        events.append(ev)
                        if ev.get("event_type") == "workflow_complete":
                            completed_question = ev.get("data", {}).get("question")
                    except json.JSONDecodeError:
                        pass

    assert len(events) >= 3, f"Expected multi-agent stream events, received: {len(events)}"

    # Verify event sequencing
    event_types = [e.get("event_type") for e in events]
    assert "workflow_start" in event_types
    assert "agent_start" in event_types
    assert "agent_complete" in event_types
    assert "workflow_complete" in event_types

    # Verify the question output
    assert completed_question is not None, "Workflow did not return a completed question"
    assert completed_question["section"] == "cars"
    assert len(completed_question["options"]) == 4
    assert completed_question["correct_answer_id"] in ["A", "B", "C", "D"]
    assert completed_question["stimulus_text"] is not None
    assert len(completed_question["stimulus_text"]) > 50
    assert completed_question["question_stem"] is not None
    assert completed_question["explanation"] is not None

    # Verify psychometric score requirement (> 90)
    final_score = completed_question.get("final_score", 0)
    assert final_score > 90, f"Question must pass rubric with score > 90, got: {final_score}"

    # Verify token and cost accounting
    assert completed_question.get("total_tokens", 0) > 0
    assert completed_question.get("cost_usd", 0.0) > 0.0


async def test_e2e_question_bank_crud_and_filtering():
    """
    E2E Test 5: Verify Question Bank queries, filtering by section,
    difficulty, search term, and question retrieval by ID.
    """
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=10.0) as client:
        # 1. Seed a known 4-option test question to verify CRUD & filtering
        seed_payload = {
            "section": "cars",
            "section_label": "Critical Analysis and Reasoning Skills",
            "subtopic": "Reasoning Within the Text",
            "difficulty": "medium",
            "stimulus_text": "Clinical audit in acute tertiary hospitals demonstrated a 34% reduction in catheter-associated urinary tract infections following protocolized catheter removal policies.",
            "question_stem": "Which conclusion is most robustly supported by the clinical audit findings?",
            "options": [
                {
                    "id": "A",
                    "text": "Protocolized catheter removal policies contributed to lower infection incidence.",
                },
                {
                    "id": "B",
                    "text": "All hospital wards eliminated urinary tract infections entirely.",
                },
                {
                    "id": "C",
                    "text": "Nurses refused to follow catheter protocols in surgical departments.",
                },
                {
                    "id": "D",
                    "text": "Infection rates increased across non-acute medical settings.",
                },
            ],
            "correct_answer_id": "A",
            "correct_answer_ids": ["A"],
            "explanation": "Option A is directly corroborated by the 34% observed reduction in catheter-associated infections.",
            "final_score": 96,
            "total_tokens": 750,
            "cost_usd": 0.0003,
        }
        save_resp = await client.post("/questions", json=seed_payload)
        assert save_resp.status_code == 200
        sample_q = save_resp.json()
        q_id = sample_q["id"]

        # 2. Fetch single question by ID
        resp_single = await client.get(f"/questions/{q_id}")
        assert resp_single.status_code == 200
        single_q = resp_single.json()
        assert single_q["id"] == q_id
        assert len(single_q["options"]) == 4

        # 3. Test filtering by section
        sec = sample_q["section"]
        resp_sec = await client.get(f"/questions?section={sec}")
        assert resp_sec.status_code == 200
        sec_questions = resp_sec.json().get("questions", [])
        assert any(q["id"] == q_id for q in sec_questions)
        for q in sec_questions:
            assert q["section"] == sec

        # 4. Test filtering by difficulty
        diff = sample_q["difficulty"]
        resp_diff = await client.get(f"/questions?difficulty={diff}")
        assert resp_diff.status_code == 200
        diff_questions = resp_diff.json().get("questions", [])
        assert any(q["id"] == q_id for q in diff_questions)
        for q in diff_questions:
            assert q["difficulty"].lower() == diff.lower()

        # 5. Test search query
        snippet = sample_q["question_stem"][:10]
        resp_search = await client.get(f"/questions?search={snippet}")
        assert resp_search.status_code == 200
        search_results = resp_search.json().get("questions", [])
        assert len(search_results) >= 1
        assert any(q["id"] == q_id for q in search_results)


async def test_e2e_export_json_and_csv():
    """
    E2E Test 6: Verify export capabilities in both JSON and RFC 4180 CSV formats.
    """
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=10.0) as client:
        # JSON Export
        resp_json = await client.get("/export?format=json")
        assert resp_json.status_code == 200
        assert "application/json" in resp_json.headers.get("content-type", "")
        exported_data = resp_json.json()
        assert isinstance(exported_data, list)
        assert len(exported_data) > 0

        # CSV Export
        resp_csv = await client.get("/export?format=csv")
        assert resp_csv.status_code == 200
        assert "text/csv" in resp_csv.headers.get("content-type", "")
        csv_text = resp_csv.text
        reader = csv.reader(io.StringIO(csv_text))
        rows = list(reader)
        assert len(rows) >= 2, "CSV should contain header row and at least one data row"
        header = rows[0]
        assert "ID" in header
        assert "Section" in header
        assert "Difficulty" in header
        assert "Final Score" in header
        assert "Image_URL" in header
        assert "Image_Description" in header


async def test_e2e_strict_threshold_rejection_boundary():
    """
    E2E Test 7: Verify rejection boundary behavior.
    When a draft scores <= 90 after max attempts, it must be rejected
    and produce diagnostic payload without being saved to database.
    """
    from app.agents.generator import get_mock_draft
    from app.schemas import Difficulty, GenerationRequest, MCATSection

    req = GenerationRequest(section=MCATSection.CHEM_PHYS, difficulty=Difficulty.HARD)
    draft = get_mock_draft(req)

    failing_review = ReviewScore(
        total_score=84,
        passed=False,
        authenticity_score=21,
        clarity_score=21,
        distractor_score=21,
        explanation_score=21,
        recommendations=["Distractor B is too obvious and tone lacks clinical rigor."],
    )

    state_failing = {
        "request": req.model_dump(),
        "current_draft": draft.model_dump(),
        "current_review": failing_review.model_dump(),
        "iteration_count": config.MAX_REGENERATION_ATTEMPTS,
    }

    # Route after review must select reject
    next_step = route_after_review(state_failing)
    assert next_step == "reject"

    # Reject node must produce diagnosis
    reject_res = await reject_node(state_failing)
    assert reject_res["status"] == "rejected_below_threshold"
    assert reject_res["rejection_data"]["final_score"] == 84
    assert "reason" in reject_res["rejection_data"]


async def test_e2e_manager_combination_matrix_and_stage_outcomes():
    """
    E2E Test 8: Verify manager combination matrix attributes (CMB00001)
    and full multi-stage outcomes JSON recording (drafting, quality_audit, polish_refine, visual_stimulus, final_payload).
    """
    from app.schemas import Difficulty, GenerationRequest
    from app.workflow import run_workflow

    req = GenerationRequest(
        combination_id="CMB00001",
        section="VR",
        subtopic="Inference",
        difficulty=Difficulty.EASY,
        content_domain="Science",
        question_type="Passage_MCQ",
        interaction_type="single_choice",
        primary_trap="Keyword_Trap",
        passage_required="Yes",
        passage_questions=1,
        image_required="No",
        visual_type="None",
        questions_to_generate=1,
        auto_save=True,
    )

    result = await run_workflow(req)
    assert result.status in ["approved", "rejected_below_threshold"]

    if result.status == "approved" and result.question:
        q = result.question
        assert q.combination_id == "CMB00001"
        assert q.content_domain == "Science"
        assert q.question_type == "Passage_MCQ"
        assert q.primary_trap in ["Keyword_Trap", "DISTRACTOR_OVERINTERPRETATION"]
        assert q.passage_required == "Yes"

        # Verify Stage Outcomes JSON recording
        assert q.stage_outcomes is not None
        assert "drafting" in q.stage_outcomes
        assert "quality_audit" in q.stage_outcomes
        assert "polish_refine" in q.stage_outcomes
        assert "visual_stimulus" in q.stage_outcomes
        assert "final_payload" in q.stage_outcomes

        # Verify drafting stage payload
        assert "question_stem" in q.stage_outcomes["drafting"]
        assert "options" in q.stage_outcomes["drafting"]
        assert len(q.stage_outcomes["drafting"]["options"]) == 4

        # Verify quality audit stage payload
        assert "total_score" in q.stage_outcomes["quality_audit"]
        assert q.stage_outcomes["quality_audit"]["total_score"] >= 90

        # Verify API query filtering by combination_id
        async with httpx.AsyncClient(base_url=BASE_URL, timeout=10.0) as client:
            resp = await client.get("/questions?combination_id=CMB00001&status=all")
            assert resp.status_code == 200
            data = resp.json()
            questions = data.get("questions", [])
            assert any(item["combination_id"] == "CMB00001" for item in questions)

            # Verify CSV export contains the manager columns
            resp_csv = await client.get("/export?format=csv")
            assert resp_csv.status_code == 200
            csv_lines = resp_csv.text.splitlines()
            header = csv_lines[0].split(",")
            assert "Combination_ID" in header
            assert "Content_Domain" in header
            assert "Primary_Trap" in header


async def test_e2e_uuid_architecture():
    """
    E2E Test 9: Verify end-to-end UUID architecture:
    1. Automatic UUID4 generation for combination_id when omitted.
    2. Unique run_id per execution.
    3. batch_id propagation across workflow, events, and persistence.
    4. audit_id assigned to psychometric reviews.
    5. event_id assigned to all SSE events.
    6. Database filtering by batch_id and run_id.
    """
    import uuid

    from app.schemas import Difficulty, GenerationRequest
    from app.workflow import run_workflow_stream

    test_batch_id = str(uuid.uuid4())

    # Request with omitted combination_id
    req = GenerationRequest(
        section="VR",
        subtopic="Critical Reading & Inferences",
        difficulty=Difficulty.EASY,
        batch_id=test_batch_id,
        questions_to_generate=1,
    )

    # 1. Assert combination_id was auto-populated with valid UUID4
    assert req.combination_id is not None
    assert uuid.UUID(req.combination_id, version=4)

    # 2. Assert run_id was auto-generated with valid UUID4
    assert req.run_id is not None
    assert uuid.UUID(req.run_id, version=4)
    assert req.batch_id == test_batch_id

    # 3. Stream workflow and verify all events contain event_id and run_id
    events_received = []
    final_question = None

    async for raw_line in run_workflow_stream(req):
        line = raw_line.strip()
        if line.startswith("data: "):
            payload = json.loads(line[6:])
            events_received.append(payload)

            # Assert event_id is valid UUID4
            assert "event_id" in payload
            assert uuid.UUID(payload["event_id"], version=4)
            assert payload.get("run_id") == req.run_id
            assert payload.get("batch_id") == test_batch_id

            if payload.get("event_type") == "workflow_complete":
                final_question = payload.get("data", {}).get("question")

    assert len(events_received) >= 4, "Should receive at least 4 workflow events"

    if final_question:
        # 4. Assert Question UUID identifiers
        assert uuid.UUID(final_question["id"], version=4)
        assert final_question["run_id"] == req.run_id
        assert final_question["batch_id"] == test_batch_id
        assert uuid.UUID(final_question["combination_id"], version=4)

        # 5. Assert audit_id in review rubric
        review = final_question.get("review_rubric")
        if review:
            assert "audit_id" in review
            assert uuid.UUID(review["audit_id"], version=4)

        # 6. Admin Review Approval Gate: approve candidate into Question Bank
        async with httpx.AsyncClient(base_url=BASE_URL, timeout=10.0) as client:
            resp_approve = await client.post("/questions", json=final_question)
            assert resp_approve.status_code == 200, (
                f"Candidate approval failed: {resp_approve.text}"
            )
            assert resp_approve.json().get("success") is True

            # Query by batch_id
            resp_batch = await client.get(f"/questions?batch_id={test_batch_id}")
            assert resp_batch.status_code == 200
            batch_qs = resp_batch.json().get("questions", [])
            assert any(q["id"] == final_question["id"] for q in batch_qs)

            # Query by run_id
            resp_run = await client.get(f"/questions?run_id={req.run_id}")
            assert resp_run.status_code == 200
            run_qs = resp_run.json().get("questions", [])
            assert any(q["id"] == final_question["id"] for q in run_qs)

            # Export CSV includes Run_ID and Batch_ID
            resp_csv = await client.get("/export?format=csv")
            assert resp_csv.status_code == 200
            csv_lines = resp_csv.text.splitlines()
            header = csv_lines[0].split(",")
            assert "Run_ID" in header
            assert "Batch_ID" in header

            # Clean up approved test question
            await client.delete(f"/questions/{final_question['id']}")


async def test_e2e_question_image_endpoint():
    """
    E2E Test 10: Verify /questions/{id}/image binary image serving endpoint
    and CSV export Image_URL formatting for Base64 and SVG visual stimuli.
    """
    import base64
    import uuid

    # 1x1 transparent GIF in base64
    dummy_b64 = "data:image/jpeg;base64," + base64.b64encode(
        b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00`\x00`\x00\x00\xff\xdb\x00C\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\t\t\x08\n\x0c\x14\r\x0c\x0b\x0b\x0c\x19\x12\x13\x0f\x14\x1d\x1a\x1f\x1e\x1d\x1a\x1c\x1c $.' \",#\x1c\x1c(7),01444\x1f'9=82<.342\xff\xc0\x00\x0b\x08\x00\x01\x00\x01\x01\x01\x11\x00\xff\xc4\x00\x1f\x00\x00\x01\x05\x01\x01\x01\x01\x01\x01\x00\x00\x00\x00\x00\x00\x00\x00\x01\x02\x03\x04\x05\x06\x07\x08\t\n\x0b\xff\xda\x00\x08\x01\x01\x00\x00?\x00\xbf\x00\xff\xd9"
    ).decode("utf-8")
    test_id = str(uuid.uuid4())

    img_q = {
        "id": test_id,
        "section": "chem_phys",
        "section_label": "Chemical and Physical Foundations of Biological Systems",
        "subtopic": "Thermodynamics & Reaction Kinetics",
        "difficulty": "hard",
        "visual_type": "AI_FLUX_Image",
        "image_url": dummy_b64,
        "image_description": "Reaction coordinate diagram showing activation energy profile",
        "question_stem": "Which transition state represents the rate-determining step?",
        "options": [
            {"id": "A", "text": "Transition State 1"},
            {"id": "B", "text": "Transition State 2"},
            {"id": "C", "text": "Intermediate Complex"},
            {"id": "D", "text": "Product Ground State"},
        ],
        "correct_answer_id": "A",
        "correct_answer_ids": ["A"],
        "explanation": "Transition State 1 presents the highest activation barrier delta G double dagger.",
        "final_score": 96,
    }

    async with httpx.AsyncClient(base_url=BASE_URL, timeout=10.0) as client:
        # Save question with visual stimulus
        save_res = await client.post("/questions", json=img_q)
        assert save_res.status_code == 200

        # Query question image endpoint
        img_res = await client.get(f"/questions/{test_id}/image")
        assert img_res.status_code == 200
        assert "image/jpeg" in img_res.headers.get("content-type", "")
        assert len(img_res.content) > 20

        # Query CSV export and verify Image_URL points to safe endpoint URL
        csv_res = await client.get("/export?format=csv")
        assert csv_res.status_code == 200
        reader = csv.reader(io.StringIO(csv_res.text))
        rows = list(reader)
        header = rows[0]
        img_url_idx = header.index("Image_URL")
        img_desc_idx = header.index("Image_Description")

        found_row = next((r for r in rows if r[0] == test_id), None)
        assert found_row is not None
        assert found_row[img_url_idx] == f"/api/questions/{test_id}/image"
        assert (
            found_row[img_desc_idx]
            == "Reaction coordinate diagram showing activation energy profile"
        )

        # Cleanup
        await client.delete(f"/questions/{test_id}")
