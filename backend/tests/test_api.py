import json
import uuid

import pytest
from app.agents.generator import get_mock_draft
from app.api.v1.questions import (
    purge_questions_batch_endpoint,
    purge_single_question,
)
from app.core.config import config
from app.db.session import init_db
from app.repositories.question_repository import (
    delete_question,
    get_questions,
    save_question,
)
from app.schemas import (
    Difficulty,
    GenerationRequest,
    MCATSection,
    OptionChoice,
    Question,
)
from app.workflow.graph import (
    finalize_node,
    run_workflow_stream,
)

pytestmark = pytest.mark.requires_db


@pytest.mark.asyncio
async def test_database_crud():
    await init_db()
    opts = [
        OptionChoice(id="A", text="Option A"),
        OptionChoice(id="B", text="Option B"),
        OptionChoice(id="C", text="Option C"),
        OptionChoice(id="D", text="Option D"),
    ]
    test_q = Question(
        section=MCATSection.PSYCH_SOC.value,
        section_label="Psychological, Social, and Biological Foundations of Behavior",
        subtopic="Cognitive Psychology & Behavioral Decision Making",
        difficulty="medium",
        stimulus_text="Test stimulus",
        question_stem="Test question stem?",
        options=opts,
        correct_answer_id="C",
        explanation="Step-by-step test explanation",
        final_score=94,
        iteration_count=2,
    )

    saved = await save_question(test_q)
    assert saved.id == test_q.id

    retrieved = await get_questions(section=MCATSection.PSYCH_SOC.value)
    assert any(q.id == test_q.id for q in retrieved)

    deleted = await delete_question(test_q.id)
    assert deleted is True


