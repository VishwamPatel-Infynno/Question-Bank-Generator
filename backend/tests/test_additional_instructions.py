import pytest
from app.agents.prompt_builder import _build_generator_user_prompt
from app.schemas import GenerationRequest, MCATSection


@pytest.mark.asyncio
async def test_generation_request_additional_instructions():
    req = GenerationRequest(
        section=MCATSection.BIO_BIOCHEM,
        subtopic="Enzyme Kinetics",
        additional_instructions="Focus on competitive inhibition with Ki = 1.2 uM and Lineweaver-Burk plots.",
    )
    assert (
        req.additional_instructions
        == "Focus on competitive inhibition with Ki = 1.2 uM and Lineweaver-Burk plots."
    )


@pytest.mark.asyncio
async def test_prompt_builder_includes_additional_instructions():
    instruction_text = (
        "Strictly avoid numerical calculations. Emphasize Le Chatelier's principle in acidosis."
    )
    req = GenerationRequest(
        section=MCATSection.CHEM_PHYS,
        subtopic="Acid-Base Equilibria",
        additional_instructions=instruction_text,
    )
    prompt = _build_generator_user_prompt(req)

    assert "CRITICAL EDUCATOR INSTRUCTION (HIGH FIDELITY MANDATE):" in prompt
    assert instruction_text in prompt


@pytest.mark.asyncio
async def test_prompt_builder_falls_back_to_custom_prompt():
    fallback_text = "Emphasize renal bicarbonate reabsorption mechanisms."
    req = GenerationRequest(
        section=MCATSection.CHEM_PHYS,
        subtopic="Renal Physiology",
        custom_prompt=fallback_text,
    )
    prompt = _build_generator_user_prompt(req)

    assert "CRITICAL EDUCATOR INSTRUCTION (HIGH FIDELITY MANDATE):" in prompt
    assert fallback_text in prompt
