"""
image_generator.py - Visual Stimulus & Diagram Generation Agent.

Generates AI medical/scientific illustrations (via FLUX on DeepInfra) or vector SVG charts
for MCAT passage stimuli and independent questions, including cost estimation and heuristic fallbacks.
"""

import asyncio
import logging
from typing import Any

import httpx

from app.core.config import config
from app.schemas import GenerationRequest, QuestionDraft

logger = logging.getLogger(__name__)


def calculate_flux_image_cost(
    width: int | None = None,
    height: int | None = None,
    iters: int | None = None,
    base_rate: float | None = None,
    model: str | None = None,
) -> float:
    """
    Calculates DeepInfra image generation cost.
    For FLUX-2-klein-4b: Flat $0.0140 per image (scaled by resolution).
    For iters > 0 / step-based: $0.0005 * (width / 1024) * (height / 1024) * iters.
    """
    _ = model  # Reserved for future per-model rate overrides
    w = width if width is not None else config.IMAGE_WIDTH
    h = height if height is not None else config.IMAGE_HEIGHT

    # If iters is explicitly passed (>0), compute per-step rate (FLUX-1-schnell standard)
    if iters is not None and iters > 0:
        rate = base_rate if base_rate is not None else 0.0005
        return round(rate * (w / 1024.0) * (h / 1024.0) * iters, 6)

    # Flat-rate pricing (FLUX-2-klein-4b)
    rate = base_rate if base_rate is not None else 0.014
    return round(rate * (w / 1024.0) * (h / 1024.0), 6)


async def _call_native_flux_endpoint(
    client: httpx.AsyncClient,
    model_id: str,
    prompt: str,
    width: int,
    height: int,
    iters: int,
    api_key: str,
) -> tuple[str | None, float | None]:
    """Tries the native DeepInfra inference endpoint for image generation."""
    try:
        native_url = f"https://api.deepinfra.com/v1/inference/{model_id}"
        payload: dict[str, Any] = {
            "prompt": prompt,
            "width": width,
            "height": height,
        }
        if "klein" not in model_id.lower() and iters > 0:
            payload["num_inference_steps"] = iters

        res = await client.post(
            native_url, json=payload, headers={"Authorization": f"Bearer {api_key}"}
        )
        if res.status_code == 200:
            data = res.json()
            cost = None
            if "inference_status" in data and isinstance(data["inference_status"], dict):
                cost = data["inference_status"].get("cost")
            if "images" in data and len(data["images"]) > 0:
                return (data["images"][0], cost)
            if "output" in data and len(data["output"]) > 0:
                return (data["output"][0], cost)
        else:
            logger.warning(
                f"DeepInfra native FLUX inference status {res.status_code}: {res.text[:200]}"
            )
    except Exception as e:
        logger.warning(f"DeepInfra native FLUX inference error: {e}")
    return (None, None)


async def _call_openai_flux_endpoint(
    client: httpx.AsyncClient,
    model_id: str,
    prompt: str,
    width: int,
    height: int,
    api_key: str,
) -> tuple[str | None, float | None]:
    """Tries the OpenAI-compatible endpoint on DeepInfra as a fallback."""
    try:
        openai_url = "https://api.deepinfra.com/v1/openai/images/generations"
        payload = {
            "model": model_id,
            "prompt": prompt,
            "size": f"{width}x{height}",
            "n": 1,
        }
        res = await client.post(
            openai_url, json=payload, headers={"Authorization": f"Bearer {api_key}"}
        )
        if res.status_code == 200:
            data = res.json()
            if "data" in data and len(data["data"]) > 0:
                item = data["data"][0]
                img = item.get("url") or (
                    f"data:image/jpeg;base64,{item.get('b64_json')}"
                    if item.get("b64_json")
                    else None
                )
                if img:
                    return (img, None)
        else:
            logger.warning(
                f"DeepInfra OpenAI-compatible FLUX status {res.status_code}: {res.text[:200]}"
            )
    except Exception as e:
        logger.warning(f"DeepInfra OpenAI-compatible FLUX endpoint error: {e}")
    return (None, None)


