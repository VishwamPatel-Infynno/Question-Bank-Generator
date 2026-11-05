import json

from app.agents.generator import get_mock_draft
from app.agents.image_generator import calculate_flux_image_cost, generate_image_stimulus
from app.core.config import config
from app.schemas import (
    Difficulty,
    GenerationRequest,
    MCATSection,
)
from app.workflow import (
    finalize_node,
    image_node,
    run_workflow_stream,
)


async def test_strict_ai_image_generator(monkeypatch):
    """
    Verifies strict AI image model policy:
    1. Returns error and NO SVG when API key is missing.
    2. Returns pure AI-generated image (image_url) and NO SVG when model succeeds.
    """
    req_ar = GenerationRequest(
        section=MCATSection.CHEM_PHYS, difficulty=Difficulty.HARD, require_image=True
    )
    draft_ar = get_mock_draft(req_ar)

    # 1. Missing API key -> strict error, never fall back to SVG
    monkeypatch.setattr(config, "DEEPINFRA_API_KEY", "")
    _img_url, img_svg, _img_desc, usage = await generate_image_stimulus(draft_ar, req_ar)

    assert _img_url is None
    assert img_svg is None
    assert usage is not None
    assert usage["agent_name"] == "Image Generator"
    assert "error" in usage["details"]

    # 2. Valid API key & mocked FLUX call -> returns image_url, img_svg is strictly None
    monkeypatch.setattr(config, "DEEPINFRA_API_KEY", "mock_key")

    async def mock_call_flux(*_args, **_kwargs):
        return "data:image/jpeg;base64,mock_flux_binary"

    from app.agents import image_generator

    monkeypatch.setattr(image_generator, "call_deepinfra_flux", mock_call_flux)

    img_url, img_svg, _img_desc, usage_success = await generate_image_stimulus(draft_ar, req_ar)
    assert img_url == "data:image/jpeg;base64,mock_flux_binary"
    assert img_svg is None
    assert usage_success["cost_usd"] > 0.0
    assert usage_success["details"]["type"] == "ai_generated_image"


def test_flux_image_cost_formula():
    """
    Verifies mathematical pricing:
    Cost = $0.0005 * (width / 1024) * (height / 1024) * iters
    """
    # Baseline: 1024x1024, 4 iters -> 0.0005 * 1 * 1 * 4 = $0.0020
    assert calculate_flux_image_cost(1024, 1024, 4) == 0.002
    assert config.calculate_flux_image_cost(1024, 1024, 4) == 0.002

    # Resolution 768x768, 4 iters -> 0.0005 * 0.75 * 0.75 * 4 = $0.001125
    assert calculate_flux_image_cost(768, 768, 4) == 0.001125

    # Resolution 512x512, 1 iter -> 0.0005 * 0.5 * 0.5 * 1 = $0.000125
    assert calculate_flux_image_cost(512, 512, 1) == 0.000125

    # Resolution 512x512, 4 iters -> 0.0005 * 0.5 * 0.5 * 4 = $0.0005
    assert calculate_flux_image_cost(512, 512, 4) == 0.0005

    # Resolution 1024x1024, 1 iter -> 0.0005 * 1 * 1 * 1 = $0.0005
    assert calculate_flux_image_cost(1024, 1024, 1) == 0.0005

    # FLUX-2-klein-4b flat rate testing
    assert (
        calculate_flux_image_cost(1024, 1024, 0, model="black-forest-labs/FLUX-2-klein-4b") == 0.014
    )
    assert (
        config.calculate_flux_image_cost(1024, 1024, 0, model="black-forest-labs/FLUX-2-klein-4b")
        == 0.014
    )
    assert (
        calculate_flux_image_cost(512, 512, 0, model="black-forest-labs/FLUX-2-klein-4b") == 0.0035
    )


async def test_image_node_workflow_accumulation(monkeypatch):
    """Verifies that image_node accurately accumulates usage into workflow state with AI image model."""

    async def mock_gen_img(*_args, **_kwargs):
        return (
            "data:image/jpeg;base64,mock_flux",
            None,
            "Mock visual prompt",
            {
                "agent_name": "Image Generator",
                "cost_usd": 0.0020,
                "model": "black-forest-labs/FLUX-1-schnell",
            },
        )

    from app.workflow import nodes as workflow_nodes

    monkeypatch.setattr(workflow_nodes, "generate_image_stimulus", mock_gen_img)

    req = GenerationRequest(
        section=MCATSection.CHEM_PHYS, difficulty=Difficulty.MEDIUM, require_image=True
    )
    draft = get_mock_draft(req)
    state = {
        "request": req.model_dump(),
        "current_draft": draft.model_dump(),
        "total_cost_usd": 0.0015,
        "agent_usage_breakdown": [
            {"agent_name": "Question Generator", "cost_usd": 0.0010},
            {"agent_name": "Question Reviewer", "cost_usd": 0.0005},
        ],
    }
    res = await image_node(state)
    assert res["active_agent"] == "Image Generator"
    assert res["status"] == "image_generated"
    assert res["image_url"] == "data:image/jpeg;base64,mock_flux"
    assert res["image_svg"] is None
    assert len(res["agent_usage_breakdown"]) == 3
    assert res["agent_usage_breakdown"][-1]["agent_name"] == "Image Generator"
    assert "latest_usage" in res


