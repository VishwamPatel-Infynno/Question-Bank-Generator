"""
scripts/benchmark_concurrency.py - In-Process ASGI High-Concurrency Stress Benchmark.

Simulates concurrent user load (20, 50, and 100 concurrent workers) against FastAPI routes,
measuring throughput (req/sec), latency percentiles (p50, p95, p99), error rates,
and connection pool behavior under heavy load.
"""

from __future__ import annotations

import asyncio
import statistics
import time
import uuid
from typing import Any

from app.db.session import init_db
from app.main import app
from app.repositories import (
    delete_batch,
    delete_passage,
    hard_delete_questions_batch,
    save_batch,
    save_passage,
    save_questions_batch,
)
from app.schemas import (
    BatchStatus,
    GenerationBatch,
    OptionChoice,
    Passage,
    Question,
)
from httpx import ASGITransport, AsyncClient


def percentile(data: list[float], pct: float) -> float:
    """Computes the p-th percentile from a sorted list of numbers."""
    if not data:
        return 0.0
    k = (len(data) - 1) * (pct / 100.0)
    f = int(k)
    c = min(f + 1, len(data) - 1)
    d0 = data[f] * (c - k)
    d1 = data[c] * (k - f)
    return d0 + d1


async def setup_benchmark_fixtures(uid: str) -> dict[str, Any]:
    """Inserts an isolated test batch, passage, and set of questions for benchmarking."""
    batch_id = f"batch-bench-{uid}"
    passage_id = f"passage-bench-{uid}"

    batch = GenerationBatch(
        id=batch_id,
        section="bio_biochem",
        subtopic="Enzyme Kinetics",
        difficulty="medium",
        passage_mode="passage_based",
        target_count=10,
        actual_count=10,
        total_jobs=2,
        completed_jobs=2,
        status=BatchStatus.COMPLETED,
    )
    await save_batch(batch)

    passage = Passage(
        id=passage_id,
        section="bio_biochem",
        title=f"Benchmark Enzyme Stimulus {uid}",
        subtopic="Enzyme Kinetics",
        text="Enzymes accelerate chemical reactions by lowering activation energy barriers.",
        word_count=10,
    )
    await save_passage(passage)

    questions = []
    for i in range(10):
        q = Question(
            id=f"q-bench-{uid}-{i:02d}",
            batch_id=batch_id,
            passage_id=passage_id,
            section="bio_biochem",
            section_label="Biological and Biochemical Foundations",
            subtopic="Enzyme Kinetics",
            difficulty="medium",
            stimulus_text=passage.text,
            question_stem=f"Benchmark question stem {i}: Which factor affects reaction rate?",
            options=[
                OptionChoice(id="A", text="Enzyme concentration"),
                OptionChoice(id="B", text="Substrate concentration"),
                OptionChoice(id="C", text="Temperature and pH"),
                OptionChoice(id="D", text="All of the above factors"),
            ],
            correct_answer_id="D",
            explanation="All listed factors modulate enzymatic velocity.",
            final_score=94,
            status="in_bank",
            stage_outcomes={"heavy_audit_trace": "X" * 1000},
            iterations_history=[{"cycle": 1, "audit_trace": "Y" * 500}],
        )
        questions.append(q)

    await save_questions_batch(questions)
    return {
        "batch_id": batch_id,
        "passage_id": passage_id,
        "question_ids": [q.id for q in questions],
    }


async def teardown_benchmark_fixtures(fixtures: dict[str, Any]) -> None:
    """Cleans up all benchmark test records."""
    if fixtures.get("question_ids"):
        await hard_delete_questions_batch(fixtures["question_ids"])
    if fixtures.get("passage_id"):
        await delete_passage(fixtures["passage_id"])
    if fixtures.get("batch_id"):
        await delete_batch(fixtures["batch_id"])


