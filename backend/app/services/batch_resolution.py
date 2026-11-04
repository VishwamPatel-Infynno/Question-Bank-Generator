"""
batch_resolution.py - Deduplication clustering, excess trimming, and deficit calculations.

Contains pure algorithmic routines for identifying duplicate questions across batches,
partitioning questions per set/job, trimming excess questions to guarantee target counts,
and calculating in-set replenishment shortfalls.
"""

import logging
from typing import Any

from app.schemas import GenerationJob, Question
from app.services.deduplication import cluster_questions

logger = logging.getLogger(__name__)


def find_cluster_duplicates(
    active_questions: list[Question],
    threshold: float = 0.75,
) -> tuple[list[dict[str, Any]], list[str]]:
    """
    Identifies semantic duplicate clusters among active questions.
    Returns: (clusters, duplicate_ids_to_purge)
    """
    q_dumps = [q.model_dump() for q in active_questions]
    clusters = cluster_questions(q_dumps, threshold=threshold)
    duplicate_ids_to_purge: list[str] = []

    if clusters:
        for c in clusters:
            leader_id = c["leader_question"]["id"]
            for d in c["duplicates"]:
                dup_id = d["question"]["id"]
                if dup_id != leader_id:
                    duplicate_ids_to_purge.append(dup_id)

    return clusters, duplicate_ids_to_purge


def partition_questions_by_job(
    active_questions: list[Question],
) -> dict[str, list[Question]]:
    """Groups active questions by their job_id or run_id."""
    qs_by_job: dict[str, list[Question]] = {}
    for q in active_questions:
        j_key = q.job_id or q.run_id
        if j_key:
            qs_by_job.setdefault(j_key, []).append(q)
    return qs_by_job


def identify_excess_questions_per_job(
    jobs: list[GenerationJob],
    qs_by_job: dict[str, list[Question]],
) -> tuple[list[str], dict[str, int]]:
    """
    Enforces exact target count per job by identifying excess question IDs to purge
    (retaining highest-scoring questions first).
    Returns: (excess_ids_to_delete, updated_actual_counts_by_job)
    """
    excess_ids: list[str] = []
    actual_counts: dict[str, int] = {}

    for job in jobs:
        job_qs = qs_by_job.get(job.id, [])
        if len(job_qs) > job.target_count:
            job_qs.sort(key=lambda q: q.final_score or 0, reverse=True)
            excess_to_delete = [q.id for q in job_qs[job.target_count :]]
            excess_ids.extend(excess_to_delete)
            actual_counts[job.id] = job.target_count
        else:
            actual_counts[job.id] = len(job_qs)

    return excess_ids, actual_counts


def identify_batch_buffer_excess(
    valid_active: list[Question],
    target_count: int,
) -> list[str]:
    """
    If remaining active questions exceed target count, returns IDs of the lowest-scoring
    excess questions that should be archived/discarded.
    """
    if len(valid_active) <= target_count:
        return []
    sorted_active = sorted(valid_active, key=lambda q: q.final_score or 0, reverse=True)
    return [q.id for q in sorted_active[target_count:]]


def compute_jobs_with_deficits(
    jobs: list[GenerationJob],
    qs_by_job: dict[str, list[Question]],
    total_deficit: int = 0,
) -> list[tuple[GenerationJob, int]]:
    """
    Identifies jobs that have question shortfalls below their target count.
    If no specific job has a shortfall below target_count, allocates the deficit
    to any incomplete jobs.
    """
    jobs_to_refill: list[tuple[GenerationJob, int]] = []
    sorted_jobs = sorted(jobs, key=lambda j: j.job_number)

    for job in sorted_jobs:
        job_active_count = len(qs_by_job.get(job.id, []))
        job_deficit = max(0, job.target_count - job_active_count)
        if job_deficit > 0:
            jobs_to_refill.append((job, job_deficit))

    if not jobs_to_refill and total_deficit > 0:
        for job in sorted_jobs:
            if job.status != "completed":
                jobs_to_refill.append((job, min(total_deficit, job.target_count)))
                break

    return jobs_to_refill

