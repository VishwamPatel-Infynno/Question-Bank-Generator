"""Model output is validated strictly, repaired once, and never silently defaulted."""

import json

import pytest
from app.agents import base, generator, regenerator
from app.agents.base import call_llm_validated
from app.schemas import GenerationRequest, OptionChoice, QuestionDraft, ReviewScore, TokenUsage


def _usage(tokens=10):
    return TokenUsage(
        prompt_tokens=tokens, completion_tokens=0, total_tokens=tokens, cost_usd=0.001
    )


def _req(**kw):
    return GenerationRequest(section="CP", subtopic="Kinetics", difficulty="Medium", **kw)


def _payload(**overrides):
    data = {
        "stimulus_text": "",
        "question_stem": "Which is correct?",
        "options": [{"id": i, "text": f"Option {i} text"} for i in "ABCD"],
        "correct_answer_id": "B",
        "explanation": "Option B is right. A no. C no. D no.",
    }
    data.update(overrides)
    return json.dumps(data)


def _script(monkeypatch, replies):
    calls = []

    async def fake(prompt, system_prompt, **kwargs):
        calls.append({"prompt": prompt, "temperature": kwargs.get("temperature")})
        return replies[len(calls) - 1], _usage()

    monkeypatch.setattr(base, "call_llm", fake)
    return calls


@pytest.mark.asyncio
async def test_valid_output_needs_one_call(monkeypatch):
    calls = _script(monkeypatch, ["42"])
    value, usage = await call_llm_validated("p", "s", parse=int)
    assert value == 42 and len(calls) == 1 and usage.total_tokens == 10


@pytest.mark.asyncio
async def test_invalid_output_is_repaired_once_with_the_error_shown_and_both_calls_billed(
    monkeypatch,
):
    calls = _script(monkeypatch, ["not a number", "7"])
    value, usage = await call_llm_validated("p", "s", parse=int, temperature=0.9)
    assert value == 7
    assert "PREVIOUS REPLY WAS INVALID" in calls[1]["prompt"]
    assert "not a number" in calls[1]["prompt"]
    assert calls[1]["temperature"] == 0.0  # repair runs deterministically
    assert usage.total_tokens == 20


@pytest.mark.asyncio
async def test_second_failure_raises_instead_of_defaulting(monkeypatch):
    _script(monkeypatch, ["nope", "still nope"])
    with pytest.raises(ValueError, match="invalid after repair"):
        await call_llm_validated("p", "s", parse=int)


@pytest.mark.asyncio
async def test_provider_errors_are_not_treated_as_parse_errors(monkeypatch):
    async def boom(*_a, **_k):
        raise RuntimeError("provider down")

    monkeypatch.setattr(base, "call_llm", boom)
    with pytest.raises(RuntimeError, match="provider down"):
        await call_llm_validated("p", "s", parse=int)


def test_missing_or_unknown_key_is_rejected_not_defaulted():
    options = generator._parse_option_choices(json.loads(_payload())["options"])
    with pytest.raises(ValueError, match="no correct_answer_id"):
        generator._parse_correct_keys({}, options)
    with pytest.raises(ValueError, match="not among the options"):
        generator._parse_correct_keys({"correct_answer_id": "E"}, options)
    assert generator._parse_correct_keys({"correct_answer_id": "c"}, options)[1] == ["C"]


@pytest.mark.parametrize(
    "payload",
    ["[]", '"text"', _payload(question_stem=""), _payload(explanation=None)],
)
def test_draft_parser_rejects_malformed_payloads(payload):
    with pytest.raises(ValueError):
        generator._parse_question_draft_data(json.loads(payload), _req())


def test_null_stimulus_is_handled():
    req = _req(passage_required="Yes")
    draft = generator._parse_question_draft_data(json.loads(_payload(stimulus_text=None)), req)
    assert draft.stimulus_text == ""


@pytest.mark.asyncio
async def test_generator_repairs_a_missing_key_via_the_validated_call(monkeypatch):
    bad = json.loads(_payload())
    del bad["correct_answer_id"]
    _script(monkeypatch, [json.dumps(bad), _payload()])
    draft, usage = await generator.generate_question(_req())
    # Options are shuffled after parsing; the key must still point at the model's chosen option
    correct = next(o for o in draft.options if o.id == draft.correct_answer_id)
    assert correct.text == "Option B text"
    assert usage.total_tokens == 20


@pytest.mark.asyncio
async def test_regenerator_preserves_design_metadata_and_gates_images(monkeypatch):
    original = QuestionDraft(
        question_stem="Old stem?",
        options=[OptionChoice(id=i, text=f"Old {i}") for i in "ABCD"],
        correct_answer_id="B",
        explanation="Old explanation.",
        primary_trap="SCOPE_SHIFT",
        aamc_skill="Skill_2",
        likely_mistake_pattern="CONFUSES_AXES",
        image_needed=True,
        image_prompt_or_type="old diagram",
    )
    review = ReviewScore(
        authenticity_score=10,
        clarity_score=10,
        distractor_score=10,
        explanation_score=10,
        total_score=40,
        weaknesses=["weak"],
    )
    reply = _payload(image_needed=True, image_prompt_or_type="new diagram")
    _script(monkeypatch, [reply])

    # Images not permitted by the request: the model's image request must be ignored
    draft, _ = await regenerator.regenerate_question(original, review, _req(), 2)
    assert draft.primary_trap == "SCOPE_SHIFT"
    assert draft.aamc_skill == "Skill_2"
    assert draft.likely_mistake_pattern == "CONFUSES_AXES"
    assert draft.image_needed is False
