"""Regression tests for the round-6 backend bug fixes."""

import pathlib
import uuid
from types import SimpleNamespace

import pytest
from app.agents import base, image_generator
from app.agents.base import _usage_from_response, calculate_token_cost
from app.core.config import config
from app.repositories import (
    get_batch_by_id,
    reconcile_interrupted_batches,
    refresh_batch_aggregates,
    save_batch,
    save_job,
    save_question,
)
from app.schemas import GenerationBatch, GenerationJob, TokenUsage
from app.services import batch_concurrency, deduplication
from app.services.batch_resolution import find_cluster_duplicates
from app.workflow import dedup_inflight
from app.workflow.engine import run_workflow_stream
from app.workflow.passage_prep import SharedPassageState, _prepare_shared_passage_and_visual
from factories import collect_events, make_draft, make_question, make_request, make_usage

# --- in-flight pool: one batch, several concurrent jobs -----------------------------------------


async def test_in_flight_pool_keeps_sibling_jobs_apart():
    batch = f"b-{uuid.uuid4()}"
    await dedup_inflight.register_in_flight_draft(batch, {"question_stem": "A"}, 0, job_id="job-a")
    await dedup_inflight.register_in_flight_draft(batch, {"question_stem": "B"}, 0, job_id="job-b")

    # Each job's worker 0 sees the other job's draft, never its own
    seen_by_a = await dedup_inflight.get_in_flight_drafts(batch, 0, job_id="job-a")
    assert [d["question_stem"] for d in seen_by_a] == ["B"]
    assert seen_by_a[0]["id"].startswith("in_flight_")

    # Job B finishing removes only its own entries
    await dedup_inflight.clear_in_flight_batch(batch, job_id="job-b")
    assert [d["question_stem"] for d in await dedup_inflight.get_in_flight_drafts(batch, 9)] == [
        "A"
    ]
    await dedup_inflight.remove_in_flight_draft(batch, 0, job_id="job-a")
    assert await dedup_inflight.get_in_flight_drafts(batch, 9) == []
    assert batch not in dedup_inflight._IN_FLIGHT_BATCH_STEMS


# --- thresholds follow the live config --------------------------------------------------------


def test_duplicate_thresholds_are_read_at_call_time(monkeypatch):
    a = make_draft().model_dump()
    b = dict(a, question_stem=a["question_stem"] + " Which statement is most accurate?")
    sim = deduplication.evaluate_duplicate(
        a, [b], threshold=0.0, soft_threshold=0.0
    ).similarity_score
    assert 0.05 < sim < 1.0

    monkeypatch.setattr(config, "DUPLICATE_HARD_THRESHOLD", sim + 0.01)
    monkeypatch.setattr(config, "DUPLICATE_SOFT_THRESHOLD", 0.0)
    assert not deduplication.evaluate_duplicate(a, [b]).is_duplicate
    assert deduplication.cluster_questions([a, b]) == []
    monkeypatch.setattr(config, "DUPLICATE_HARD_THRESHOLD", sim - 0.01)
    assert deduplication.evaluate_duplicate(a, [b]).is_duplicate
    clusters, purge = find_cluster_duplicates([make_question(**a), make_question(id="q2", **b)])
    assert len(clusters) == 1 and len(purge) == 1


# --- stored requests are bounded and forgotten on delete -------------------------------------


def test_stored_batch_requests_are_bounded_and_forgettable(monkeypatch):
    monkeypatch.setattr(
        batch_concurrency, "_batch_requests", type(batch_concurrency._batch_requests)()
    )
    monkeypatch.setattr(batch_concurrency, "MAX_STORED_BATCH_REQUESTS", 2)
    for i in range(3):
        batch_concurrency.store_batch_request(f"b{i}", make_request(api_key=f"k{i}"))
    assert batch_concurrency.get_stored_batch_request("b0") is None  # oldest evicted
    assert batch_concurrency.get_stored_batch_request("b2").api_key == "k2"
    batch_concurrency.forget_batch_request("b2")
    assert batch_concurrency.get_stored_batch_request("b2") is None
    batch_concurrency.forget_batch_request("missing")  # no-op


# --- passage prep streams its events and accounts the diagram -------------------------------


