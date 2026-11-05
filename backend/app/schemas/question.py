"""
question.py - Pydantic schemas for MCAT questions, passages, batches, and jobs.

Defines the core data contracts for the MCAT Question Bank Generator:
- Question lifecycle statuses and validation
- QuestionDraft, ReviewScore, and OptionChoice schemas
- Passage and GenerationBatch/Job structures
- Request/response payloads for status updates and duplicate checking
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

from app.core.config import config
from app.schemas.mcat import calculate_mcat_scaled_score


class QuestionStatus(str, Enum):
    """Lifecycle statuses for MCAT questions."""

    IN_BANK = "in_bank"
    AI_VALIDATED = "ai_validated"
    BATCH_ONLY = "batch_only"
    BELOW_THRESHOLD = "below_threshold"
    DISCARDED = "discarded"
    APPROVED = "approved"
    REJECTED_BELOW_THRESHOLD = "rejected_below_threshold"
    ERROR = "error"
    FAILED = "failed"


ACTIVE_QUESTION_STATUSES: frozenset[str] = frozenset(
    {
        QuestionStatus.IN_BANK.value,
        QuestionStatus.AI_VALIDATED.value,
        QuestionStatus.BATCH_ONLY.value,
        QuestionStatus.APPROVED.value,
    }
)

INACTIVE_QUESTION_STATUSES: frozenset[str] = frozenset(
    {
        QuestionStatus.DISCARDED.value,
        QuestionStatus.BELOW_THRESHOLD.value,
        QuestionStatus.REJECTED_BELOW_THRESHOLD.value,
        QuestionStatus.ERROR.value,
        QuestionStatus.FAILED.value,
    }
)

VALID_QUESTION_STATUSES: frozenset[str] = ACTIVE_QUESTION_STATUSES | INACTIVE_QUESTION_STATUSES


def is_question_active(status: str | QuestionStatus | None) -> bool:
    """Returns True if the question status represents an active, non-discarded question."""
    if not status:
        return False
    val = status.value if isinstance(status, QuestionStatus) else str(status)
    return val in ACTIVE_QUESTION_STATUSES


class OptionChoice(BaseModel):
    id: str  # A, B, C, D
    text: str


class DuplicateInfo(BaseModel):
    is_duplicate: bool = False
    similarity_score: float = 0.0
    matched_question_id: str | None = None
    matched_question_stem: str | None = None
    matched_options: list[dict[str, Any]] | None = None
    matched_explanation: str | None = None
    match_reason: str | None = None
    is_overridden: bool = False
    overridden_at: str | None = None


class ReviewScore(BaseModel):
    audit_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique psychometric audit evaluation UUID4",
    )
    evaluated_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
    authenticity_score: int = Field(
        ..., ge=0, le=25, description="AAMC MCAT authentic scientific tone and style (0-25)"
    )
    clarity_score: int = Field(
        ..., ge=0, le=25, description="Stem clarity and logical tightness (0-25)"
    )
    distractor_score: int = Field(
        ..., ge=0, le=25, description="Plausibility and sophistication of distractors (0-25)"
    )
    explanation_score: int = Field(
        ..., ge=0, le=25, description="Soundness and rigor of step-by-step key proof (0-25)"
    )
    total_score: int = Field(..., ge=0, le=100, description="Overall psychometric score (0-100)")
    strengths: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
    passed: bool = Field(False, description="True if total_score > 90 benchmark")


class QuestionDraft(BaseModel):
    stimulus_text: str = Field(
        "", description="Reading passage, clinical case context, or research scenario"
    )
    question_stem: str = Field(..., description="The direct question or prompt to solve")
    options: list[OptionChoice] = Field(
        ..., min_length=4, max_length=4, description="4 choices (A, B, C, D)"
    )
    correct_answer_id: str = Field(
        ..., description="Key option id e.g. 'A', or comma-joined keys e.g. 'A, C'"
    )
    correct_answer_ids: list[str] = Field(
        default_factory=list, description="List of correct keys e.g. ['A']"
    )
    explanation: str = Field(
        ..., description="Comprehensive step-by-step cognitive and pedagogical rationale"
    )
    image_needed: bool = Field(False, description="True if a visual diagram/chart is essential")
    image_prompt_or_type: str | None = Field(
        None, description="Visual description, chart type, or SVG geometry description"
    )
    primary_trap: str | None = Field(
        None, description="Primary cognitive distractor trap used (e.g. Scope_Shift, Out_of_Scope)"
    )
    aamc_skill: str | None = Field(
        None,
        description="AAMC Scientific Inquiry & Reasoning Skill (SIRS) or CARS skill classification",
    )
    subject: str | None = Field(None, description="Taxonomy subject e.g. General Chemistry")
    unit: str | None = Field(
        None, description="Taxonomy unit e.g. Atomic Structure and Periodicity"
    )
    topic: str | None = Field(None, description="Taxonomy topic e.g. Periodic Trends")
    subskill: str | None = Field(None, description="Granular AAMC subskill focus")
    likely_mistake_pattern: str | None = Field(
        None, description="Targeted student misconception or mistake pattern"
    )

    def model_post_init(self, __context: Any) -> None:
        # Synchronize correct_answer_id and correct_answer_ids
        if not self.correct_answer_ids and self.correct_answer_id:
            self.correct_answer_ids = [
                k.strip().upper() for k in self.correct_answer_id.split(",") if k.strip()
            ]
        elif self.correct_answer_ids and not self.correct_answer_id:
            self.correct_answer_id = ", ".join(self.correct_answer_ids)
        elif self.correct_answer_ids and self.correct_answer_id:
            # Ensure upper-case
            self.correct_answer_ids = [k.strip().upper() for k in self.correct_answer_ids]
            self.correct_answer_id = self.correct_answer_id.strip().upper()


class Question(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    run_id: str | None = Field(None, description="Workflow execution run UUID4")
    batch_id: str | None = Field(
        None, description="Batch execution UUID4 binding multiple questions"
    )
    job_id: str | None = Field(
        None, description="Job execution UUID4 binding questions to a specific job"
    )
    status: str = Field(
        "in_bank",
        description="Lifecycle status: 'ai_validated', 'in_bank', 'discarded', 'below_threshold', 'batch_only'",
    )
    is_deleted: bool = Field(
        False, description="Whether the question is soft-deleted from the bank"
    )
    deleted_at: str | None = Field(
        None, description="ISO timestamp when the question was soft-deleted"
    )
    section: str
    section_label: str
    subtopic: str
    difficulty: str
    stimulus_text: str | None = None
    question_stem: str
    options: list[OptionChoice]
    correct_answer_id: str
    correct_answer_ids: list[str] = Field(default_factory=list)
    explanation: str
    image_url: str | None = None
    image_svg: str | None = None
    image_description: str | None = None
    final_score: int = 95
    review_rubric: ReviewScore | None = None
    mcat_scaled_score: int | None = Field(
        None, description="Calibrated MCAT section scaled score (118-132)"
    )
    mcat_percentile: str | None = Field(
        None, description="Calibrated percentile rank e.g. '96th Percentile (Top Tier)'"
    )
    aamc_skill: str | None = Field(None, description="AAMC SIRS or CARS skill classification")

    iteration_count: int = 1
    iterations_history: list[dict[str, Any]] = Field(default_factory=list)
    total_tokens: int = Field(
        0, description="Total tokens consumed across all agent generation & review cycles"
    )
    prompt_tokens: int = Field(0, description="Total prompt tokens consumed")
    completion_tokens: int = Field(0, description="Total completion tokens generated")
    cost_usd: float = Field(
        0.0, description="Total estimated cost in USD based on exact model rates"
    )
    token_usage_details: list[dict[str, Any]] | dict[str, Any] | None = Field(
        default_factory=list, description="Per-agent granular token and cost breakdown"
    )
    created_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
    updated_at: str | None = None

    # Manager Combination Matrix attributes
    combination_id: str | None = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Combination UUID4 or custom manager code",
    )
    content_domain: str | None = Field(None, description="e.g. Science, Healthcare")
    question_type: str | None = Field(None, description="e.g. Passage_MCQ, Independent_Discrete")
    interaction_type: str | None = Field(
        "single_choice", description="single_choice (standard 4-choice AAMC)"
    )
    primary_trap: str | None = Field(None, description="e.g. Keyword_Trap, Partial_Match")
    passage_required: str | None = Field(None, description="Yes or No")
    passage_mode: str | None = Field(
        "single_passage",
        description="single_passage (1 shared passage) or independent (separate scenarios)",
    )
    passage_id: str | None = Field(
        None, description="Shared UUID for questions linked to the same passage"
    )
    passage_questions: int | None = Field(None, description="Number of passage questions e.g. 3, 4")
    visual_type: str | None = Field("None", description="e.g. None, SVG_Diagram, AI_FLUX_Image")

    # Granular Dependent Taxonomy Hierarchy
    subject: str | None = Field(None, description="Taxonomy subject e.g. General Chemistry")
    unit: str | None = Field(
        None, description="Taxonomy unit e.g. Atomic Structure and Periodicity"
    )
    topic: str | None = Field(None, description="Taxonomy topic e.g. Periodic Trends")
    subskill: str | None = Field(None, description="Granular AAMC subskill focus")
    likely_mistake_pattern: str | None = Field(
        None, description="Targeted student misconception or mistake pattern"
    )

    # Deduplication & Collision Metadata
    duplicate_info: DuplicateInfo | None = Field(
        None, description="Collision evaluation details against existing bank or batch items"
    )
    is_duplicate_override: bool = Field(
        False,
        description="Whether an administrator or reviewer manually approved a flagged duplicate",
    )

    # Multi-Stage Raw Outcome JSON
    stage_outcomes: dict[str, Any] | None = Field(
        default_factory=dict, description="Raw outcome JSON of all agent workflow stages"
    )
    option_symmetry: dict[str, Any] | None = Field(
        default_factory=dict,
        description="Option length disparity, symmetry score, and anti-guessability balance metrics",
    )

    def model_post_init(self, __context: Any) -> None:
        if not self.correct_answer_ids and self.correct_answer_id:
            self.correct_answer_ids = [
                k.strip().upper() for k in self.correct_answer_id.split(",") if k.strip()
            ]
        elif self.correct_answer_ids and not self.correct_answer_id:
            self.correct_answer_id = ", ".join(self.correct_answer_ids)

        if not self.mcat_scaled_score:
            scaled_info = calculate_mcat_scaled_score(self.final_score, self.difficulty)
            self.mcat_scaled_score = scaled_info["section_score"]
            if not self.mcat_percentile:
                self.mcat_percentile = scaled_info["percentile"]


class Passage(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str | None = None
    text: str
    word_count: int | None = None
    section: str | None = None
    subtopic: str | None = None
    image_url: str | None = None
    image_svg: str | None = None
    image_description: str | None = None
    question_count: int = 0
    is_deleted: bool = Field(False, description="Whether the passage is soft-deleted from the bank")
    deleted_at: str | None = Field(
        None, description="ISO timestamp when the passage was soft-deleted"
    )
    created_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
    updated_at: str | None = None


class GenerationBatch(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    section: str | None = None
    subtopic: str | None = None
    difficulty: str | None = None
    passage_mode: str | None = None
    target_count: int = 50
    actual_count: int = 0
    total_jobs: int = 10
    completed_jobs: int = 0
    failed_jobs: int = 0
    error_message: str | None = None
    total_tokens: int = 0
    cost_usd: float = 0.0
    status: str = "completed"
    request_payload: dict[str, Any] | None = None
    created_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
    updated_at: str | None = None


class GenerationJob(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    batch_id: str
    job_number: int
    status: str = "pending"  # pending, running, completed, failed
    target_count: int = 5
    actual_count: int = 0
    trial_count: int = 1
    passage_id: str | None = None
    total_tokens: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    cost_usd: float = 0.0
    error_message: str | None = None
    created_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
    started_at: str | None = None
    completed_at: str | None = None


class ResolveDuplicatesRequest(BaseModel):
    """Payload for resolving duplicate clusters inside a batch."""

    # "archive" (mark status='discarded', recoverable; the default) or "delete" (permanent)
    action: Literal["archive", "delete"] = "archive"
    cluster_ids: list[str] | None = None  # Specific cluster IDs, or None for all
    custom_leader_ids: list[str] | None = None  # Optional custom leader question IDs


class BatchDeleteRequest(BaseModel):
    """Request body for bulk question deletion."""

    ids: list[str] = Field(max_length=1000)


def _validate_question_status(v: Any) -> str:
    """Shared validator: normalizes and guards the question lifecycle status field."""
    val = v.value if hasattr(v, "value") else str(v)
    if val not in VALID_QUESTION_STATUSES:
        raise ValueError(
            f"Invalid status '{val}'. Must be one of {sorted(VALID_QUESTION_STATUSES)}"
        )
    return val


class StatusUpdateRequest(BaseModel):
    """Request body for updating lifecycle status of questions."""

    ids: list[str] = Field(max_length=1000)
    status: QuestionStatus | str

    @field_validator("status", mode="before")
    @classmethod
    def validate_status(cls, v: Any) -> str:
        return _validate_question_status(v)


class SingleStatusUpdateRequest(BaseModel):
    """Request body for updating lifecycle status of a single question."""

    status: QuestionStatus | str

    @field_validator("status", mode="before")
    @classmethod
    def validate_status(cls, v: Any) -> str:
        return _validate_question_status(v)


class DuplicateCheckRequest(BaseModel):
    """Request body for evaluating candidate question duplicate similarity."""

    section: str = ""
    subtopic: str = ""
    question_stem: str
    options: list[OptionChoice] | list[dict[str, Any]] = Field(default_factory=list, max_length=10)


def determine_question_status(
    score: float | int | None,
    is_in_progress_batch: bool = False,
) -> str:
    """
    Determines question lifecycle status based on psychometric score thresholds.

    If is_in_progress_batch is True, active questions are withheld in 'batch_only'
    (if score > BATCH_PASSING_SCORE_THRESHOLD) or 'below_threshold' until batch completion.
    If is_in_progress_batch is False, scores > PASSING_SCORE_THRESHOLD become 'ai_validated'.
    """
    s = score or 0
    if is_in_progress_batch:
        if s > config.BATCH_PASSING_SCORE_THRESHOLD:
            return "batch_only"
        return "below_threshold"

    if s > config.PASSING_SCORE_THRESHOLD:
        return "ai_validated"
    if s > config.BATCH_PASSING_SCORE_THRESHOLD:
        return "batch_only"
    return "below_threshold"