@pytest.mark.asyncio
async def test_admin_approval_and_persistence_endpoints():
    from app.api.v1.questions import (
        BatchDeleteRequest,
        approve_and_save_question,
        batch_approve_and_save_questions,
        remove_questions_batch,
    )
    from app.repositories.question_repository import (
        delete_questions_batch,
        get_question_by_id,
    )

    # 1. Test finalize_node with auto_save=False (Default for Admin Review)
    req = GenerationRequest(
        section=MCATSection.PSYCH_SOC, difficulty=Difficulty.MEDIUM, auto_save=False
    )
    draft_data = {
        "stimulus_text": "Clinical patient trial data on neuroprotective agents.",
        "question_stem": "Which trial finding supports the clinical efficacy?",
        "options": [
            {"id": "A", "text": "Significant reduction in infarct volume."},
            {"id": "B", "text": "Adverse events reported in high doses."},
            {"id": "C", "text": "Participant attrition rate was 12%."},
            {"id": "D", "text": "No statistical difference noted."},
        ],
        "correct_answer_id": "A",
        "explanation": "Option A directly demonstrates efficacy.",
    }
    review_data = {
        "authenticity_score": 24,
        "clarity_score": 24,
        "distractor_score": 24,
        "explanation_score": 24,
        "total_score": 96,
        "strengths": ["Clear stimulus"],
        "weaknesses": [],
        "recommendations": [],
    }
    state = {
        "request": req.model_dump(),
        "current_draft": draft_data,
        "current_review": review_data,
        "iteration_count": 1,
        "iterations_history": [],
        "total_tokens": 1200,
        "total_cost_usd": 0.00045,
        "stage_outcomes": {},
    }
    fin_res = await finalize_node(state)
    candidate = fin_res["final_question"]
    cand_id = candidate["id"]

    # Verify candidate is NOT automatically saved in database
    db_check = await get_question_by_id(cand_id)
    assert db_check is None, "Candidate question should NOT be saved in DB before Admin approval!"

    # 2. Test Admin Approval: POST /questions
    q_schema = Question(**candidate)
    approve_res = await approve_and_save_question(q_schema)
    assert approve_res["success"] is True
    assert approve_res["question"]["id"] == cand_id

    # Verify candidate is now saved in DB
    db_saved = await get_question_by_id(cand_id)
    assert db_saved is not None
    assert db_saved.id == cand_id
    assert db_saved.final_score == 96

    # 3. Test Batch Approval: POST /questions/batch
    batch_q1 = Question(
        id=str(uuid.uuid4()),
        section=MCATSection.PSYCH_SOC.value,
        section_label="Psychological, Social, and Biological Foundations of Behavior",
        subtopic="Cognitive Bias & Heuristics",
        difficulty="Medium",
        stimulus_text="All doctors are certified.",
        question_stem="Is Dr. Smith certified?",
        options=[
            OptionChoice(id="A", text="Yes"),
            OptionChoice(id="B", text="No"),
            OptionChoice(id="C", text="Cannot Tell"),
            OptionChoice(id="D", text="Insufficient"),
        ],
        correct_answer_id="A",
        explanation="Yes by syllogism.",
        final_score=94,
    )
    batch_q2 = Question(
        id=str(uuid.uuid4()),
        section=MCATSection.CHEM_PHYS.value,
        section_label="Chemical and Physical Foundations of Biological Systems",
        subtopic="Thermodynamics & Kinetics",
        difficulty="Easy",
        stimulus_text="Dosage is 10mg/kg.",
        question_stem="What is the dose for 70kg?",
        options=[
            OptionChoice(id="A", text="700mg"),
            OptionChoice(id="B", text="500mg"),
            OptionChoice(id="C", text="100mg"),
            OptionChoice(id="D", text="350mg"),
        ],
        correct_answer_id="A",
        explanation="70 * 10 = 700mg.",
        final_score=95,
    )

    batch_res = await batch_approve_and_save_questions([batch_q1, batch_q2])
    assert batch_res["success"] is True
    assert batch_res["saved_count"] == 2

    # Clean up single test question
    del_single = await delete_question(cand_id)
    assert del_single is True
    assert await get_question_by_id(cand_id) is None

    # Test atomic batch deletion endpoint
    del_batch_res = await remove_questions_batch(BatchDeleteRequest(ids=[batch_q1.id, batch_q2.id]))
    assert del_batch_res["success"] is True
    assert del_batch_res["deleted_count"] == 2
    assert await get_question_by_id(batch_q1.id) is None
    assert await get_question_by_id(batch_q2.id) is None
    assert await delete_questions_batch([]) == 0

    # Test permanent purge endpoints
    purge_q_id = str(uuid.uuid4())
    await save_question(
        Question(
            id=purge_q_id,
            section="biological_biochemical",
            section_label="Biological and Biochemical Foundations of Living Systems",
            subtopic="Enzyme Kinetics",
            difficulty="medium",
            question_stem="Question for permanent purge test?",
            options=[OptionChoice(id="A", text="Opt A")],
            correct_answer_id="A",
            explanation="Test purge rationale",
            final_score=95,
            status="ai_validated",
        )
    )
    assert await get_question_by_id(purge_q_id) is not None
    purge_res = await purge_single_question(purge_q_id)
    assert purge_res["success"] is True
    assert await get_question_by_id(purge_q_id) is None

    # Test purge batch endpoint
    purge_b1 = str(uuid.uuid4())
    await save_question(
        Question(
            id=purge_b1,
            section="biological_biochemical",
            section_label="Biological and Biochemical Foundations of Living Systems",
            subtopic="Enzyme Kinetics",
            difficulty="medium",
            question_stem="Batch question for permanent purge test?",
            options=[OptionChoice(id="A", text="Opt A")],
            correct_answer_id="A",
            explanation="Test purge rationale",
            final_score=95,
            status="ai_validated",
        )
    )
    purge_batch_res = await purge_questions_batch_endpoint(BatchDeleteRequest(ids=[purge_b1]))
    assert purge_batch_res["success"] is True
    assert purge_batch_res["purged_count"] == 1
    assert await get_question_by_id(purge_b1) is None