async def test_passage_prep_emits_start_before_the_call_and_bills_the_diagram():
    timeline: list[str] = []

    async def fake_passage(req):
        timeline.append("passage_llm_called")
        return "A dense passage about kinetics.", make_usage(100, 0.01), True, "a diagram"

    async def fake_image(draft, req):
        timeline.append("image_called")
        return (
            "https://img/x.png",
            None,
            "A diagram",
            {"agent": "Image Generator", "cost_usd": 0.02},
        )

    def make_event(event_type, agent_name, message, data=None, run_id=None):
        from app.schemas import WorkflowEvent

        return WorkflowEvent(
            run_id="r",
            batch_id="b",
            event_type=event_type,
            agent_name=agent_name,
            message=message,
            data=data or {},
        )

    state = SharedPassageState()
    async for evt in _prepare_shared_passage_and_visual(
        req=make_request(allow_ai_images=True),
        batch_id="b",
        shared_passage_id="p",
        shared_passage_text=None,
        is_single_passage_set=True,
        effective_passage_count=5,
        independent_count=0,
        total_qty=5,
        make_event=make_event,
        passage_generator_fn=fake_passage,
        image_generator_fn=fake_image,
        state=state,
    ):
        timeline.append(f"{evt.event_type}:{evt.agent_name}")

    assert timeline == [
        "agent_start:Passage Writer",
        "passage_llm_called",
        "agent_complete:Passage Writer",
        "agent_start:Diagram & Chart Maker",
        "image_called",
        "agent_complete:Diagram & Chart Maker",
    ]
    assert state.passage_text.startswith("A dense passage")
    assert state.image_url == "https://img/x.png"
    assert [u["agent"] for u in state.usage_breakdown] == ["Passage Writer", "Image Generator"]
    assert (
        round(sum(u["cost_usd"] for u in state.usage_breakdown), 6) == round(state.cost, 6) == 0.03
    )


async def test_image_generator_usage_uses_the_shared_agent_key(monkeypatch):
    monkeypatch.setattr(config, "ACTIVE_IMAGE_PROVIDER", "openai")
    monkeypatch.setattr(config, "OPENAI_API_KEY", "")
    _, _, _, usage = await image_generator.generate_image_stimulus(make_draft(), make_request())
    assert usage["agent"] == "Image Generator" and "agent_name" not in usage


# --- usage parsing: cache tokens on every path ------------------------------------------------


def test_usage_from_response_applies_cache_pricing_and_provider_totals():
    resp = SimpleNamespace(
        usage=SimpleNamespace(
            prompt_tokens=1000,
            completion_tokens=100,
            total_tokens=1100,
            cache_read_input_tokens=800,
            cache_creation_input_tokens=0,
        )
    )
    model = config.DEFAULT_TEXT_MODEL
    usage = _usage_from_response(resp, model, duration_ms=12)
    assert usage.total_tokens == 1100 and usage.duration_ms == 12 and usage.calls == 1
    assert usage.cost_usd == calculate_token_cost(
        prompt_tokens=1000, completion_tokens=100, model=model, cache_read_tokens=800
    )
    assert usage.cost_usd <= calculate_token_cost(
        prompt_tokens=1000, completion_tokens=100, model=model
    )


# --- one workflow_error per failed run --------------------------------------------------------


@pytest.fixture
def strict_no_keys(monkeypatch):
    """Real-credentials behaviour: conftest enables OFFLINE_MODE, which would mock the run."""
    monkeypatch.setattr(config, "OFFLINE_MODE", False)


async def test_failed_single_question_run_reports_one_workflow_error(strict_no_keys):
    # Independent mode: a passage set fails earlier, inside the shared-passage draft
    events = await collect_events(
        run_workflow_stream(make_request(passage_mode="independent", questions_to_generate=1))
    )
    kinds = [e["event_type"] for e in events]
    assert kinds.count("question_failed") == 1
    assert kinds.count("workflow_error") == 1
    error = next(e for e in events if e["event_type"] == "workflow_error")
    assert "API Key is required" in error["data"]["error"]
    assert "API Key is required" in error["message"]
    assert "cumulative_usage" in error["data"]


# --- patch_llm alone reaches the passage generator -------------------------------------------


async def test_patch_llm_intercepts_the_passage_generator(patch_llm):
    calls = []

    async def fake(prompt, system_prompt, **kwargs):
        calls.append(prompt)
        return "A passage written by the fake.", TokenUsage(
            prompt_tokens=1, completion_tokens=1, total_tokens=2
        )

    patch_llm(fake)
    from app.agents.generator import generate_passage_stimulus

    text, _usage, _, _ = await generate_passage_stimulus(make_request())
    assert calls and text == "A passage written by the fake."
    assert base.call_llm is fake


# --- database-backed: aggregates and reconcile ------------------------------------------------


