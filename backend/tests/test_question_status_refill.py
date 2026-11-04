import pytest
from app.schemas import (
    QuestionStatus,
    SingleStatusUpdateRequest,
    StatusUpdateRequest,
    determine_question_status,
    is_question_active,
)
from pydantic import ValidationError


def test_question_status_enum_values():
    """Validates that QuestionStatus members correspond to exact database constraint tokens."""
    assert QuestionStatus.IN_BANK == "in_bank"
    assert QuestionStatus.AI_VALIDATED == "ai_validated"
    assert QuestionStatus.BATCH_ONLY == "batch_only"
    assert QuestionStatus.DISCARDED == "discarded"
    assert QuestionStatus.BELOW_THRESHOLD == "below_threshold"
    assert QuestionStatus.APPROVED == "approved"
    assert QuestionStatus.REJECTED_BELOW_THRESHOLD == "rejected_below_threshold"
    assert QuestionStatus.ERROR == "error"
    assert QuestionStatus.FAILED == "failed"


def test_is_question_active_helper():
    """Ensures active statuses are recognized and discarded/error statuses evaluate to False."""
    assert is_question_active(QuestionStatus.IN_BANK) is True
    assert is_question_active("in_bank") is True
    assert is_question_active(QuestionStatus.AI_VALIDATED) is True
    assert is_question_active(QuestionStatus.BATCH_ONLY) is True
    assert is_question_active(QuestionStatus.APPROVED) is True

    # Inactive / archived statuses
    assert is_question_active(QuestionStatus.DISCARDED) is False
    assert is_question_active("discarded") is False
    assert is_question_active(QuestionStatus.BELOW_THRESHOLD) is False
    assert is_question_active(QuestionStatus.REJECTED_BELOW_THRESHOLD) is False
    assert is_question_active(QuestionStatus.ERROR) is False
    assert is_question_active(QuestionStatus.FAILED) is False
    assert is_question_active(None) is False
    assert is_question_active("") is False


def test_status_update_requests_validation():
    """Ensures StatusUpdateRequest and SingleStatusUpdateRequest accept valid statuses and reject invalid ones."""
    req = StatusUpdateRequest(ids=["q1", "q2"], status="in_bank")
    assert req.status == "in_bank"

    req_enum = StatusUpdateRequest(ids=["q1"], status=QuestionStatus.DISCARDED)
    assert req_enum.status == "discarded"

    single_req = SingleStatusUpdateRequest(status="ai_validated")
    assert single_req.status == "ai_validated"

    with pytest.raises(ValidationError):
        SingleStatusUpdateRequest(status="invalid_nonexistent_status")


def test_batch_refill_deficit_calculation_with_discarded_questions():
    """
    Verifies that when a batch has archived/discarded duplicate questions,
    is_question_active accurately discounts them so the refill deficit is positive.
    """

    class MockQuestion:
        def __init__(self, q_id: str, status: str):
            self.id = q_id
            self.status = status

    target_count = 50
    # Simulate a batch of 50 questions where 4 were marked discarded as duplicates
    questions = [MockQuestion(f"q_{i}", "in_bank") for i in range(46)] + [
        MockQuestion(f"dup_{i}", "discarded") for i in range(4)
    ]

    # Old buggy logic: sum(1 for q in questions if q.status != "rejected") -> evaluated to 50! Deficit was 0!
    old_active_count = sum(1 for q in questions if q.status != "rejected")
    old_deficit = max(0, target_count - old_active_count)
    assert old_active_count == 50
    assert old_deficit == 0  # Bug reproduction: would not refill!

    # New corrected logic using is_question_active
    active_count = sum(1 for q in questions if is_question_active(q.status))
    deficit = max(0, target_count - active_count)
    assert active_count == 46
    assert deficit == 4  # Correct: refills the 4 discarded slots!


def test_determine_question_status():
    """
    Validates determine_question_status across boundary conditions:
    - Standalone runs: > 90 -> 'ai_validated', 86-90 -> 'batch_only', <= 85 -> 'below_threshold'
    - In-progress batches: > 85 -> 'batch_only' (withheld), <= 85 -> 'below_threshold'
    """
    # Standalone / completed runs (is_in_progress_batch=False)
    assert determine_question_status(95) == "ai_validated"
    assert determine_question_status(91) == "ai_validated"
    assert determine_question_status(90) == "batch_only"
    assert determine_question_status(88) == "batch_only"
    assert determine_question_status(85) == "below_threshold"
    assert determine_question_status(70) == "below_threshold"
    assert determine_question_status(None) == "below_threshold"

    # In-progress batch runs (is_in_progress_batch=True)
    assert determine_question_status(95, is_in_progress_batch=True) == "batch_only"
    assert determine_question_status(90, is_in_progress_batch=True) == "batch_only"
    assert determine_question_status(86, is_in_progress_batch=True) == "batch_only"
    assert determine_question_status(85, is_in_progress_batch=True) == "below_threshold"
    assert determine_question_status(50, is_in_progress_batch=True) == "below_threshold"
    assert determine_question_status(None, is_in_progress_batch=True) == "below_threshold"
