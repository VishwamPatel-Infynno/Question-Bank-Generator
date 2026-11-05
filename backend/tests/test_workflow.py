import json

from app.schemas import (
    Difficulty,
    GenerationRequest,
    MCATSection,
)


async def test_per_question_stage_metadata_in_events(monkeypatch):
    from app.core.config import config
    from app.workflow import run_workflow_stream

    monkeypatch.setattr(config, "DEEPINFRA_API_KEY", "")
    monkeypatch.delenv("DEEPINFRA_API_KEY", raising=False)

    req = GenerationRequest(
        section=MCATSection.CHEM_PHYS,
        difficulty=Difficulty.MEDIUM,
        questions_to_generate=5,
    )

    events = []
    async for chunk in run_workflow_stream(req):
        line = chunk.strip()
        if line.startswith("data: "):
            events.append(json.loads(line[6:]))

    # Assert agent_start events carry index, total, and stage
    gen_starts = [
        e
        for e in events
        if e["event_type"] == "agent_start"
        and e["agent_name"]
        in ("Question Writer & Reviewer", "Question Writer", "Question Generator")
    ]
    assert len(gen_starts) >= 5
    for e in gen_starts:
        assert e["data"]["index"] in (1, 2, 3, 4, 5)
        assert e["data"]["total"] == 5
        assert e["data"]["stage"] in ("drafting", "anti_collision_regeneration")

    rev_starts = [
        e
        for e in events
        if e["event_type"] == "agent_start"
        and e["agent_name"] in ("Quality Reviewer", "Question Reviewer")
    ]
    assert len(rev_starts) >= 5
    for e in rev_starts:
        assert e["data"]["index"] in (1, 2, 3, 4, 5)
        assert e["data"]["total"] == 5
        assert e["data"]["stage"] == "reviewing"
        assert e["data"]["iteration"] >= 1

    q_gens = [e for e in events if e["event_type"] == "question_generated"]
    assert len(q_gens) == 5
    for e in q_gens:
        assert e["data"]["index"] in (1, 2, 3, 4, 5)
        assert e["data"]["total"] == 5
        assert e["data"]["stage"] == "completed"
        assert e["data"]["question"]["index"] in (1, 2, 3, 4, 5)


async def test_fused_workflow_bypasses_reviewer_when_self_critique_passed(monkeypatch):
    """Verifies that if the fused generator self-scores > 90, the separate Reviewer agent node is bypassed."""
    import app.workflow.nodes as nodes_mod
    from app.core.config import config
    from app.schemas import OptionChoice, QuestionDraft, ReviewScore, TokenUsage
    from app.workflow import run_workflow_stream

    monkeypatch.setattr(config, "DEEPINFRA_API_KEY", "")
    monkeypatch.delenv("DEEPINFRA_API_KEY", raising=False)
    # Opt out of the default independent audit to exercise the self-critique bypass path
    monkeypatch.setattr(config, "ALWAYS_INDEPENDENT_REVIEW", False)

    passing_review = ReviewScore(
        authenticity_score=24,
        clarity_score=24,
        distractor_score=24,
        explanation_score=24,
        total_score=96,
        strengths=["Top tier question"],
        weaknesses=[],
        recommendations=[],
        passed=True,
    )
    passing_draft = QuestionDraft(
        stimulus_text="A clinical trial testing drug X...",
        question_stem="Which option is correct?",
        options=[
            OptionChoice(id="A", text="Option A"),
            OptionChoice(id="B", text="Option B"),
            OptionChoice(id="C", text="Option C"),
            OptionChoice(id="D", text="Option D"),
        ],
        correct_answer_id="B",
        correct_answer_ids=["B"],
        explanation="Step by step proof...",
        image_needed=False,
    )
    mock_usage = TokenUsage(
        prompt_tokens=400, completion_tokens=300, total_tokens=700, cost_usd=0.001
    )

    async def mock_fused_gen(_r, *_args, **_kwargs):
        return passing_draft, passing_review, mock_usage

    monkeypatch.setattr(nodes_mod, "generate_question_with_self_critique", mock_fused_gen)

    req = GenerationRequest(
        section=MCATSection.BIO_BIOCHEM,
        difficulty=Difficulty.MEDIUM,
        questions_to_generate=1,
    )

    events = []
    async for chunk in run_workflow_stream(req):
        line = chunk.strip()
        if line.startswith("data: "):
            events.append(json.loads(line[6:]))

    # Reviewer agent_start should NOT be called (bypassed)
    rev_starts = [
        e
        for e in events
        if e["event_type"] == "agent_start"
        and e["agent_name"] in ("Quality Reviewer", "Question Reviewer")
    ]
    assert len(rev_starts) == 0, "Separate Quality Reviewer LLM call was not bypassed!"

    # Separate Quality Reviewer complete event is NOT emitted because Step 1 fused engine handles review
    rev_completes = [
        e
        for e in events
        if e["event_type"] == "agent_complete"
        and e["agent_name"] in ("Quality Reviewer", "Question Reviewer")
    ]
    assert len(rev_completes) == 0, (
        "Separate Quality Reviewer complete should not be emitted on fused pass!"
    )

    # Step 1 Question Writer & Reviewer emitted complete event carrying the self-critique score
    fused_completes = [
        e
        for e in events
        if e["event_type"] == "agent_complete" and e["agent_name"] == "Question Writer & Reviewer"
    ]
    assert len(fused_completes) == 1
    assert fused_completes[0]["data"]["score"] == 96
    assert "Score: 96/100" in fused_completes[0]["message"]