@pytest.mark.asyncio
async def test_multichoice_and_passage_support():
    from app.repositories.question_repository import get_question_by_id

    # 1. Test multi-choice GenerationRequest with passage and trap
    req = GenerationRequest(
        section=MCATSection.CARS,
        difficulty=Difficulty.HARD,
        interaction_type="multi_choice",
        passage_required="Yes",
        primary_trap="Extreme_Language",
    )
    draft = get_mock_draft(req)

    assert len(draft.options) in (4, 5)
    assert len(draft.correct_answer_ids) >= 1
    assert draft.correct_answer_id is not None
    assert len(draft.stimulus_text) > 100

    # 2. Test Question model creation with multiple keys
    multi_q = Question(
        id=str(uuid.uuid4()),
        section="cars",
        section_label="Critical Analysis and Reasoning Skills (CARS)",
        subtopic="Critical Inference",
        difficulty="Hard",
        interaction_type="multi_choice",
        primary_trap="Extreme_Language",
        passage_required="Yes",
        stimulus_text="A comprehensive 300-word clinical study on pharmacology...",
        question_stem="Which TWO of the following statements are supported by the passage?",
        options=[
            OptionChoice(id="A", text="Statement A is clinically validated."),
            OptionChoice(id="B", text="Statement B is statistically confirmed."),
            OptionChoice(id="C", text="Statement C always occurs in every patient."),
            OptionChoice(id="D", text="Statement D is never applicable."),
            OptionChoice(id="E", text="Statement E represents a partial correlation."),
        ],
        correct_answer_id="A, B",
        correct_answer_ids=["A", "B"],
        explanation="Statements A and B are definitively supported. C and D commit extreme language fallacies.",
        final_score=96,
    )
    assert multi_q.correct_answer_ids == ["A", "B"]
    assert multi_q.correct_answer_id == "A, B"

    # 3. Test persistence in PostgreSQL and schema reconstruction
    saved = await save_question(multi_q)
    assert saved.id == multi_q.id

    fetched = await get_question_by_id(multi_q.id)
    assert fetched is not None
    assert fetched.interaction_type == "multi_choice"
    assert fetched.primary_trap == "Extreme_Language"
    assert fetched.passage_required == "Yes"
    assert fetched.correct_answer_ids == ["A", "B"]
    assert "A" in fetched.correct_answer_id
    assert "B" in fetched.correct_answer_id
    assert len(fetched.options) == 5

    # Clean up
    await delete_question(multi_q.id)


@pytest.mark.asyncio
async def test_batch_generation_and_staging_flow(monkeypatch):
    from app.repositories.question_repository import get_question_by_id

    monkeypatch.setattr(config, "DEEPINFRA_API_KEY", "")
    monkeypatch.delenv("DEEPINFRA_API_KEY", raising=False)

    # Request batch of 5 questions
    req = GenerationRequest(
        section=MCATSection.BIO_BIOCHEM,
        difficulty=Difficulty.MEDIUM,
        questions_to_generate=5,
    )

    events = []
    async for chunk in run_workflow_stream(req):
        line = chunk.strip()
        if line.startswith("data: "):
            events.append(json.loads(line[6:]))

    # Verify event stream contents
    event_types = [e["event_type"] for e in events]
    assert "workflow_start" in event_types
    assert "batch_progress" in event_types
    assert event_types.count("question_generated") == 5
    assert "workflow_complete" in event_types

    # Verify workflow_complete contains all 5 staged questions
    complete_evt = next(e for e in events if e["event_type"] == "workflow_complete")
    staged_qs = complete_evt["data"]["questions"]
    assert len(staged_qs) == 5

    # Verify candidates are tracked under the live batch and job in PostgreSQL
    live_batch_id = complete_evt["data"]["batch_id"]
    live_job_id = complete_evt["data"]["job_id"]
    assert live_batch_id is not None
    assert live_job_id is not None

    for q_data in staged_qs:
        in_db = await get_question_by_id(q_data["id"])
        assert in_db is not None
        assert in_db.batch_id == live_batch_id
        assert in_db.job_id == live_job_id
        assert in_db.status in ("ai_validated", "batch_only")

    # Test approving selected questions into the Question Bank
    from app.repositories.question_repository import batch_update_question_status

    approved_ids = [staged_qs[0]["id"], staged_qs[1]["id"]]
    await batch_update_question_status(approved_ids, "in_bank")

    q0 = await get_question_by_id(staged_qs[0]["id"])
    q1 = await get_question_by_id(staged_qs[1]["id"])
    q2 = await get_question_by_id(staged_qs[2]["id"])
    assert q0.status == "in_bank"
    assert q1.status == "in_bank"
    assert q2.status != "in_bank"

    # Clean up
    for q_data in staged_qs:
        await delete_question(q_data["id"])