async def call_deepinfra_flux(
    prompt: str,
    width: int,
    height: int,
    iters: int,
    api_key: str,
    model: str | None = None,
) -> tuple[str | None, float | None]:
    """
    Calls DeepInfra API for dedicated AI image generation (default: black-forest-labs/FLUX-2-klein-4b).
    Supports both native inference endpoint and OpenAI-compatible endpoint with automated retry & backoff.
    Returns: (image_data, actual_cost_if_reported)
    """
    model_id = (model or config.DEFAULT_IMAGE_MODEL).replace("deepinfra/", "").strip()
    if not model_id:
        model_id = "black-forest-labs/FLUX-2-klein-4b"

    max_retries = 2
    for attempt in range(max_retries + 1):
        try:
            async with httpx.AsyncClient(timeout=35.0) as client:
                img_data, cost = await _call_native_flux_endpoint(
                    client, model_id, prompt, width, height, iters, api_key
                )
                if img_data:
                    return (img_data, cost)

                img_data, cost = await _call_openai_flux_endpoint(
                    client, model_id, prompt, width, height, api_key
                )
                if img_data:
                    return (img_data, cost)

        except Exception as client_err:
            logger.warning(
                f"HTTP client error in FLUX call (attempt {attempt + 1}/{max_retries + 1}): {client_err}"
            )

        if attempt < max_retries:
            backoff_secs = 1.0 * (attempt + 1)
            logger.info(f"Retrying AI image model generation in {backoff_secs}s...")
            await asyncio.sleep(backoff_secs)

    logger.error(f"AI image model ({model_id}) generation failed after {max_retries + 1} attempts.")
    return (None, None)


async def generate_image_stimulus(
    draft: QuestionDraft, req: GenerationRequest
) -> tuple[str | None, str | None, str | None, dict[str, Any]]:
    """
    Invokes the Image Generator Agent strictly using the AI Image Model (FLUX-2-klein-4b via DeepInfra).
    Strict policy: Never uses SVG mock fallbacks. Returns: (image_url, None, image_description, usage_dict).
    """
    width = config.IMAGE_WIDTH
    height = config.IMAGE_HEIGHT
    iters = config.IMAGE_ITERS
    model_id = (
        config.DEFAULT_IMAGE_MODEL.replace("deepinfra/", "").strip()
        or "black-forest-labs/FLUX-2-klein-4b"
    )

    if not config.DEEPINFRA_API_KEY:
        logger.error(
            "AI Gateway Key is not configured. Strict image generation policy prohibits SVG mock fallbacks."
        )
        error_usage = {
            "agent_name": "Image Generator",
            "model": model_id,
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
            "cost_usd": 0.0,
            "details": {
                "error": "AI Gateway Key is not configured. Visual stimuli strictly require an active AI image engine.",
                "type": "error",
            },
        }
        return (None, None, None, error_usage)

    prompt_for_image = (
        draft.image_prompt_or_type
        or f"AAMC MCAT educational exam visual stimulus for {req.section.value}: {draft.question_stem}"
    )
    flux_prompt = (
        f"High-quality educational test figure, scientific illustration, or medical diagram on clean white background, high contrast, "
        f"clear professional labeling for AAMC MCAT exam: {prompt_for_image}"
    )
    logger.info(f"Generating AI image with {model_id} ({width}x{height}, {iters} iters)...")

    res = await call_deepinfra_flux(
        prompt=flux_prompt,
        width=width,
        height=height,
        iters=iters,
        api_key=config.DEEPINFRA_API_KEY,
        model=model_id,
    )
    if isinstance(res, tuple):
        img_data, reported_cost = res
    else:
        img_data, reported_cost = res, None

    if img_data:
        cost = (
            reported_cost
            if (
                reported_cost is not None
                and isinstance(reported_cost, (int, float))
                and reported_cost > 0
            )
            else calculate_flux_image_cost(width, height, iters, model=model_id)
        )
        cost_formula = (
            "DeepInfra API reported inference cost"
            if (
                reported_cost is not None
                and isinstance(reported_cost, (int, float))
                and reported_cost > 0
            )
            else (
                f"Flat $0.0140 * ({width}/1024) * ({height}/1024)"
                if "klein" in model_id.lower()
                else f"$0.0005 * ({width}/1024) * ({height}/1024) * {iters}"
            )
        )
        usage_dict = {
            "agent_name": "Image Generator",
            "model": model_id,
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
            "cost_usd": cost,
            "details": {
                "provider": "deepinfra",
                "width": width,
                "height": height,
                "iters": iters,
                "cost_formula": cost_formula,
                "type": "ai_generated_image",
            },
        }
        return (img_data, None, prompt_for_image, usage_dict)

    # If call_deepinfra_flux returns None after all retries:
    logger.error(
        f"AI Image Model ({model_id}) failed to generate an image. Strictly returning failure without SVG mock fallback."
    )
    failure_usage = {
        "agent_name": "Image Generator",
        "model": model_id,
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "total_tokens": 0,
        "cost_usd": 0.0,
        "details": {
            "error": f"Failed to generate image via {model_id} after retries.",
            "type": "error",
        },
    }
    return (None, None, prompt_for_image, failure_usage)
