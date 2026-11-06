"""Question bank API: CRUD, approval, status lifecycle, pagination."""

import json
import uuid

import pytest
from app.api.v1.questions import (
    purge_questions_batch_endpoint,
    purge_single_question,
)
from app.repositories import (
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
from app.workflow import (
    finalize_node,
)

pytestmark = pytest.mark.requires_db


async def test_database_crud():
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


async def test_admin_approval_and_persistence_endpoints():
    from app.api.v1.questions import (
        BatchDeleteRequest,
        approve_and_save_question,
        batch_approve_and_save_questions,
        remove_questions_batch,
    )
    from app.repositories import (
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


async def test_question_status_lifecycle_and_counts():
    """Verifies question status filtering, counts aggregation, and status transitions."""
    from app.repositories import (
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