@pytest.mark.asyncio
async def test_single_passage_multi_question_set(monkeypatch):
    """Verifies that 1 shared reading passage is generated for multiple linked questions (Single & Multi-choice)."""
    monkeypatch.setattr(config, "DEEPINFRA_API_KEY", "")
    monkeypatch.delenv("DEEPINFRA_API_KEY", raising=False)

    req = GenerationRequest(
        section=MCATSection.CARS,
        difficulty=Difficulty.MEDIUM,
        questions_to_generate=5,
        passage_required="Yes",
        passage_mode="single_passage",
    )

    events = []
    async for chunk in run_workflow_stream(req):
        line = chunk.strip()
        if line.startswith("data: "):
            events.append(json.loads(line[6:]))

    # Assert Passage Writer events exist
    passage_starts = [
        e
        for e in events
        if e["agent_name"] == "Passage Writer" and e["event_type"] == "agent_start"
    ]
    passage_completes = [
        e
        for e in events
        if e["agent_name"] == "Passage Writer" and e["event_type"] == "agent_complete"
    ]
    assert len(passage_starts) == 1
    assert len(passage_completes) == 1

    shared_passage_text = passage_completes[0]["data"]["passage_text"]
    shared_passage_id = passage_completes[0]["data"]["passage_id"]
    assert shared_passage_text
    assert len(shared_passage_text.split()) > 100
    assert shared_passage_id

    # Check workflow_complete
    complete_events = [e for e in events if e["event_type"] == "workflow_complete"]
    assert len(complete_events) == 1
    data = complete_events[0]["data"]
    questions = data["questions"]
    assert len(questions) == 5

    # Verify all questions share the exact same passage_id and stimulus_text
    single_count = 0
    for q in questions:
        assert q["passage_id"] == shared_passage_id
        assert q["stimulus_text"] == shared_passage_text
        assert q["final_score"] > 90
        if q["interaction_type"] == "single_choice":
            single_count += 1

    assert single_count == 5


@pytest.mark.asyncio
async def test_binary_passage_and_independent_batches(monkeypatch):
    """Verifies clean binary passage mode: either all 5 linked to 1 passage or all 5 independent discretes."""
    monkeypatch.setattr(config, "DEEPINFRA_API_KEY", "")
    monkeypatch.delenv("DEEPINFRA_API_KEY", raising=False)

    # Mode A: 5 Questions all linked to 1 shared passage
    req_passage = GenerationRequest(
        section=MCATSection.BIO_BIOCHEM,
        difficulty=Difficulty.MEDIUM,
        questions_to_generate=5,
        passage_mode="single_passage",
        passage_required="Yes",
    )

    events_a = []
    async for chunk in run_workflow_stream(req_passage):
        line = chunk.strip()
        if line.startswith("data: "):
            events_a.append(json.loads(line[6:]))

    complete_a = next(e for e in events_a if e["event_type"] == "workflow_complete")
    assert complete_a["data"]["passage_mode"] == "single_passage"
    qs_a = complete_a["data"]["questions"]
    assert len(qs_a) == 5
    shared_pid = complete_a["data"]["passage_id"]
    assert shared_pid is not None
    for q in qs_a:
        assert q["passage_id"] == shared_pid
        assert q["passage_required"] == "Yes"
        assert len(q["stimulus_text"]) > 50

    # Mode B: 5 Independent Discretes (No shared passage)
    req_indep = GenerationRequest(
        section=MCATSection.CHEM_PHYS,
        difficulty=Difficulty.MEDIUM,
        questions_to_generate=5,
        passage_mode="independent",
        passage_required="No",
    )

    events_b = []
    async for chunk in run_workflow_stream(req_indep):
        line = chunk.strip()
        if line.startswith("data: "):
            events_b.append(json.loads(line[6:]))

    complete_b = next(e for e in events_b if e["event_type"] == "workflow_complete")
    assert complete_b["data"]["passage_mode"] == "independent"
    qs_b = complete_b["data"]["questions"]
    assert len(qs_b) == 5
    for q in qs_b:
        assert q.get("passage_id") is None
        assert q["passage_required"] == "No"
        assert q["stimulus_text"] == ""


