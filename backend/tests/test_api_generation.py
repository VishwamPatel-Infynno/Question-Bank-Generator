"""Generation flows through the API: batches, passage sets, visuals."""

import json
import uuid

import pytest
from app.agents.generator import get_mock_draft
from app.core.config import config
from app.repositories import (
    delete_question,
    save_question,
)
from app.schemas import (
    Difficulty,
    GenerationRequest,
    MCATSection,
    OptionChoice,
    Question,
)
from app.workflow import (
    run_workflow_stream,
)

pytestmark = pytest.mark.requires_db


@pytest.mark.asyncio
async def test_multichoice_and_passage_support():
    from app.repositories import get_question_by_id

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
    assert draft.correct_answer_id in {o.id for o in draft.options}
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
    from app.repositories import get_question_by_id

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
    assert isinstance(live_batch_id, str) and live_batch_id
    assert isinstance(live_job_id, str) and live_job_id

    for q_data in staged_qs:
        in_db = await get_question_by_id(q_data["id"])
        assert in_db is not None
        assert in_db.batch_id == live_batch_id
        assert in_db.job_id == live_job_id
        assert in_db.status in ("ai_validated", "batch_only")

    # Test approving selected questions into the Question Bank
    from app.repositories import batch_update_question_status

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
    assert isinstance(shared_pid, str) and shared_pid
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