async def test_visual_stimulus_persistence_in_finalize_node():
    """Verifies that finalize_node preserves image_svg, image_url, and image_description in final_question and stage_outcomes."""
    req = GenerationRequest(
        section=MCATSection.CHEM_PHYS,
        difficulty=Difficulty.MEDIUM,
        visual_type="svg_diagram",
    )
    draft = get_mock_draft(req)
    mock_svg = '<svg viewBox="0 0 400 300"><circle cx="200" cy="150" r="80" fill="#0284c7"/></svg>'
    mock_desc = "Scatter diagram showing correlation between patient dosage and response."

    state = {
        "request": req.model_dump(),
        "current_draft": draft.model_dump(),
        "current_review": None,
        "iteration_count": 1,
        "iterations_history": [],
        "total_tokens": 850,
        "total_cost_usd": 0.0003,
        "image_svg": mock_svg,
        "image_url": None,
        "image_description": mock_desc,
        "stage_outcomes": {},
    }

    res = await finalize_node(state)
    final_q = res["final_question"]
    assert final_q["image_svg"] == mock_svg
    assert final_q["image_url"] is None
    assert final_q["image_description"] == mock_desc

    final_payload = res["stage_outcomes"]["final_payload"]
    assert final_payload["image_svg"] == mock_svg
    assert final_payload["image_url"] is None
    assert final_payload["image_description"] == mock_desc


async def test_autonomous_ai_determined_image_workflow(monkeypatch):
    """Verifies that image generation strictly follows autonomous AI determination when enabled, and is bypassed when disabled or in CARS."""
    import app.agents.generator as gen_mod

    monkeypatch.setattr(config, "DEEPINFRA_API_KEY", "")
    monkeypatch.delenv("DEEPINFRA_API_KEY", raising=False)

    from app.agents.base import LLMNotConfiguredError

    async def mock_fail_call_llm(*_args, **_kwargs):
        raise LLMNotConfiguredError("Fast unit test fallback")

    monkeypatch.setattr(gen_mod, "call_llm", mock_fail_call_llm)

    images_generated = []

    async def mock_flux_gen(*_args, **_kwargs):
        images_generated.append(True)
        return (
            "data:image/jpeg;base64,mock_flux",
            None,
            "Autonomous diagram description",
            {"agent_name": "Image Generator", "cost_usd": 0.014},
        )

    from app.workflow import engine as workflow_engine
    from app.workflow import nodes as workflow_nodes

    monkeypatch.setattr(workflow_nodes, "generate_image_stimulus", mock_flux_gen)
    monkeypatch.setattr(workflow_engine, "generate_image_stimulus", mock_flux_gen)

    # 1. allow_ai_images=False: Image generation bypassed even if draft requests it
    req_disabled = GenerationRequest(
        section=MCATSection.CHEM_PHYS,
        difficulty=Difficulty.MEDIUM,
        questions_to_generate=1,
        passage_mode="independent",
        passage_required="No",
        allow_ai_images=False,
    )
    events_disabled = []
    async for chunk in run_workflow_stream(req_disabled):
        line = chunk.strip()
        if line.startswith("data: "):
            events_disabled.append(json.loads(line[6:]))
    assert not any(e.get("agent_name") == "Diagram & Chart Maker" for e in events_disabled)
    assert len(images_generated) == 0

    # 2. CARS with allow_ai_images=True: Strictly NO images generated
    req_cars = GenerationRequest(
        section=MCATSection.CARS,
        difficulty=Difficulty.MEDIUM,
        questions_to_generate=1,
        passage_mode="single_passage",
        allow_ai_images=True,
    )
    events_cars = []
    async for chunk in run_workflow_stream(req_cars):
        line = chunk.strip()
        if line.startswith("data: "):
            events_cars.append(json.loads(line[6:]))
    assert not any(e.get("agent_name") == "Diagram & Chart Maker" for e in events_cars)
    assert len(images_generated) == 0

    # 3. Chem/Phys with allow_ai_images=True: Generates image when AI flags image_needed=True
    req_enabled = GenerationRequest(
        section=MCATSection.CHEM_PHYS,
        difficulty=Difficulty.MEDIUM,
        questions_to_generate=1,
        passage_mode="single_passage",
        passage_required="Yes",
        allow_ai_images=True,
    )
    events_enabled = []
    async for chunk in run_workflow_stream(req_enabled):
        line = chunk.strip()
        if line.startswith("data: "):
            events_enabled.append(json.loads(line[6:]))
    img_evts = [
        e
        for e in events_enabled
        if e.get("agent_name") == "Diagram & Chart Maker"
        and e.get("event_type") == "agent_complete"
    ]
    assert len(img_evts) == 1
    assert len(images_generated) == 1

    # 4. route_after_review honours the model's autonomous image discretion
    from app.workflow.routes import route_after_review

    state_review_needed = {
        "request": req_enabled.model_dump(),
        "current_review": {"total_score": 95},
        "current_draft": {"image_needed": True},
    }
    assert route_after_review(state_review_needed) == "image_generator"

    state_review_not_needed = {
        "request": req_enabled.model_dump(),
        "current_review": {"total_score": 95},
        "current_draft": {"image_needed": False},
    }
    assert route_after_review(state_review_not_needed) == "finalize"