@pytest.mark.asyncio
async def test_independent_question_direct_no_stimulus(monkeypatch):
    """Verifies that independent questions (passage_required='No') enforce empty stimulus_text and direct question stems."""
    from app.agents.generator import _build_generator_user_prompt, _parse_question_draft_data
    from app.agents.mock_fixtures import get_mock_draft

    # 1. Verify user prompt instructions
    req_no_passage = GenerationRequest(
        section=MCATSection.CHEM_PHYS,
        difficulty=Difficulty.MEDIUM,
        passage_required="No",
    )
    prompt_str = _build_generator_user_prompt(req_no_passage)
    assert "Passage Required: No - Standalone discrete question ONLY" in prompt_str
    assert "Leave stimulus_text strictly as an empty string" in prompt_str

    # 2. Verify _parse_question_draft_data enforces empty stimulus when passage_required='No'
    raw_data = {
        "stimulus_text": "Unexpected lingering vignette text that LLM might return.",
        "question_stem": "A 72 kg patient requires 15 mg/kg per day. What is the single dose?",
        "options": [
            {"id": "A", "text": "12.4 mL"},
            {"id": "B", "text": "14.4 mL"},
            {"id": "C", "text": "16.2 mL"},
            {"id": "D", "text": "43.2 mL"},
        ],
        "correct_answer_id": "B",
        "explanation": "Calculated dose is 14.4 mL.",
    }
    draft = _parse_question_draft_data(raw_data, req_no_passage)
    assert draft.stimulus_text == "", (
        "Independent questions must strictly force stimulus_text to empty string"
    )
    assert "72 kg patient" in draft.question_stem

    # When passage_required is 'Yes', stimulus_text is preserved
    req_yes_passage = GenerationRequest(
        section=MCATSection.BIO_BIOCHEM,
        difficulty=Difficulty.MEDIUM,
        passage_required="Yes",
    )
    draft_yes = _parse_question_draft_data(raw_data, req_yes_passage)
    assert draft_yes.stimulus_text == "Unexpected lingering vignette text that LLM might return."

    # 3. Verify get_mock_draft outputs empty stimulus for all subtests when passage_required='No'
    for sec in MCATSection:
        r = GenerationRequest(section=sec, difficulty=Difficulty.MEDIUM, passage_required="No")
        md = get_mock_draft(r)
        if sec == MCATSection.CARS:
            # CARS is strictly 100% passage-based in official MCAT
            continue
        assert md.stimulus_text == "", (
            f"Mock draft for {sec} with passage_required='No' must have empty stimulus_text"
        )
        assert len(md.question_stem) > 10, f"Mock draft for {sec} must have a direct question stem"

    # Multi-choice direct question mock
    r_mc = GenerationRequest(
        section=MCATSection.BIO_BIOCHEM,
        difficulty=Difficulty.HARD,
        interaction_type="multi_choice",
        passage_required="No",
    )
    md_mc = get_mock_draft(r_mc)
    assert md_mc.stimulus_text == ""
    assert "Which" in md_mc.question_stem

    # 4. End-to-end workflow SSE stream: Verify independent discrete batch (5 questions)
    monkeypatch.setattr(config, "DEEPINFRA_API_KEY", "")
    monkeypatch.delenv("DEEPINFRA_API_KEY", raising=False)
    batch_req = GenerationRequest(
        section=MCATSection.CHEM_PHYS,
        difficulty=Difficulty.MEDIUM,
        questions_to_generate=5,
        passage_mode="independent",
        passage_required="No",
    )
    events = []
    async for chunk in run_workflow_stream(batch_req):
        line = chunk.strip()
        if line.startswith("data: "):
            events.append(json.loads(line[6:]))

    # Check worker progress message for independent question items
    batch_progress_events = [e for e in events if e.get("event_type") == "batch_progress"]
    assert len(batch_progress_events) >= 5
    for b_evt in batch_progress_events:
        assert (
            "independent" in b_evt["message"].lower()
            or "direct question" in b_evt["message"].lower()
        )

    # Verify final staged questions
    complete_evt = next(e for e in events if e.get("event_type") == "workflow_complete")
    staged = complete_evt["data"]["questions"]
    assert len(staged) == 5
    for q in staged:
        assert q["passage_required"] == "No"
        assert q["stimulus_text"] == ""


