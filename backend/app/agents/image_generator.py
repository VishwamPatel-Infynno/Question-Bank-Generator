"""
image_generator.py - Visual Stimulus & Diagram Generation Agent.

Generates AI medical/scientific illustrations (via OpenAI GPT Image 2.5 or FLUX on DeepInfra)
for MCAT passage stimuli and independent questions, including cost estimation and strict error handling.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from typing import Any

import httpx

from app.agents.medical_imaging import (
    detect_medical_modality,
    synthesize_medical_prompt,
)
from app.core.config import config
from app.schemas import GenerationRequest, QuestionDraft

logger = logging.getLogger(__name__)


def calculate_flux_image_cost(
    width: int | None = None,
    height: int | None = None,
    iters: int | None = None,
    base_rate: float | None = None,
    model: str | None = None,
    quality: str = "standard",
) -> float:
    """Calculates image generation cost, delegating to central config calculator with optional base_rate override."""
    w = width if width is not None else config.IMAGE_WIDTH
    h = height if height is not None else config.IMAGE_HEIGHT

    if base_rate is not None:
        multiplier = iters if (iters is not None and iters > 0) else 1.0
        return round(base_rate * (w / 1024.0) * (h / 1024.0) * multiplier, 7)

    return config.calculate_flux_image_cost(
        width=w, height=h, iters=iters, model=model, quality=quality
    )


def calculate_image_cost(
    width: int | None = None,
    height: int | None = None,
    iters: int | None = None,
    base_rate: float | None = None,
    model: str | None = None,
    quality: str = "standard",
) -> float:
    """Universal image generation cost calculator across all supported providers."""
    if base_rate is not None:
        return calculate_flux_image_cost(
            width=width,
            height=height,
            iters=iters,
            base_rate=base_rate,
            model=model,
            quality=quality,
        )
    return config.calculate_image_cost(
        width=width, height=height, iters=iters, model=model, quality=quality
    )


def openai_image_usage_cost(usage: object) -> float | None:
    """Cost of an OpenAI image generation from the usage the API returned, or None without usage.

    gpt-image models bill text input, image input and image output tokens at different rates
    (text $5, image $8, output $30 per million for gpt-image-2.5-flare). Without a text/image split
    in ``input_tokens_details`` all input tokens are text, which is what a plain prompt is.
    """
    if not isinstance(usage, dict):
        return None
    input_tokens = int(usage.get("input_tokens") or usage.get("prompt_tokens") or 0)
    output_tokens = int(usage.get("output_tokens") or usage.get("completion_tokens") or 0)
    if not (input_tokens or output_tokens):
        return None
    details = usage.get("input_tokens_details")
    details = details if isinstance(details, dict) else {}
    image_input = int(details.get("image_tokens") or 0)
    text_input = details.get("text_tokens")
    text_input = int(text_input) if text_input is not None else max(0, input_tokens - image_input)
    return round(
        (text_input / 1_000_000.0) * config.OPENAI_IMAGE_COST_PER_MILLION_TEXT_INPUT_TOKENS
        + (image_input / 1_000_000.0) * config.OPENAI_IMAGE_COST_PER_MILLION_IMAGE_INPUT_TOKENS
        + (output_tokens / 1_000_000.0) * config.OPENAI_IMAGE_COST_PER_MILLION_OUTPUT_TOKENS,
        7,
    )


_IMAGE_MAX_RETRIES = 2


async def _retry_image_call(
    label: str,
    timeout: float,  # noqa: ASYNC109 - sets the HTTP client timeout, not a cancel scope
    attempt_once: Callable[[httpx.AsyncClient], Awaitable[tuple[str | None, float | None]]],
) -> tuple[str | None, float | None]:
    """Runs ``attempt_once`` with a fresh HTTP client, retrying with linear backoff.

    An attempt succeeds when it returns image data; an empty result or an exception is logged and
    retried up to _IMAGE_MAX_RETRIES more times. Returns ``(None, None)`` when all attempts fail.
    """
    for attempt in range(_IMAGE_MAX_RETRIES + 1):
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                img_data, cost = await attempt_once(client)
                if img_data:
                    return (img_data, cost)
        except Exception as err:
            logger.warning(
                "HTTP client error in %s call (attempt %d/%d): %s",
                label,
                attempt + 1,
                _IMAGE_MAX_RETRIES + 1,
                err,
            )

        if attempt < _IMAGE_MAX_RETRIES:
            backoff_secs = 1.0 * (attempt + 1)
            logger.info("Retrying %s generation in %ss...", label, backoff_secs)
            await asyncio.sleep(backoff_secs)

    logger.error("%s generation failed after %d attempts.", label, _IMAGE_MAX_RETRIES + 1)
    return (None, None)


async def call_openai_image_api(
    prompt: str,
    width: int,
    height: int,
    api_key: str,
    model: str | None = None,
    quality: str = "standard",
) -> tuple[str | None, float | None]:
    """
    Calls official OpenAI Image Generation endpoint (v1/images/generations).
    Targets modern GPT Image 2.5 models (default: gpt-image-2.5-flare) and DALL-E 3.
    Requests base64 binary payload (b64_json) for permanent zero-expiration PostgreSQL persistence.
    Returns: (image_data_uri, cost_usd_if_reported_or_calculated)
    """
    model_id = (model or config.OPENAI_IMAGE_MODEL).replace("openai/", "").strip()
    if not model_id:
        model_id = "gpt-image-2.5-flare"

    url = "https://api.openai.com/v1/images/generations"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload: dict[str, Any] = {
        "model": model_id,
        "prompt": prompt,
        "n": 1,
        "size": f"{width}x{height}",
        "response_format": "b64_json",
    }
    if "dall-e-3" in model_id:
        payload["quality"] = quality

    async def attempt_once(client: httpx.AsyncClient) -> tuple[str | None, float | None]:
        res = await client.post(url, json=payload, headers=headers)
        if res.status_code != 200:
            logger.warning(
                "OpenAI image generation error (status %s): %s", res.status_code, res.text[:200]
            )
            return (None, None)
        data = res.json()
        calculated_cost = openai_image_usage_cost(data.get("usage"))
        if calculated_cost is None:
            # No usage in the response: a flat estimate for this size (actual cost depends on
            # quality, see core/pricing.py PRICE_SOURCES), so say so in the log
            logger.warning(
                "OpenAI image response for %s had no usage; using the flat estimate", model_id
            )
            calculated_cost = config.calculate_image_cost(
                width=width, height=height, model=model_id, quality=quality
            )

        if "data" in data and len(data["data"]) > 0:
            item = data["data"][0]
            b64 = item.get("b64_json")
            if b64:
                img_data = f"data:image/png;base64,{b64}" if not b64.startswith("data:") else b64
                return (img_data, calculated_cost)
            if item.get("url"):
                return (item.get("url"), calculated_cost)
        return (None, None)

    return await _retry_image_call(f"OpenAI image model ({model_id})", 45.0, attempt_once)


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
                "DeepInfra native FLUX inference status %s: %s", res.status_code, res.text[:200]
            )
    except Exception as e:
        logger.warning("DeepInfra native FLUX inference error: %s", e)
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
                "DeepInfra OpenAI-compatible FLUX status %s: %s", res.status_code, res.text[:200]
            )
    except Exception as e:
        logger.warning("DeepInfra OpenAI-compatible FLUX endpoint error: %s", e)
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

    async def attempt_once(client: httpx.AsyncClient) -> tuple[str | None, float | None]:
        img_data, cost = await _call_native_flux_endpoint(
            client, model_id, prompt, width, height, iters, api_key
        )
        if img_data:
            return (img_data, cost)
        return await _call_openai_flux_endpoint(client, model_id, prompt, width, height, api_key)

    return await _retry_image_call(f"AI image model ({model_id})", 35.0, attempt_once)


def _image_usage(cost: float, **details: Any) -> dict[str, Any]:
    """The usage record of one image call (image models bill per image, so no tokens)."""
    return {
        "agent": "Image Generator",
        "model": "Infynno Visual Studio v2",
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "total_tokens": 0,
        "cost_usd": cost,
        "details": {"provider": "infynno", **details},
    }


async def generate_image_stimulus(
    draft: QuestionDraft, req: GenerationRequest
) -> tuple[str | None, str | None, str | None, dict[str, Any]]:
    """
    Invokes the Image Generator Agent dynamically routing to the active engine
    (OpenAI GPT Image 2.5 or DeepInfra FLUX).
    Strict policy: Never uses SVG mock fallbacks. Returns: (image_url, None, image_description, usage_dict).
    """
    width = config.IMAGE_WIDTH
    height = config.IMAGE_HEIGHT
    iters = config.IMAGE_ITERS
    active_provider = config.get_active_image_provider()

    if active_provider == "openai":
        model_id = (config.OPENAI_IMAGE_MODEL or config.DEFAULT_IMAGE_MODEL).replace(
            "openai/", ""
        ).strip() or "gpt-image-2.5-flare"
        api_key = config.OPENAI_API_KEY
        if not api_key:
            logger.error(
                "OpenAI API Key is not configured. Strict image generation policy prohibits SVG mock fallbacks."
            )
            error_usage = _image_usage(
                0.0,
                error="AI Visual Studio Key is not configured. Visual stimuli strictly require an active AI image engine.",
                type="error",
            )
            return (None, None, None, error_usage)

        prompt_for_image = (
            draft.image_prompt_or_type
            or f"AAMC MCAT educational exam visual stimulus for {req.section.value}: {draft.question_stem}"
        )
        section_val = req.section.value if hasattr(req.section, "value") else str(req.section)
        topic_val = req.subtopic or getattr(draft, "topic", "") or ""
        stem_val = draft.question_stem or ""

        modality = detect_medical_modality(
            prompt_text=prompt_for_image,
            section=section_val,
            topic=topic_val,
            question_stem=stem_val,
        )
        openai_prompt = synthesize_medical_prompt(prompt_for_image, modality)
        logger.info(
            "Generating OpenAI image with %s [%s] (%sx%s)...",
            model_id,
            modality.value.upper(),
            width,
            height,
        )

        res = await call_openai_image_api(
            prompt=openai_prompt,
            width=width,
            height=height,
            api_key=api_key,
            model=model_id,
        )
        img_data, reported_cost = res if isinstance(res, tuple) else (res, None)

        if img_data:
            cost = (
                reported_cost
                if (
                    reported_cost is not None
                    and isinstance(reported_cost, (int, float))
                    and reported_cost > 0
                )
                else calculate_image_cost(width=width, height=height, model=model_id)
            )
            cost = round(cost, 7)
            cost_formula = f"Standard Visual Stimulus Rate (${cost:.5f}/unit)"
            usage_dict = _image_usage(
                cost,
                width=width,
                height=height,
                cost_formula=cost_formula,
                type="ai_generated_image",
                modality=modality.value,
                medical_modality=modality.value,
            )
            return (img_data, None, prompt_for_image, usage_dict)

        logger.error(
            "OpenAI Image Model (%s) failed to generate an image. Strictly returning failure without SVG mock fallback.",
            model_id,
        )
        failure_usage = _image_usage(
            0.0,
            error="Failed to generate visual stimulus after retries.",
            type="error",
            modality=modality.value,
            medical_modality=modality.value,
        )
        return (None, None, prompt_for_image, failure_usage)

    # DeepInfra FLUX provider
    model_id = (config.DEEPINFRA_IMAGE_MODEL or config.DEFAULT_IMAGE_MODEL).replace(
        "deepinfra/", ""
    ).strip() or "black-forest-labs/FLUX-2-klein-4b"

    if not config.DEEPINFRA_API_KEY:
        logger.error(
            "AI Gateway Key is not configured. Strict image generation policy prohibits SVG mock fallbacks."
        )
        error_usage = _image_usage(
            0.0,
            error="AI Visual Studio Key is not configured. Visual stimuli strictly require an active AI image engine.",
            type="error",
        )
        return (None, None, None, error_usage)

    prompt_for_image = (
        draft.image_prompt_or_type
        or f"AAMC MCAT educational exam visual stimulus for {req.section.value}: {draft.question_stem}"
    )
    section_val = req.section.value if hasattr(req.section, "value") else str(req.section)
    topic_val = req.subtopic or getattr(draft, "topic", "") or ""
    stem_val = draft.question_stem or ""

    modality = detect_medical_modality(
        prompt_text=prompt_for_image,
        section=section_val,
        topic=topic_val,
        question_stem=stem_val,
    )
    flux_prompt = synthesize_medical_prompt(prompt_for_image, modality)
    logger.info(
        "Generating DeepInfra AI image with %s [%s] (%sx%s, %s iters)...",
        model_id,
        modality.value.upper(),
        width,
        height,
        iters,
    )

    res = await call_deepinfra_flux(
        prompt=flux_prompt,
        width=width,
        height=height,
        iters=iters,
        api_key=config.DEEPINFRA_API_KEY,
        model=model_id,
    )
    img_data, reported_cost = res if isinstance(res, tuple) else (res, None)

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
        cost = round(cost, 7)
        cost_formula = (
            f"High-Precision Telemetry Rate (${cost:.6f}/unit)"
            if reported_cost is not None and reported_cost > 0
            else f"Standard Visual Stimulus Rate (${cost:.5f}/unit)"
        )
        usage_dict = _image_usage(
            cost,
            width=width,
            height=height,
            iters=iters,
            cost_formula=cost_formula,
            type="ai_generated_image",
            modality=modality.value,
            medical_modality=modality.value,
        )
        return (img_data, None, prompt_for_image, usage_dict)

    # If call_deepinfra_flux returns None after all retries:
    logger.error(
        "AI Image Model (%s) failed to generate an image. Strictly returning failure without SVG mock fallback.",
        model_id,
    )
    failure_usage = _image_usage(
        0.0,
        error="Failed to generate visual stimulus after retries.",
        type="error",
        modality=modality.value,
        medical_modality=modality.value,
    )
    return (None, None, prompt_for_image, failure_usage)