@pytest.mark.requires_db
async def test_batch_aggregates_count_only_active_statuses():
    batch_id, job_id = str(uuid.uuid4()), str(uuid.uuid4())
    await save_batch(
        GenerationBatch(
            id=batch_id,
            section="chem_phys",
            subtopic="Kinetics",
            difficulty="medium",
            target_count=5,
            total_jobs=1,
            status="in_progress",
        )
    )
    await save_job(
        GenerationJob(id=job_id, batch_id=batch_id, job_number=1, status="running", target_count=5)
    )
    for i, status in enumerate(["batch_only", "ai_validated", "below_threshold", "discarded"]):
        await save_question(
            make_question(
                id=f"{batch_id}-{i}",
                batch_id=batch_id,
                job_id=job_id,
                status=status,
                question_stem=f"Stem {i} {uuid.uuid4()}",
            )
        )

    refreshed = await refresh_batch_aggregates(batch_id)
    assert refreshed.actual_count == 2


@pytest.mark.requires_db
async def test_reconcile_stops_pending_batches_too():
    batch_id = str(uuid.uuid4())
    await save_batch(
        GenerationBatch(
            id=batch_id,
            section="chem_phys",
            subtopic="Kinetics",
            difficulty="medium",
            target_count=5,
            status="pending",
        )
    )
    await reconcile_interrupted_batches()
    assert (await get_batch_by_id(batch_id)).status == "stopped"


# --- batch status state machine (pure) --------------------------------------------------------


@pytest.mark.parametrize(
    ("current", "counts", "allow_complete", "expected"),
    [
        # terminal and user-stopped statuses are preserved
        (
            "cancelled",
            {"completed_jobs": 5, "failed_jobs": 0, "active_jobs": 0, "actual_count": 50},
            True,
            "cancelled",
        ),
        (
            "stopped",
            {"completed_jobs": 5, "failed_jobs": 0, "active_jobs": 0, "actual_count": 50},
            True,
            "stopped",
        ),
        (
            "partially_completed",
            {"completed_jobs": 3, "failed_jobs": 0, "active_jobs": 0, "actual_count": 15},
            False,
            "partially_completed",
        ),
        # a partially completed batch with live jobs may still move on
        (
            "partially_completed",
            {"completed_jobs": 10, "failed_jobs": 0, "active_jobs": 1, "actual_count": 50},
            True,
            "completed",
        ),
        # every job ended and some failed
        (
            "in_progress",
            {"completed_jobs": 7, "failed_jobs": 3, "active_jobs": 0, "actual_count": 35},
            True,
            "partially_completed",
        ),
        (
            "in_progress",
            {"completed_jobs": 0, "failed_jobs": 10, "active_jobs": 0, "actual_count": 0},
            True,
            "failed",
        ),
        # target reached: completed only when the caller allows it
        (
            "in_progress",
            {"completed_jobs": 4, "failed_jobs": 0, "active_jobs": 6, "actual_count": 50},
            False,
            "in_progress",
        ),
        (
            "in_progress",
            {"completed_jobs": 4, "failed_jobs": 0, "active_jobs": 6, "actual_count": 50},
            True,
            "completed",
        ),
        # all jobs done but short of the target
        (
            "in_progress",
            {"completed_jobs": 10, "failed_jobs": 0, "active_jobs": 0, "actual_count": 40},
            True,
            "partially_completed",
        ),
        (
            "in_progress",
            {"completed_jobs": 10, "failed_jobs": 0, "active_jobs": 0, "actual_count": 40},
            False,
            "in_progress",
        ),
        # nothing running and the caller says the run is over: never left live
        (
            "in_progress",
            {"completed_jobs": 0, "failed_jobs": 0, "active_jobs": 0, "actual_count": 0},
            True,
            "cancelled",
        ),
        (
            "pending",
            {"completed_jobs": 0, "failed_jobs": 2, "active_jobs": 0, "actual_count": 0},
            True,
            "failed",
        ),
        (
            "in_progress",
            {"completed_jobs": 2, "failed_jobs": 0, "active_jobs": 0, "actual_count": 8},
            True,
            "partially_completed",
        ),
        # still running
        (
            "pending",
            {"completed_jobs": 1, "failed_jobs": 0, "active_jobs": 9, "actual_count": 5},
            False,
            "in_progress",
        ),
    ],
)
def test_next_batch_status(current, counts, allow_complete, expected):
    from app.repositories.batch_repository import _next_batch_status

    result = _next_batch_status(
        current, target_count=50, total_jobs=10, allow_complete=allow_complete, **counts
    )
    assert result == expected


def test_enum_value_and_is_cars_accept_members_and_strings():
    from app.schemas import MCATSection, enum_value, is_cars

    assert enum_value(MCATSection.CARS) == "cars"
    assert enum_value("psych_soc") == "psych_soc"
    assert enum_value(None) == "None"
    assert is_cars(MCATSection.CARS) and is_cars("CARS") and is_cars(" cars ")
    assert not is_cars(MCATSection.CHEM_PHYS) and not is_cars("critical_analysis")