@pytest.mark.asyncio
async def test_passage_set_with_passage_level_visual_stimulus(monkeypatch):
    """Verifies that in passage-type sets, visual stimulus is generated once for the passage and not duplicated question-wise."""
    monkeypatch.setattr(config, "DEEPINFRA_API_KEY", "")
    monkeypatch.delenv("DEEPINFRA_API_KEY", raising=False)

    async def mock_passage_img(*_args, **_kwargs):
        return (
            "data:image/jpeg;base64,mock_passage_flux",
            None,
            "Passage visual stimulus",
            {
                "agent_name": "Image Generator",
                "cost_usd": 0.0020,
                "model": "black-forest-labs/FLUX-1-schnell",
            },
        )

    from app.workflow import engine as workflow_engine
    from app.workflow import nodes as workflow_nodes

    monkeypatch.setattr(workflow_nodes, "generate_image_stimulus", mock_passage_img)
    monkeypatch.setattr(workflow_engine, "generate_image_stimulus", mock_passage_img)

    req = GenerationRequest(
        section=MCATSection.CHEM_PHYS,
        difficulty=Difficulty.MEDIUM,
        questions_to_generate=5,
        passage_mode="single_passage",
        passage_required="Yes",
        require_image=True,
    )

    events = []
    async for chunk in run_workflow_stream(req):
        line = chunk.strip()
        if line.startswith("data: "):
            events.append(json.loads(line[6:]))

    # 1. Diagram & Chart Maker runs once for the passage
    passage_img_completes = [
        e
        for e in events
        if e.get("agent_name") == "Diagram & Chart Maker"
        and e.get("event_type") == "agent_complete"
        and e.get("data", {}).get("stage") == "passage_image"
    ]
    assert len(passage_img_completes) == 1
    assert (
        passage_img_completes[0]["data"]["image_url"] == "data:image/jpeg;base64,mock_passage_flux"
    )
    assert passage_img_completes[0]["data"]["image_svg"] is None

    # 2. workflow_complete has shared passage image
    complete_evt = next(e for e in events if e.get("event_type") == "workflow_complete")
    assert (
        complete_evt["data"]["shared_passage_image_url"]
        == "data:image/jpeg;base64,mock_passage_flux"
    )
    assert complete_evt["data"]["shared_passage_image_svg"] is None

    # 3. Questions have passage_visual_stimulus in outcomes and do NOT run question-wise image generation
    questions = complete_evt["data"]["questions"]
    assert len(questions) == 5
    for q in questions:
        assert (
            q["stage_outcomes"]["passage_visual_stimulus"]["note"]
            == "Visual stimulus belongs to shared reading passage"
        )


