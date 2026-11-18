"""
dedup_clustering.py - Disjoint-set graph clustering for batch duplicate grouping.
"""

from __future__ import annotations

import logging
from typing import Any

from app.core.config import config
from app.services.dedup_metrics import (
    DuplicateCluster,
    compute_question_similarity,
    compute_stem_similarity,
)

logger = logging.getLogger(__name__)


def cluster_questions(
    questions: list[dict[str, Any] | Any],
    threshold: float | None = None,
) -> list[DuplicateCluster]:
    """
    Groups questions into duplicate clusters using graph connected components.

    For each cluster with >= 2 items, identifies the leader question (highest final_score or manual override)
    and list of redundant sibling duplicates with similarity metrics.
    """
    threshold = config.DUPLICATE_HARD_THRESHOLD if threshold is None else threshold
    n = len(questions)
    if n < 2:
        return []

    parent = list(range(n))

    def find(i: int) -> int:
        path = []
        curr = i
        while parent[curr] != curr:
            path.append(curr)
            curr = parent[curr]
        for node in path:
            parent[node] = curr
        return curr

    def union(i: int, j: int) -> None:
        root_i = find(i)
        root_j = find(j)
        if root_i != root_j:
            parent[root_i] = root_j

    pairwise_sims: dict[tuple[int, int], tuple[float, str]] = {}

    for i in range(n):
        for j in range(i + 1, n):
            score, reason = compute_question_similarity(questions[i], questions[j])
            stem_sim = compute_stem_similarity(
                questions[i].get("question_stem")
                if isinstance(questions[i], dict)
                else getattr(questions[i], "question_stem", ""),
                questions[j].get("question_stem")
                if isinstance(questions[j], dict)
                else getattr(questions[j], "question_stem", ""),
            )
            effective_sim = max(score, stem_sim)
            if effective_sim >= threshold:
                union(i, j)
                pairwise_sims[(min(i, j), max(i, j))] = (round(effective_sim, 4), reason)

    # Collect grouped indices
    groups: dict[int, list[int]] = {}
    for idx in range(n):
        root = find(idx)
        groups.setdefault(root, []).append(idx)

    clusters: list[dict[str, Any]] = []
    cluster_num = 1

    for members in groups.values():
        if len(members) < 2:
            continue

        # Sort members by final_score descending (best first)
        def _get_score(q_idx: int) -> float:
            q = questions[q_idx]
            s = q.get("final_score") if isinstance(q, dict) else getattr(q, "final_score", 0)
            return float(s) if s is not None else 0.0

        sorted_members = sorted(members, key=_get_score, reverse=True)
        leader_idx = sorted_members[0]
        leader_q = questions[leader_idx]
        leader_dict = leader_q if isinstance(leader_q, dict) else leader_q.model_dump()

        duplicates = []
        for dup_idx in sorted_members[1:]:
            dup_q = questions[dup_idx]
            dup_dict = dup_q if isinstance(dup_q, dict) else dup_q.model_dump()
            pair_key = (min(leader_idx, dup_idx), max(leader_idx, dup_idx))
            sim_score, sim_reason = pairwise_sims.get(pair_key, (0.0, "Cluster collision"))
            if sim_score == 0.0:
                # Calculate directly against leader if not directly paired
                sim_score, sim_reason = compute_question_similarity(leader_q, dup_q)
            duplicates.append(
                {
                    "question": dup_dict,
                    "similarity_score": round(sim_score, 4),
                    "reason": sim_reason,
                }
            )

        clusters.append(
            {
                "cluster_id": f"cluster-{cluster_num}",
                "size": len(members),
                "leader_question": leader_dict,
                "duplicates": duplicates,
                "highest_similarity": max(d["similarity_score"] for d in duplicates)
                if duplicates
                else 1.0,
            }
        )
        cluster_num += 1

    # Sort clusters by size descending, then highest_similarity descending
    clusters.sort(key=lambda c: (c["size"], c["highest_similarity"]), reverse=True)
    return clusters