def test_slot_attempts_follow_the_worker_retry_setting(monkeypatch):
    """The engine's attempts per slot are the configured retries plus the first draft."""
    from app.workflow import engine

    source = pathlib.Path(engine.__file__).read_text()
    assert "config.WORKFLOW_MAX_WORKER_RETRIES + 1" in source
    assert "MAX_SLOT_ATTEMPTS" not in source


# --- phase 6: shared helpers ------------------------------------------------------------------


def test_find_cluster_duplicates_honours_custom_leaders_and_cluster_filter():
    from app.services.batch_resolution import find_cluster_duplicates

    stem = "Which enzyme catalyses the rate-limiting step of glycolysis in hepatocytes?"
    a = make_question(id="qa", question_stem=stem, final_score=96)
    b = make_question(id="qb", question_stem=stem + " Choose the best answer.", final_score=80)
    other = make_question(id="qc", question_stem="Describe the sliding filament model of muscle.")

    clusters, purge = find_cluster_duplicates([a, b, other], threshold=0.6)
    assert len(clusters) == 1 and purge == ["qb"]  # the higher score leads

    _, purge = find_cluster_duplicates([a, b, other], threshold=0.6, custom_leader_ids=["qb"])
    assert purge == ["qa"]

    _, purge = find_cluster_duplicates([a, b, other], threshold=0.6, cluster_ids=["no-such"])
    assert purge == []


async def test_iter_sse_events_skips_noise_and_bad_json():
    from app.workflow.sse import iter_sse_events

    async def stream():
        for chunk in [
            ": keep-alive\n\n",
            'data: {"event_type": "a"}\n\n',
            "data: {broken\n\n",
            'data: {"event_type": "b"}\n\n',
        ]:
            yield chunk

    assert [e["event_type"] async for e in iter_sse_events(stream())] == ["a", "b"]


def test_image_usage_record_shape():
    from app.agents.image_generator import _image_usage

    usage = _image_usage(0.02, width=1024, height=1024, type="ai_generated_image")
    assert usage["agent"] == "Image Generator" and usage["cost_usd"] == 0.02
    assert usage["total_tokens"] == 0
    assert usage["details"] == {
        "provider": "infynno",
        "width": 1024,
        "height": 1024,
        "type": "ai_generated_image",
    }


def test_active_statuses_agree_between_python_and_sql_sets():
    from app.schemas import ACTIVE_QUESTION_STATUSES, QuestionStatus
    from app.schemas.question import is_question_active

    for status in QuestionStatus:
        assert is_question_active(status) == (status.value in ACTIVE_QUESTION_STATUSES)


def test_agent_usage_update_extends_the_breakdown_and_totals():
    from app.workflow.nodes import _record_agent_usage, agent_usage_entry

    usage = make_usage(30, 0.002)
    state = {"total_tokens": 10, "total_cost_usd": 0.001, "agent_usage_breakdown": [{"agent": "x"}]}
    update = _record_agent_usage(state, "Quality Reviewer", usage, iteration=2)
    assert update["total_tokens"] == 40 and update["total_cost_usd"] == 0.003
    assert update["total_prompt_tokens"] == 30
    assert [e["agent"] for e in update["agent_usage_breakdown"]] == ["x", "Quality Reviewer"]
    assert agent_usage_entry("Passage Writer", usage)["iteration"] == 1


def test_timestamp_migration_sql_covers_every_column():
    from app.db.init_db import _TIMESTAMP_COLUMNS, _timestamptz_migration_sql

    sql = _timestamptz_migration_sql()
    assert sql.startswith("DO $$") and sql.rstrip().endswith("END $$;")
    assert sql.count("IF EXISTS") == len(_TIMESTAMP_COLUMNS) == 9
    assert sql.count("SET DEFAULT NOW()") == sum(1 for _, _, now in _TIMESTAMP_COLUMNS if now)
    assert (
        "ALTER TABLE generation_jobs ALTER COLUMN completed_at TYPE TIMESTAMP WITH TIME ZONE" in sql
    )


async def test_public_runtime_fields_are_part_of_both_payloads(monkeypatch):
    from app.api.v1.config import get_runtime_settings, public_runtime_fields

    monkeypatch.setattr("app.api.v1.config.is_admin_request", lambda _request: False)
    masked = await get_runtime_settings(None)
    monkeypatch.setattr("app.api.v1.config.is_admin_request", lambda _request: True)
    admin = await get_runtime_settings(None)
    shared = public_runtime_fields()
    assert set(shared) <= set(masked) and set(shared) <= set(admin)
    assert "has_openai_key" in admin and "has_openai_key" not in masked
