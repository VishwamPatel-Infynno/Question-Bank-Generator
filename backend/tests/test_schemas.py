import pytest
from app.schemas import (
    GenerationRequest,
    MCATSection,
    OptionChoice,
    QuestionDraft,
)
from pydantic import ValidationError


async def test_schemas_validation():
    # Test valid options
    opts = [
        OptionChoice(id="A", text="Option A"),
        OptionChoice(id="B", text="Option B"),
        OptionChoice(id="C", text="Option C"),
        OptionChoice(id="D", text="Option D"),
    ]
    draft = QuestionDraft(
        stimulus_text="Sample MCAT reading passage.",
        question_stem="Which option follows?",
        options=opts,
        correct_answer_id="B",
        explanation="Option B is correct because...",
        image_needed=False,
    )
    assert len(draft.options) == 4
    assert draft.correct_answer_id == "B"

    # Test batch limit <= 50 constraint
    valid_batch_req = GenerationRequest(
        section=MCATSection.CHEM_PHYS,
        questions_to_generate=10,
    )
    assert valid_batch_req.questions_to_generate == 10

    # Test batch limit <= 50 constraint
    with pytest.raises(ValidationError):
        GenerationRequest(
            section=MCATSection.CHEM_PHYS,
            questions_to_generate=51,
        )

    # Test calculate_mcat_scaled_score parity between 'high' and legacy 'hard'
    from app.schemas import calculate_mcat_scaled_score

    score_high = calculate_mcat_scaled_score(audit_total=98, difficulty="high")
    score_hard = calculate_mcat_scaled_score(audit_total=98, difficulty="hard")
    score_medium = calculate_mcat_scaled_score(audit_total=98, difficulty="medium")

    assert score_high["section_score"] == 132
    assert score_hard["section_score"] == 132
    assert score_medium["section_score"] == 131
    assert score_high["composite_score"] == 528
    assert score_medium["composite_score"] == 524