def test_safe_json_loads_and_resilient_parsing():
    from app.agents.base import safe_json_loads
    from app.agents.generator import _parse_question_draft_data

    # 1. Unescaped literal newlines in JSON strings (exact terminal error)
    raw_with_literal_newlines = (
        "{\n"
        '  "stimulus_text": "Paragraph 1 has content.\nParagraph 2 has content on a new line.",\n'
        '  "question_stem": "Which option is correct?",\n'
        '  "options": [\n'
        '    {"id": "A", "text": "Option A"},\n'
        '    {"id": "B", "text": "Option B"},\n'
        '    {"id": "C", "text": "Option C"},\n'
        '    {"id": "D", "text": "Option D"}\n'
        "  ],\n"
        '  "correct_answer_id": "B",\n'
        '  "explanation": "Why B is correct:\nLine 1 proof\nLine 2 proof"\n'
        "}"
    )
    parsed = safe_json_loads(raw_with_literal_newlines)
    assert "Paragraph 2" in parsed["stimulus_text"]
    assert "Line 2 proof" in parsed["explanation"]

    # 2. Markdown fence wrapped in conversational prose
    raw_with_fence = (
        "Here is the requested question:\n"
        "```json\n"
        "{\n"
        '  "stimulus_text": "Sample stimulus",\n'
        '  "question_stem": "Sample stem",\n'
        '  "options": [\n'
        '    {"id": "A", "text": "Option A"},\n'
        '    {"id": "B", "text": "Option B"},\n'
        '    {"id": "C", "text": "Option C"},\n'
        '    {"id": "D", "text": "Option D"}\n'
        "  ],\n"
        '  "correct_answer_id": "A",\n'
        '  "explanation": "Rationale"\n'
        "}\n"
        "```\n"
        "I hope this satisfies the psychometric standard."
    )
    parsed2 = safe_json_loads(raw_with_fence)
    assert parsed2["correct_answer_id"] == "A"

    # 3. Trailing comma in JSON
    raw_trailing_comma = (
        "{\n"
        '  "stimulus_text": "",\n'
        '  "question_stem": "Stem",\n'
        '  "options": [\n'
        '    {"id": "A", "text": "A"},\n'
        '    {"id": "B", "text": "B"},\n'
        '    {"id": "C", "text": "C"},\n'
        '    {"id": "D", "text": "D"},\n'
        "  ],\n"
        '  "correct_answer_id": "A",\n'
        '  "explanation": "Exp",\n'
        "}"
    )
    parsed3 = safe_json_loads(raw_trailing_comma)
    assert len(parsed3["options"]) == 4

    # 4. Parse draft data with dict options
    req = GenerationRequest(
        section=MCATSection.PSYCH_SOC,
        difficulty=Difficulty.MEDIUM,
        passage_required="No",
    )
    dict_options_data = {
        "stimulus_text": "",
        "question_stem": "Stem",
        "options": {"A": "Choice A", "B": "Choice B", "C": "Choice C", "D": "Choice D"},
        "correct_answer_id": "C",
        "explanation": "Option C is correct",
    }
    draft = _parse_question_draft_data(dict_options_data, req)
    assert len(draft.options) == 4
    assert draft.correct_answer_id == "C"
