"""Lightweight, zero-dependency Prometheus/OpenMetrics exposition engine for MCAT Question Bank Generator."""

from __future__ import annotations

import logging
import re
import threading
from collections import defaultdict

from app.core.config import config
from app.db.session import check_db_health
from app.repositories.question_repository import get_repository_metrics
from app.services.batch_concurrency import get_active_batch_metrics

logger = logging.getLogger(__name__)

# UUID pattern for path normalization to prevent high-cardinality time-series explosions
_UUID_RE = re.compile(
    r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}"
)
_NUMERIC_ID_RE = re.compile(r"/\d+(?=/|$)")


def normalize_metric_path(path: str) -> str:
    """Normalizes dynamic URL parameters into generic tokens to keep label cardinality bounded."""
    cleaned = _UUID_RE.sub("{id}", path)
    cleaned = _NUMERIC_ID_RE.sub("/{id}", cleaned)
    # Strip trailing slash if present unless root
    if len(cleaned) > 1 and cleaned.endswith("/"):
        cleaned = cleaned[:-1]
    return cleaned


class TelemetryStore:
    """Thread-safe in-memory store for HTTP request counters and duration metrics."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        # (method, endpoint, status_code) -> count
        self._request_counts: dict[tuple[str, str, int], int] = defaultdict(int)
        # (method, endpoint) -> (sum_seconds, count)
        self._durations: dict[tuple[str, str], list[float]] = defaultdict(lambda: [0.0, 0.0])

    def record_request(
        self, method: str, raw_path: str, status_code: int, duration_sec: float
    ) -> None:
        endpoint = normalize_metric_path(raw_path)
        with self._lock:
            self._request_counts[(method.upper(), endpoint, status_code)] += 1
            entry = self._durations[(method.upper(), endpoint)]
            entry[0] += duration_sec
            entry[1] += 1

    def get_snapshot(
        self,
    ) -> tuple[dict[tuple[str, str, int], int], dict[tuple[str, str], tuple[float, int]]]:
        with self._lock:
            counts = dict(self._request_counts)
            durations = {k: (v[0], int(v[1])) for k, v in self._durations.items()}
        return counts, durations

    def reset(self) -> None:
        with self._lock:
            self._request_counts.clear()
            self._durations.clear()


telemetry_store = TelemetryStore()


async def render_prometheus_metrics() -> str:
    """Renders real-time system, database, batch concurrency, and HTTP telemetry in Prometheus format."""
    lines: list[str] = [
        "# HELP mcat_up Operational status of the MCAT Question Bank application (1 = up).",
        "# TYPE mcat_up gauge",
        "mcat_up 1",
    ]

    # Database connectivity probe
    db_connected = False
    try:
        health_status = await check_db_health()
        db_connected = bool(health_status.get("connected"))
    except Exception as exc:
        logger.debug("Database probe error during metrics collection: %s", exc)

    lines.extend(
        [
            "# HELP mcat_database_connected Database connection state (1 = connected, 0 = disconnected).",
            "# TYPE mcat_database_connected gauge",
            f"mcat_database_connected {1 if db_connected else 0}",
            "# HELP mcat_offline_mode Application offline mode configuration flag.",
            "# TYPE mcat_offline_mode gauge",
            f"mcat_offline_mode {1 if config.OFFLINE_MODE else 0}",
        ]
    )

    # Concurrency and worker pool telemetry
    batch_metrics = get_active_batch_metrics()
    lines.extend(
        [
            "# HELP mcat_batches_active Number of active running background generation batches.",
            "# TYPE mcat_batches_active gauge",
            f"mcat_batches_active {batch_metrics.get('active_running_batches', 0)}",
            "# HELP mcat_worker_jobs_active Number of currently executing worker jobs.",
            "# TYPE mcat_worker_jobs_active gauge",
            f"mcat_worker_jobs_active {batch_metrics.get('active_worker_jobs', 0)}",
            "# HELP mcat_global_max_concurrent_jobs Maximum permitted parallel background jobs.",
            "# TYPE mcat_global_max_concurrent_jobs gauge",
            f"mcat_global_max_concurrent_jobs {batch_metrics.get('global_max_concurrent_jobs', config.GLOBAL_MAX_CONCURRENT_JOBS)}",
            "# HELP mcat_global_max_concurrent_llm_calls Maximum permitted simultaneous LLM inference calls.",
            "# TYPE mcat_global_max_concurrent_llm_calls gauge",
            f"mcat_global_max_concurrent_llm_calls {batch_metrics.get('global_max_concurrent_llm_calls', config.GLOBAL_MAX_CONCURRENT_LLM_CALLS)}",
        ]
    )

    # Repository questions and token spend telemetry
    if db_connected:
        try:
            repo_metrics = await get_repository_metrics()
            lines.extend(
                [
                    "# HELP mcat_questions_total Total question count categorized by repository status.",
                    "# TYPE mcat_questions_total gauge",
                    f'mcat_questions_total{{status="total"}} {repo_metrics.get("total_count", 0)}',
                ]
            )

            # Status breakdown
            for st in ("in_bank", "ai_validated", "batch_only", "discarded"):
                try:
                    st_metrics = await get_repository_metrics(status=st)
                    lines.append(
                        f'mcat_questions_total{{status="{st}"}} {st_metrics.get("total_count", 0)}'
                    )
                except Exception:
                    pass

            lines.extend(
                [
                    "# HELP mcat_tokens_consumed_total Total tokens consumed across all agent generations.",
                    "# TYPE mcat_tokens_consumed_total counter",
                    f"mcat_tokens_consumed_total {repo_metrics.get('total_tokens', 0)}",
                    "# HELP mcat_inference_cost_usd_total Cumulative LLM and image inference spend in USD.",
                    "# TYPE mcat_inference_cost_usd_total counter",
                    f"mcat_inference_cost_usd_total {repo_metrics.get('total_cost_usd', 0.0):.6f}",
                ]
            )
        except Exception as exc:
            logger.debug("Repository metrics extraction error: %s", exc)

    # HTTP request traffic and latencies
    counts, durations = telemetry_store.get_snapshot()

    lines.extend(
        [
            "# HELP mcat_http_requests_total Total number of HTTP requests processed by endpoint and status.",
            "# TYPE mcat_http_requests_total counter",
        ]
    )
    if counts:
        for (method, endpoint, status_code), count in sorted(counts.items()):
            lines.append(
                f'mcat_http_requests_total{{endpoint="{endpoint}",method="{method}",status="{status_code}"}} {count}'
            )
    else:
        lines.append("# mcat_http_requests_total (no requests recorded yet)")

    lines.extend(
        [
            "# HELP mcat_http_request_duration_seconds Total execution time spent processing HTTP requests in seconds.",
            "# TYPE mcat_http_request_duration_seconds summary",
        ]
    )
    if durations:
        for (method, endpoint), (total_time, req_count) in sorted(durations.items()):
            lines.append(
                f'mcat_http_request_duration_seconds_sum{{endpoint="{endpoint}",method="{method}"}} {total_time:.6f}'
            )
            lines.append(
                f'mcat_http_request_duration_seconds_count{{endpoint="{endpoint}",method="{method}"}} {req_count}'
            )
    else:
        lines.append("# mcat_http_request_duration_seconds (no requests recorded yet)")

    return "\n".join(lines) + "\n"
