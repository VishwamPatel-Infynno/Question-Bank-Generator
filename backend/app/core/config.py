from __future__ import annotations

import json
import logging
import os
from pathlib import Path

# Suppress remote model price map fetch and telemetry to guarantee instant startup and offline resilience
os.environ.setdefault("LITELLM_LOCAL_MODEL_COST_MAP", "True")
os.environ.setdefault("LITELLM_TELEMETRY", "False")

from pydantic import PrivateAttr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.core import pricing

logger = logging.getLogger(__name__)


# DeepInfra FLUX-1-schnell is billed per denoising step (the app's FLUX-2-klein is per image)
FLUX_SCHNELL_COST_PER_STEP = 0.0005


class Settings(BaseSettings):
    # Base paths

    # Active LLM Provider: 'deepinfra', 'anthropic', or 'openai'
    ACTIVE_LLM_PROVIDER: str = "deepinfra"

    # Active Image Provider: 'openai' or 'deepinfra'
    ACTIVE_IMAGE_PROVIDER: str = "openai"

    # PostgreSQL Database URL
    DATABASE_URL: str = "postgresql+asyncpg://mcat_user:mcat_password@localhost:5432/mcat_db"

    # Dedicated Anthropic settings
    ANTHROPIC_MODEL: str = "claude-haiku-5-5"
    ANTHROPIC_COST_PER_MILLION_INPUT_TOKENS: float = 0.10
    ANTHROPIC_COST_PER_MILLION_OUTPUT_TOKENS: float = 0.50
    ANTHROPIC_API_KEY: str = ""

    # Dedicated DeepInfra settings
    DEEPINFRA_MODEL: str = "deepinfra/deepseek-ai/DeepSeek-V4.1-Flash-1017"
    # Standard price. DeepInfra currently also lists a 51% promo ($0.098 / $0.294, no end date);
    # set these two values to use it (see core/pricing.py PRICE_SOURCES).
    DEEPINFRA_COST_PER_MILLION_INPUT_TOKENS: float = 0.20
    DEEPINFRA_COST_PER_MILLION_OUTPUT_TOKENS: float = 0.60
    DEEPINFRA_API_KEY: str = ""
    DEEPINFRA_IMAGE_MODEL: str = "black-forest-labs/FLUX-2-klein-4b"
    DEEPINFRA_IMAGE_COST_PER_UNIT: float = 0.014

    # Dedicated OpenAI settings
    OPENAI_MODEL: str = "gpt-4o-mini"
    OPENAI_COST_PER_MILLION_INPUT_TOKENS: float = 0.15
    OPENAI_COST_PER_MILLION_OUTPUT_TOKENS: float = 0.60
    OPENAI_API_KEY: str = ""
    OPENAI_IMAGE_MODEL: str = "gpt-image-2.5-flare"
    # gpt-image models are billed per token: the cost of an image is the returned usage times these
    # rates (USD per million tokens). The per-unit value below is only the fallback estimate for a
    # response without usage (a 1024x1024 image).
    OPENAI_IMAGE_COST_PER_MILLION_TEXT_INPUT_TOKENS: float = 5.00
    OPENAI_IMAGE_COST_PER_MILLION_IMAGE_INPUT_TOKENS: float = 8.00
    OPENAI_IMAGE_COST_PER_MILLION_OUTPUT_TOKENS: float = 30.00
    OPENAI_IMAGE_COST_PER_UNIT: float = 0.020

    # Private runtime override attributes
    _override_default_text_model: str | None = PrivateAttr(default=None)
    _override_cost_input: float | None = PrivateAttr(default=None)
    _override_cost_output: float | None = PrivateAttr(default=None)

    @property
    def active_provider_key(self) -> str:
        """Normalized active text LLM provider identifier."""
        return (self.ACTIVE_LLM_PROVIDER or "").strip().lower()

    @property
    def active_image_provider_key(self) -> str:
        """Normalized active image provider identifier."""
        return (self.ACTIVE_IMAGE_PROVIDER or "").strip().lower()

    @property
    def DEFAULT_TEXT_MODEL(self) -> str:
        """Active primary text model identifier, dynamically resolved from ACTIVE_LLM_PROVIDER."""
        if self._override_default_text_model is not None:
            return self._override_default_text_model
        if self.active_provider_key == "anthropic":
            return self.ANTHROPIC_MODEL
        if self.active_provider_key == "openai":
            return self.OPENAI_MODEL
        return self.DEEPINFRA_MODEL

    @DEFAULT_TEXT_MODEL.setter
    def DEFAULT_TEXT_MODEL(self, value: str | None) -> None:
        if value is None or value in (
            self.ANTHROPIC_MODEL,
            self.DEEPINFRA_MODEL,
            self.OPENAI_MODEL,
        ):
            self._override_default_text_model = None
        else:
            self._override_default_text_model = value

    @property
    def COST_PER_MILLION_INPUT_TOKENS(self) -> float:
        """Active input token price per million tokens, dynamically resolved from ACTIVE_LLM_PROVIDER."""
        if self._override_cost_input is not None:
            return self._override_cost_input
        if self.active_provider_key == "anthropic":
            return self.ANTHROPIC_COST_PER_MILLION_INPUT_TOKENS
        if self.active_provider_key == "openai":
            return self.OPENAI_COST_PER_MILLION_INPUT_TOKENS
        return self.DEEPINFRA_COST_PER_MILLION_INPUT_TOKENS

    @COST_PER_MILLION_INPUT_TOKENS.setter
    def COST_PER_MILLION_INPUT_TOKENS(self, value: float | None) -> None:
        if value is None or value in (
            self.ANTHROPIC_COST_PER_MILLION_INPUT_TOKENS,
            self.DEEPINFRA_COST_PER_MILLION_INPUT_TOKENS,
            self.OPENAI_COST_PER_MILLION_INPUT_TOKENS,
        ):
            self._override_cost_input = None
        else:
            self._override_cost_input = value

    @property
    def COST_PER_MILLION_OUTPUT_TOKENS(self) -> float:
        """Active output token price per million tokens, dynamically resolved from ACTIVE_LLM_PROVIDER."""
        if self._override_cost_output is not None:
            return self._override_cost_output
        if self.active_provider_key == "anthropic":
            return self.ANTHROPIC_COST_PER_MILLION_OUTPUT_TOKENS
        if self.active_provider_key == "openai":
            return self.OPENAI_COST_PER_MILLION_OUTPUT_TOKENS
        return self.DEEPINFRA_COST_PER_MILLION_OUTPUT_TOKENS

    @COST_PER_MILLION_OUTPUT_TOKENS.setter
    def COST_PER_MILLION_OUTPUT_TOKENS(self, value: float | None) -> None:
        if value is None or value in (
            self.ANTHROPIC_COST_PER_MILLION_OUTPUT_TOKENS,
            self.DEEPINFRA_COST_PER_MILLION_OUTPUT_TOKENS,
            self.OPENAI_COST_PER_MILLION_OUTPUT_TOKENS,
        ):
            self._override_cost_output = None
        else:
            self._override_cost_output = value

    @property
    def FAST_MODEL_CASCADE(self) -> list[str]:
        """Candidate models for fallback, aware of the active provider."""
        if self.active_provider_key == "anthropic":
            return [self.ANTHROPIC_MODEL]
        if self.active_provider_key == "openai":
            return [self.OPENAI_MODEL]
        return [self.DEEPINFRA_MODEL]

    # Image generation parameters
    IMAGE_WIDTH: int = 1024
    IMAGE_HEIGHT: int = 1024
    IMAGE_ITERS: int = 0

    @property
    def DEFAULT_IMAGE_MODEL(self) -> str:
        """Active default image model, dynamically resolved from active image provider."""
        provider = self.get_active_image_provider()
        if provider == "openai":
            return self.OPENAI_IMAGE_MODEL
        return self.DEEPINFRA_IMAGE_MODEL

    def calculate_flux_image_cost(
        self,
        width: int | None = None,
        height: int | None = None,
        iters: int | None = None,
        model: str | None = None,
        quality: str = "standard",
    ) -> float:
        """
        Calculates image generation cost using DeepInfra FLUX model pricing:
        - FLUX-2-klein-4b (flat rate): Flat $0.014 per image (at 1024x1024 base unit)
        - Step-based (iters > 0): rate * (width / 1024) * (height / 1024) * iters
        - If an OpenAI model is explicitly passed, routes to OpenAI rate.
        """
        w = width if width is not None else self.IMAGE_WIDTH
        h = height if height is not None else self.IMAGE_HEIGHT

        if model and self.is_openai_image_model(model):
            return self.calculate_image_cost(
                width=w, height=h, iters=iters, model=model, quality=quality
            )

        # If iters is explicitly passed (>0), compute per-step rate (FLUX-1-schnell standard)
        if iters is not None and iters > 0:
            return round(FLUX_SCHNELL_COST_PER_STEP * (w / 1024.0) * (h / 1024.0) * iters, 7)

        return round(self.DEEPINFRA_IMAGE_COST_PER_UNIT * (w / 1024.0) * (h / 1024.0), 7)

    def calculate_image_cost(
        self,
        width: int | None = None,
        height: int | None = None,
        iters: int | None = None,
        model: str | None = None,
        quality: str = "standard",
    ) -> float:
        """
        Universal image generation cost calculator matching official platform pricing:
        - OpenAI DALL-E 3:
            - 1024x1024: $0.040 Standard, $0.080 HD
            - 1024x1792 / 1792x1024: $0.080 Standard, $0.120 HD
        - OpenAI DALL-E 2:
            - 1024x1024: $0.020
            - 512x512: $0.018
            - 256x256: $0.016
        - OpenAI GPT Image 2.5:
            - gpt-image-2.5-flare: $0.020 base unit scaled by (width/1024)*(height/1024)
            - gpt-image-2.5-sunburst: $0.060 base unit scaled by (width/1024)*(height/1024)
        - DeepInfra FLUX:
            - FLUX-2-klein-4b: Flat $0.0140 scaled by (width/1024)*(height/1024)
            - FLUX-1-schnell: $0.0005 * (width/1024)*(height/1024) * iters
        """
        target_model = (model or self.DEFAULT_IMAGE_MODEL).lower()
        w = width if width is not None else self.IMAGE_WIDTH
        h = height if height is not None else self.IMAGE_HEIGHT

        if self.is_openai_image_model(target_model) and (iters is None or iters <= 0):
            # DALL-E 3
            if "dall-e-3" in target_model:
                is_hd = (quality or "").lower() == "hd"
                is_large = w >= 1792 or h >= 1792
                if is_large:
                    return 0.120 if is_hd else 0.080
                return 0.080 if is_hd else 0.040

            # DALL-E 2
            if "dall-e-2" in target_model or target_model == "dall-e":
                max_dim = max(w, h)
                if max_dim <= 256:
                    return 0.016
                if max_dim <= 512:
                    return 0.018
                return 0.020

            # GPT Image 2.5 models
            base = 0.060 if "sunburst" in target_model else self.OPENAI_IMAGE_COST_PER_UNIT
            return round(base * (w / 1024.0) * (h / 1024.0), 7)

        return self.calculate_flux_image_cost(
            width=width, height=height, iters=iters, model=target_model
        )

    def is_anthropic_model(self, model: str | None = None) -> bool:
        """Determines if the provided or default model is an Anthropic Claude model."""
        target = (model or self.DEFAULT_TEXT_MODEL).strip().lower()
        return "claude" in target or target.startswith("anthropic/")

    def is_openai_model(self, model: str | None = None) -> bool:
        """Determines if the provided or default model is an OpenAI text model."""
        target = (model or self.DEFAULT_TEXT_MODEL).strip().lower()
        return (
            target.startswith(("gpt-", "o1", "o3", "openai/"))
            or "gpt-4" in target
            or "gpt-3.5" in target
        )

    def is_openai_image_model(self, model: str | None = None) -> bool:
        """Determines if the provided or default model is an OpenAI image generation model."""
        target = (model or self.OPENAI_IMAGE_MODEL).strip().lower()
        return "gpt-image" in target or "dall-e" in target or target.startswith("openai/")

    def get_active_provider(self, model: str | None = None) -> str:
        """Returns the primary text provider ('anthropic', 'openai', or 'deepinfra') for the active or given model."""
        if model:
            if self.is_anthropic_model(model):
                return "anthropic"
            if self.is_openai_model(model):
                return "openai"
            return "deepinfra"
        if self.active_provider_key in ("anthropic", "openai"):
            return self.active_provider_key
        if self.is_anthropic_model():
            return "anthropic"
        if self.is_openai_model():
            return "openai"
        return "deepinfra"

    def get_active_image_provider(self, model: str | None = None) -> str:
        """Returns the active image provider ('openai' or 'deepinfra')."""
        if model:
            if self.is_openai_image_model(model):
                return "openai"
            if "flux" in model.lower() or "deepinfra" in model.lower() or "klein" in model.lower():
                return "deepinfra"
        key = self.active_image_provider_key
        if key in ("openai", "deepinfra"):
            # Seamless fallback: If openai is chosen but only DEEPINFRA_API_KEY is configured
            if key == "openai" and not self.OPENAI_API_KEY and self.DEEPINFRA_API_KEY:
                return "deepinfra"
            return key
        return "openai" if self.is_openai_image_model() else "deepinfra"

    def rate_override_applies(self, model: str | None = None) -> bool:
        """True when a runtime rate override (COST_PER_MILLION_* setter) governs this model.

        An override is a price for the ACTIVE provider's models; it must never re-price a model
        that belongs to another provider.
        """
        has_override = (
            getattr(self, "_override_cost_input", None) is not None
            or getattr(self, "_override_cost_output", None) is not None
        )
        if not has_override:
            return False
        return model is None or self.get_active_provider(model) == self.get_active_provider()

    def get_default_pricing_rates(self, model: str | None = None) -> tuple[float, float]:
        """
        Returns (cost_per_million_input, cost_per_million_output) for the given/default model.

        Rates follow the MODEL's provider, not the active provider, so a request-time model from
        another provider is never billed at the active provider's prices:
        1. A runtime override applies to the active provider's models only.
        2. Claude Haiku 5.5 and gpt-4o-mini use their configured rates.
        3. Other Claude/OpenAI models: LiteLLM registry, then family fallbacks.
        4. Everything else is a DeepInfra-hosted model: DeepSeek reasoner, else the configured
           DeepInfra rates (with a one-time warning when the model is not the configured one).
        """
        target = (model or self.DEFAULT_TEXT_MODEL).strip().lower()

        if self.rate_override_applies(target):
            return self.COST_PER_MILLION_INPUT_TOKENS, self.COST_PER_MILLION_OUTPUT_TOKENS

        provider = self.get_active_provider(target)

        if provider == "anthropic":
            if pricing.is_haiku_5_5(target):  # the configured flagship model
                return (
                    self.ANTHROPIC_COST_PER_MILLION_INPUT_TOKENS,
                    self.ANTHROPIC_COST_PER_MILLION_OUTPUT_TOKENS,
                )
            return (
                pricing.litellm_rate(target, "anthropic")
                or pricing.family_rate(target, pricing.ANTHROPIC_FAMILY_RATES)
                or pricing.ANTHROPIC_DEFAULT_RATE
            )

        if provider == "openai":
            if "gpt-4o-mini" in target:  # the configured default model
                return (
                    self.OPENAI_COST_PER_MILLION_INPUT_TOKENS,
                    self.OPENAI_COST_PER_MILLION_OUTPUT_TOKENS,
                )
            return (
                pricing.litellm_rate(target, "openai")
                or pricing.family_rate(target, pricing.OPENAI_FAMILY_RATES)
                or (
                    self.OPENAI_COST_PER_MILLION_INPUT_TOKENS,
                    self.OPENAI_COST_PER_MILLION_OUTPUT_TOKENS,
                )
            )

        # DeepInfra-hosted / custom models
        if pricing.is_deepseek_reasoner(target):
            return pricing.DEEPSEEK_REASONER_RATE

        if target != self.DEEPINFRA_MODEL.strip().lower() and not target.startswith("deepinfra/"):
            pricing.warn_unpriced_model(target, "deepinfra")
        return (
            self.DEEPINFRA_COST_PER_MILLION_INPUT_TOKENS,
            self.DEEPINFRA_COST_PER_MILLION_OUTPUT_TOKENS,
        )

    # CORS Trusted Origins (extra origins beyond localhost defaults, comma-separated or JSON list in .env)
    ALLOWED_ORIGINS: list[str] | str = []

    @field_validator("ALLOWED_ORIGINS", mode="before")
    @classmethod
    def parse_allowed_origins(cls, v: object) -> list[str]:
        if isinstance(v, str):
            v_str = v.strip()
            if v_str.startswith("[") and v_str.endswith("]"):
                try:
                    parsed = json.loads(v_str)
                    if isinstance(parsed, list):
                        return [str(x).strip() for x in parsed if str(x).strip()]
                except (json.JSONDecodeError, ValueError):
                    pass  # Fall through to comma-split parsing
            return [x.strip() for x in v_str.split(",") if x.strip()]
        if isinstance(v, list):
            return [str(x).strip() for x in v if str(x).strip()]
        return []

    @property
    def effective_allowed_origins(self) -> list[str]:
        """Merges hardcoded localhost dev origins with any runtime ALLOWED_ORIGINS overrides."""
        defaults = [
            "http://localhost:5173",
            "http://127.0.0.1:5173",
            "http://localhost:3000",
            "http://127.0.0.1:3000",
        ]
        origins = (
            self.ALLOWED_ORIGINS
            if isinstance(self.ALLOWED_ORIGINS, list)
            else [self.ALLOWED_ORIGINS]
        )
        return list(set(defaults + [o for o in origins if o]))

    # Multi-Agent Workflow Parameters
    MAX_REGENERATION_ATTEMPTS: int = 3
    PASSING_SCORE_THRESHOLD: int = 90
    # Duplicate detection: engine/batch thresholds and the (stricter) on-demand API threshold
    DUPLICATE_HARD_THRESHOLD: float = 0.75
    DUPLICATE_SOFT_THRESHOLD: float = 0.60
    DUPLICATE_API_THRESHOLD: float = 0.80
    # When True the independent reviewer always audits a draft, even if its own self-critique passed.
    ALWAYS_INDEPENDENT_REVIEW: bool = True
    # Hard cap on LLM calls spent on one question slot (drafts, dedup retries, regenerations,
    # review and solve samples, across slot replenishments). 0 disables the cap.
    MAX_LLM_CALLS_PER_SLOT: int = 16
    # Allow mock/heuristic fixtures when no LLM credentials exist (demos, tests). Off by default:
    # a missing key in production must fail loudly instead of shipping fake 'verified' questions.
    OFFLINE_MODE: bool = False
    LOG_FORMAT: str = "text"  # 'text' or 'json' (one JSON object per line)
    # Optional secret for the full /health diagnostic payload (header x-admin-key).
    ADMIN_API_KEY: str = ""
    # Optional shared secret: when set, mutating API calls must send it as X-API-Key.
    API_ACCESS_KEY: str = ""
    # Cost guards for the LLM-spending routes (POST /generate, /batches/start, retry, refill).
    # Requests per client IP per minute (0 disables) and batches allowed to run at once (0 disables).
    GENERATION_RATE_LIMIT_PER_MINUTE: int = 30
    MAX_ACTIVE_BATCHES: int = 5
    # Largest accepted request body in megabytes (HTTP 413 above it); 0 disables
    MAX_REQUEST_BODY_MB: int = 25
    # Run the reviewer and blind solver concurrently (saves one LLM round trip per question).
    PARALLEL_REVIEW_AND_SOLVE: bool = False
    # Mark static system prompts cacheable for providers that need an explicit marker (Anthropic).
    ENABLE_PROMPT_CACHING: bool = True
    BATCH_PASSING_SCORE_THRESHOLD: int = 85
    DEFAULT_MAX_TOKENS: int = 3000
    LLM_MAX_TOKENS_CEILING: int = 8000  # Upper bound when retrying a truncated completion
    REVIEWER_MAX_TOKENS: int = 1800

    # Strict Temperature Parameters for High Instruction Fidelity
    DEFAULT_TEMPERATURE: float = 0.2
    # Drafting needs variety (batches on one subtopic must not converge); the reviewer, solver and
    # regenerator stay low-temperature for consistent judgement.
    GENERATOR_TEMPERATURE: float = 0.5
    PASSAGE_TEMPERATURE: float = 0.7
    REGENERATOR_TEMPERATURE: float = 0.2
    REVIEWER_TEMPERATURE: float = 0.1
    BLIND_SOLVER_TEMPERATURE: float = 0.1

    def passes_quality_gate(self, score: float | int | None) -> bool:
        """Single source of truth for the Tier-1 quality gate: score must be strictly above threshold."""
        return score is not None and score > self.PASSING_SCORE_THRESHOLD

    def get_effective_cascade(self, primary_model: str | None = None) -> list[str]:
        """Returns candidate models for fallback, aware of the active provider."""
        p_model = primary_model or self.DEFAULT_TEXT_MODEL
        if self.is_anthropic_model(p_model):
            return [p_model]
        return self.FAST_MODEL_CASCADE

    # Blind-Solver Dual Validation Agent
    ENABLE_BLIND_SOLVER: bool = True
    # Independent solver: optional dedicated model (empty = the request's model) and sample count
    BLIND_SOLVER_MODEL: str = ""
    BLIND_SOLVER_SAMPLES: int = 2  # 1 = single sample; 2 = two layouts; 3 = tie-breaker on split
    BLIND_SOLVER_CONFIDENCE_THRESHOLD: int = 88
    BLIND_SOLVER_MAX_TOKENS: int = 1200

    # Global Multi-Batch Concurrency & Rate Limiting Controls
    GLOBAL_MAX_CONCURRENT_PIPELINES: int = 8  # question pipelines in flight across all runs
    GLOBAL_MAX_CONCURRENT_JOBS: int = 4
    GLOBAL_MAX_CONCURRENT_LLM_CALLS: int = 10
    LLM_MAX_RETRIES: int = 3
    LLM_BASE_BACKOFF_SECONDS: float = 1.5
    # Per-worker retry attempts for individual question generation jobs within a batch
    WORKFLOW_MAX_WORKER_RETRIES: int = 2

    # Production Database Connection Pool Settings
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 10
    DB_POOL_TIMEOUT: int = 60
    DB_POOL_RECYCLE: int = 1800

    model_config = SettingsConfigDict(
        env_file=[str(Path(__file__).resolve().parent.parent.parent.parent / ".env"), ".env"],
        extra="allow",
    )


config = Settings()
