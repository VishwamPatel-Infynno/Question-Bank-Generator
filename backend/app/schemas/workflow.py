from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator

from app.schemas.mcat import Difficulty, MCATSection, normalize_section

KNOWN_VISUAL_TYPES: tuple[str, ...] = (
    "SVG_Diagram",
    "AI_FLUX_Image",
    "AI_Image",
    "AI_OpenAI_Image",
)


class GenerationRequest(BaseModel):
    section: MCATSection
    subtopic: str | None = None
    difficulty: Difficulty = Difficulty.MEDIUM
    aamc_skill: str | None = Field(
        default=None,
        description="AAMC Scientific Inquiry & Reasoning Skill (SIRS) or CARS skill classification",
    )
    allow_ai_images: bool = Field(
        default=False,
        description="Whether AI is permitted to generate visual stimuli (figures, diagrams, illustrations, plots) when deemed pedagogically necessary",
    )
    require_image: bool = False
    require_passage_image: bool = Field(
        default=False,
        description="Whether the shared reading passage stimulus requires an image diagram",
    )
    custom_prompt: str | None = None
    additional_instructions: str | None = Field(
        default=None,
        description="Educator instructions specifying constraints, scenarios, or pedagogical rules to strictly enforce",
    )
    model_name: str | None = None
    api_key: str | None = None

    # Execution & Batch UUID Identifiers
    run_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()), description="Unique execution run UUID4"
    )
    batch_id: str | None = Field(
        None, description="Optional batch run UUID4 binding multiple questions"
    )
    job_id: str | None = Field(
        None, description="Optional batch job UUID4 binding questions to a specific job"
    )
    passing_threshold: int | None = Field(
        None,
        description="Quality benchmark passing threshold score (defaults to 90; 85 for batch jobs)",
    )

    # Manager Combination Matrix attributes
    combination_id: str | None = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Combination UUID4 or custom code e.g. CMB00001",
    )
    subcategory: str | None = Field(None, description="e.g. Inference")
    content_domain: str | None = Field(None, description="e.g. General_Chemistry, Biochemistry")
    question_type: str | None = Field(
        None, description="e.g. Passage_Based_Set, Independent_Discrete"
    )
    interaction_type: str | None = Field(
        "single_choice", description="single_choice (standard 4-choice AAMC)"
    )
    primary_trap: str | None = Field(None, description="e.g. Out_of_Scope, Distortion_Opposite")
    passage_required: str | bool | None = Field(None, description="Yes or No")
    passage_mode: str | None = Field(
        "single_passage",
        description="single_passage (all 5 linked to 1 passage) or independent (all 5 standalone discretes)",
    )
    passage_id: str | None = Field(
        None, description="Shared UUID for questions linked to the same passage"
    )
    shared_stimulus: str | None = Field(None, description="Pre-generated shared passage text")
    passage_questions: int | None = Field(None, description="Number of passage questions e.g. 5")
    image_required: str | bool | None = Field(None, description="Yes or No")
    visual_type: str | None = Field("None", description="e.g. None, SVG_Diagram, AI_FLUX_Image")

    # Granular Dependent Taxonomy Hierarchy
    subject: str | None = Field(None, description="Taxonomy subject e.g. General Chemistry")
    unit: str | None = Field(
        None, description="Taxonomy unit e.g. Atomic Structure and Periodicity"
    )
    topic: str | None = Field(None, description="Taxonomy topic e.g. Periodic Trends")
    subskill: str | None = Field(None, description="Granular AAMC subskill focus")
    likely_mistake_pattern: str | None = Field(
        None, description="Targeted student misconception pattern"
    )
    thematic_angle: str | None = Field(
        None, description="Optional angle/scenario focus to guarantee cross-job passage diversity"
    )
    content_domains: list[str] | None = Field(None, description="Multi-selected content domains")

    questions_to_generate: int = Field(
        5,
        ge=1,
        le=50,
        description="Quantity to generate in MCAT batch (1 to 50 questions)",
    )
    passage_count: int | None = Field(
        None, ge=0, le=50, description="Number of passage-type items in batch"
    )
    passage_question_count: int | None = Field(
        5, ge=0, le=50, description="Number of questions linked to the shared passage"
    )
    auto_save: bool = Field(
        False,
        description="Whether to automatically persist candidate in the Question Bank (default: False for admin review)",
    )

    @property
    def is_passage_active(self) -> bool:
        """Determines whether a reading passage stimulus is active for this request."""
        # CARS is strictly 100% passage-based in official MCAT
        if self.section in (MCATSection.CARS, "CARS", "cars"):
            return True
        if self.passage_required is not None:
            return str(self.passage_required).lower() in ("yes", "true", "1")
        if self.shared_stimulus and self.shared_stimulus.strip():
            return True
        return self.passage_mode != "independent"

    @property
    def requires_visual_stimulus(self) -> bool:
        """Determines whether visual image/diagram stimulus generation is explicitly required."""
        if self.section in (MCATSection.CARS, "CARS", "cars"):
            return False
        if self.visual_type in KNOWN_VISUAL_TYPES:
            return True
        return bool(self.require_image or self.require_passage_image)

    @field_validator("combination_id", mode="before")
    @classmethod
    def validate_combination_id(cls, v):
        if v is None or (isinstance(v, str) and not v.strip()):
            return str(uuid.uuid4())
        return str(v).strip()

    @field_validator("section", mode="before")
    @classmethod
    def validate_section(cls, v):
        if isinstance(v, str):
            return normalize_section(v)
        return v

    @field_validator("difficulty", mode="before")
    @classmethod
    def validate_difficulty(cls, v):
        if isinstance(v, str):
            lower = v.strip().lower()
            if lower in ["low", "easy", "foundational"]:
                return Difficulty.LOW
            if lower in ["medium", "standard", "standard exam"]:
                return Difficulty.MEDIUM
            if lower in ["high", "hard", "top percentile", "mastery", "elite"]:
                return Difficulty.HIGH
            raise ValueError(
                f"Invalid difficulty '{v}'. Difficulty must strictly be one of: low, medium, high."
            )
        return v

    @model_validator(mode="after")
    def resolve_binary_passage_and_fixed_count(self) -> GenerationRequest:
        """Enforces 1 to 50 questions for batch runs and binary passage mode (all linked or all independent)."""
        if not (1 <= self.questions_to_generate <= 50):
            raise ValueError(
                f"MCAT question generation requires 1 to 50 questions per run (received {self.questions_to_generate})."
            )

        total_q = self.questions_to_generate or 5

        # Rule 1: CARS is ALWAYS 100% passage-based (all linked to passage)
        if self.section in (MCATSection.CARS, "cars", "CARS"):
            self.passage_mode = "single_passage"
            self.passage_required = "Yes"
            self.passage_question_count = total_q
            self.passage_count = total_q
            return self

        # Rule 2: Science sections - binary choice (all passage-linked or all independent discretes)
        is_independent = (
            self.passage_mode == "independent"
            or str(self.passage_required).lower() in ("no", "false", "0")
            or (self.passage_question_count == 0 and not self.shared_stimulus)
        )

        if is_independent:
            self.passage_mode = "independent"
            self.passage_required = "No"
            self.passage_question_count = 0
            self.passage_count = 0
        else:
            self.passage_mode = "single_passage"
            self.passage_required = "Yes"
            self.passage_question_count = total_q
            self.passage_count = total_q

        return self


class WorkflowEvent(BaseModel):
    event_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()), description="Unique SSE event UUID4"
    )
    run_id: str | None = Field(None, description="Execution run UUID4")
    batch_id: str | None = Field(None, description="Batch execution UUID4")
    event_type: str  # 'workflow_start', 'agent_start', 'agent_complete', 'workflow_complete', 'question_rejected', 'workflow_rejected', 'workflow_error'
    agent_name: str  # 'Question Generator', 'Question Reviewer', 'Question Re-Generator', 'Image Generator', 'Quality Gate', 'System'
    message: str
    data: dict[str, Any] | None = None
    timestamp: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