@pytest.mark.asyncio
async def test_question_status_lifecycle_and_counts():
    """Verifies question status filtering, counts aggregation, and status transitions."""
    from app.repositories.question_repository import (
        batch_update_question_status,
        get_question_status_counts,
        update_question_status,
    )

    uid1 = str(uuid.uuid4())
    uid2 = str(uuid.uuid4())

    q1 = Question(
        id=uid1,
        section="chem_phys",
        section_label="Chemical and Physical Foundations",
        subtopic="Acid-Base Equilibrium",
        difficulty="Hard",
        question_stem="What is the pH?",
        options=[
            OptionChoice(id="A", text="3.0"),
            OptionChoice(id="B", text="4.0"),
            OptionChoice(id="C", text="5.0"),
            OptionChoice(id="D", text="7.0"),
        ],
        correct_answer_id="A",
        explanation="Calculated pH is 3.0",
        final_score=96,
        status="ai_validated",
    )

    q2 = Question(
        id=uid2,
        section="bio_biochem",
        section_label="Biological and Biochemical Foundations",
        subtopic="Enzyme Kinetics",
        difficulty="Medium",
        question_stem="What is Km?",
        options=[
            OptionChoice(id="A", text="Vmax/2"),
            OptionChoice(id="B", text="Substrate concentration at half Vmax"),
            OptionChoice(id="C", text="Turnover rate"),
            OptionChoice(id="D", text="Inhibition constant"),
        ],
        correct_answer_id="B",
        explanation="Km definition",
        final_score=85,
        status="below_threshold",
    )

    uid3 = str(uuid.uuid4())
    q3 = Question(
        id=uid3,
        section="psych_soc",
        section_label="Psychological, Social, and Biological Foundations",
        subtopic="Cognitive Development",
        difficulty="Medium",
        question_stem="Which stage corresponds to concrete operations?",
        options=[
            OptionChoice(id="A", text="Sensorimotor"),
            OptionChoice(id="B", text="Preoperational"),
            OptionChoice(id="C", text="Concrete operational"),
            OptionChoice(id="D", text="Formal operational"),
        ],
        correct_answer_id="C",
        explanation="Piaget stage 7-11 years.",
        final_score=88,
        status="batch_only",
    )

    uid4 = str(uuid.uuid4())
    q4 = Question(
        id=uid4,
        section="cars",
        section_label="Critical Analysis and Reasoning Skills",
        subtopic="Rhetorical Analysis",
        difficulty="Hard",
        question_stem="The author's tone is best described as:",
        options=[
            OptionChoice(id="A", text="Objective"),
            OptionChoice(id="B", text="Critical"),
            OptionChoice(id="C", text="Nostalgic"),
            OptionChoice(id="D", text="Dismissive"),
        ],
        correct_answer_id="B",
        explanation="Text analysis tone",
        final_score=90,  # 90 is <= 90, so it must NOT pass strict >90 ai_validated check
        status="ai_validated",
    )

    await save_question(q1)
    await save_question(q2)
    await save_question(q3)
    await save_question(q4)

    # Verify filtering: ai_validated strictly returns final_score > 90
    validated_qs = await get_questions(status="ai_validated")
    assert any(q.id == uid1 for q in validated_qs)
    assert not any(q.id == uid2 for q in validated_qs)
    assert not any(q.id == uid3 for q in validated_qs)
    assert not any(q.id == uid4 for q in validated_qs), (
        "Questions with score <= 90 must not appear in ai_validated query!"
    )

    batch_only_qs = await get_questions(status="batch_only")
    assert any(q.id == uid3 for q in batch_only_qs)
    assert not any(q.id == uid1 for q in batch_only_qs)

    below_qs = await get_questions(status="below_threshold")
    assert any(q.id == uid2 for q in below_qs)
    assert not any(q.id == uid1 for q in below_qs)

    # Verify list_questions endpoint defaults strictly to in_bank
    from app.api.v1.questions import export_questions, list_questions

    default_list = await list_questions()
    default_ids = [q["id"] for q in default_list["questions"]]
    assert uid1 not in default_ids, (
        "Unapproved ai_validated question must not appear in default Question Bank list!"
    )
    assert uid2 not in default_ids, (
        "below_threshold question must not appear in default Question Bank list!"
    )
    assert uid3 not in default_ids, (
        "batch_only question must not appear in default Question Bank list!"
    )

    # Verify list_questions with status="ai_validated"
    validated_list = await list_questions(status="ai_validated")
    validated_ids = [q["id"] for q in validated_list["questions"]]
    assert uid1 in validated_ids
    assert uid2 not in validated_ids
    assert uid3 not in validated_ids
    assert uid4 not in validated_ids

    # Test counts
    counts = await get_question_status_counts()
    assert counts["ai_validated"] >= 1
    assert counts["below_threshold"] >= 1
    assert counts["batch_only"] >= 1

    # Update single status (e.g. promote batch_only to in_bank)
    res_single = await update_question_status(uid3, "in_bank")
    assert res_single is True

    # Now verify it immediately appears in the default Question Bank list and in exports
    bank_list_after_approval = await list_questions()
    approved_bank_ids = [q["id"] for q in bank_list_after_approval["questions"]]
    assert uid3 in approved_bank_ids, "Approved question must appear in Question Bank list!"

    export_res = await export_questions()
    export_body = json.loads(export_res.body)
    export_ids = [q["id"] for q in export_body]
    assert uid3 in export_ids, "Approved question must appear in Question Bank export!"
    assert uid2 not in export_ids, "Unapproved question must never appear in Question Bank export!"

    # Batch update status (e.g. discard)
    res_batch = await batch_update_question_status([uid1, uid2, uid3, uid4], "discarded")
    assert res_batch == 4

    # Cleanup
    await delete_question(uid1)
    await delete_question(uid2)
    await delete_question(uid3)
    await delete_question(uid4)