async def run_tier(
    client: AsyncClient,
    routes: list[str],
    concurrency: int,
    total_requests: int,
) -> dict[str, Any]:
    """Runs a benchmark tier with a fixed concurrency cap and measures response times."""
    semaphore = asyncio.Semaphore(concurrency)
    latencies: list[float] = []
    status_counts: dict[int, int] = {}
    errors: list[str] = []

    async def worker(route: str):
        async with semaphore:
            start_t = time.perf_counter()
            try:
                res = await client.get(route)
                duration_ms = (time.perf_counter() - start_t) * 1000.0
                latencies.append(duration_ms)
                status_counts[res.status_code] = status_counts.get(res.status_code, 0) + 1
            except Exception as exc:
                duration_ms = (time.perf_counter() - start_t) * 1000.0
                latencies.append(duration_ms)
                errors.append(str(exc))

    tasks = []
    for i in range(total_requests):
        route = routes[i % len(routes)]
        tasks.append(worker(route))

    wall_start = time.perf_counter()
    await asyncio.gather(*tasks)
    total_time = time.perf_counter() - wall_start

    sorted_latencies = sorted(latencies)
    throughput = len(latencies) / total_time if total_time > 0 else 0

    return {
        "concurrency": concurrency,
        "total_requests": total_requests,
        "total_time_sec": total_time,
        "throughput_req_sec": throughput,
        "min_ms": sorted_latencies[0] if sorted_latencies else 0,
        "mean_ms": statistics.mean(sorted_latencies) if sorted_latencies else 0,
        "p50_ms": percentile(sorted_latencies, 50),
        "p90_ms": percentile(sorted_latencies, 90),
        "p95_ms": percentile(sorted_latencies, 95),
        "p99_ms": percentile(sorted_latencies, 99),
        "max_ms": sorted_latencies[-1] if sorted_latencies else 0,
        "status_counts": status_counts,
        "error_count": len(errors),
        "errors": errors[:5],
    }


async def main() -> None:
    print("=" * 80)
    print("MCAT QUESTION BANK GENERATOR - FULL-STACK ASGI CONCURRENCY BENCHMARK")
    print("=" * 80)

    # 1. Initialize DB connection
    print("\n[1/4] Probing PostgreSQL connection and verifying schema...")
    db_ready = await init_db()
    if not db_ready:
        print("ERROR: Database not reachable. Aborting benchmark.")
        return

    # 2. Setup isolated benchmark fixtures
    uid = uuid.uuid4().hex[:8]
    print(f"[2/4] Seeding isolated benchmark test fixtures (ID: {uid})...")
    fixtures = await setup_benchmark_fixtures(uid)

    batch_id = fixtures["batch_id"]
    routes = [
        f"/api/batches/{batch_id}?slim=true",
        "/api/questions?slim=true&status=in_bank&limit=20",
        "/api/passages?limit=20",
        "/metrics",
    ]

    print("\n[3/4] Benchmarking targets across routes:")
    for r in routes:
        print(f"  • {r}")

    tiers = [
        {"concurrency": 20, "requests": 100, "label": "Tier 1: Moderate Concurrency (20 workers)"},
        {"concurrency": 50, "requests": 250, "label": "Tier 2: High Concurrency (50 workers)"},
        {"concurrency": 100, "requests": 500, "label": "Tier 3: Stress Concurrency (100 workers)"},
    ]

    tier_results = []
    transport = ASGITransport(app=app)

    try:
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            # Warm up JIT / connection pool
            print("\n  Warming up database connection pool (10 requests)...")
            for _ in range(10):
                await client.get(routes[0])

            print("\n[4/4] Executing multi-tier concurrency load curve...")
            for t in tiers:
                print(f"\n>>> Running {t['label']} ({t['requests']} requests)...")
                res = await run_tier(
                    client=client,
                    routes=routes,
                    concurrency=t["concurrency"],
                    total_requests=t["requests"],
                )
                tier_results.append(res)
                print(
                    f"    Throughput: {res['throughput_req_sec']:.1f} req/s | "
                    f"p50: {res['p50_ms']:.2f}ms | p95: {res['p95_ms']:.2f}ms | p99: {res['p99_ms']:.2f}ms | "
                    f"Success: {res['status_counts'].get(200, 0)}/{res['total_requests']} (Errors: {res['error_count']})"
                )

        # Print structured summary table
        print("\n" + "=" * 80)
        print("CONCURRENCY BENCHMARK SUMMARY RESULTS")
        print("=" * 80)
        header = f"{'Tier':<25} | {'Conc':<5} | {'Reqs':<5} | {'Throughput':<12} | {'p50 (ms)':<9} | {'p95 (ms)':<9} | {'p99 (ms)':<9} | {'Errors'}"
        print(header)
        print("-" * len(header))
        for r in tier_results:
            tier_name = f"Tier ({r['concurrency']} clients)"
            line = (
                f"{tier_name:<25} | {r['concurrency']:<5} | {r['total_requests']:<5} | "
                f"{r['throughput_req_sec']:>7.1f} req/s | {r['p50_ms']:>8.2f}  | "
                f"{r['p95_ms']:>8.2f}  | {r['p99_ms']:>8.2f}  | {r['error_count']}"
            )
            print(line)
        print("=" * 80)

    finally:
        print("\nTeardown: Cleaning up isolated benchmark fixtures...")
        await teardown_benchmark_fixtures(fixtures)
        print("Teardown completed successfully.\n")


if __name__ == "__main__":
    asyncio.run(main())