@pytest.mark.asyncio
async def test_deduplication_and_override_api():
    from app.api.v1.questions import (
        check_question_duplicate_endpoint,
        override_question_duplicate_endpoint,
    )
    from app.db.session import init_db
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
    check_res = await check_question_duplicate_endpoint(dup_payload)
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
    from app.repositories.batch_repository import delete_batch, save_batch
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
async def test_questions_pagination_and_slim_projection(client):
    """Verify that GET /questions supports limit, offset, and slim projection flags with total_count."""
    opts = [OptionChoice(id="A", text="Opt A"), OptionChoice(id="B", text="Opt B")]
    prefix = f"pag-{uuid.uuid4().hex[:6]}"
    for i in range(3):
        q = Question(
            id=f"{prefix}-{i}",
            section="chem_phys",
            section_label="Chemical and Physical Foundations",
            difficulty="medium",
            subtopic="Stoichiometry",
            stimulus_text="",
            explanation="Explanation",
            question_stem=f"Pagination {prefix} test question stem #{i}",
            options=opts,
            correct_answer_id="A",
            final_score=92,
            status="in_bank",
            stage_outcomes={"draft": {"stem": "draft stem"}},
            iterations_history=[{"cycle": 1, "score": 92}],
        )
        await save_question(q)

    # 1. Test limit=2
    res_limit = await client.get(f"/api/questions?search={prefix}&limit=2")
    assert res_limit.status_code == 200
    data_limit = res_limit.json()
    assert len(data_limit["questions"]) == 2
    assert "total_count" in data_limit
    assert data_limit["total_count"] >= 3

    # 2. Test slim=true
    res_slim = await client.get(f"/api/questions?search={prefix}&limit=1&slim=true")
    assert res_slim.status_code == 200
    data_slim = res_slim.json()
    assert len(data_slim["questions"]) == 1
    first_q = data_slim["questions"][0]
    assert first_q["stage_outcomes"] == {}
    assert first_q["iterations_history"] == []
