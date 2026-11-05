"""Dedup pruning keeps verdicts, big pools leave the loop, litellm stays lazy."""

import random
import subprocess
import sys
from pathlib import Path

from app.services import deduplication as dd
from app.workflow import engine_helpers as eh

BACKEND = Path(__file__).resolve().parents[1]
VOCAB = [
    "enzyme",
    "kinetics",
    "substrate",
    "inhibitor",
    "binding",
    "affinity",
    "membrane",
    "potential",
    "sodium",
    "channel",
    "neuron",
    "synapse",
    "glycolysis",
    "pyruvate",
    "oxidation",
    "entropy",
    "enthalpy",
    "equilibrium",
    "acid",
    "base",
    "buffer",
    "titration",
    "reaction",
    "mechanism",
    "orbital",
    "hybridization",
    "resonance",
    "carbonyl",
    "nucleophile",
    "elimination",
]


def _stem(rng, n):
    return "Which of the following " + " ".join(rng.choice(VOCAB) for _ in range(n)) + "?"


def _question(rng, i, base=None):
    stem = base if base is not None else _stem(rng, rng.randint(6, 24))
    return {
        "id": f"q{i}",
        "question_stem": stem,
        "options": [{"id": c, "text": " ".join(rng.sample(VOCAB, 3))} for c in "ABCD"],
    }


def _exact_evaluate(candidate, pool, threshold, soft):
    """Reference implementation: same loop, no pruning."""
    best, best_ref, reason = 0.0, None, ""
    for ref in pool:
        score, why = dd.compute_question_similarity(candidate, ref)
        if score > best:
            best, best_ref, reason = score, ref, why
    return best, best_ref, reason, best >= threshold, best >= soft and best < threshold


def test_pruned_dedup_matches_exact_verdicts():
    rng = random.Random(1234)
    for _ in range(40):
        pool = [_question(rng, i) for i in range(30)]
        # plant near-duplicates of a pool member so flagged cases occur too
        src = rng.choice(pool)["question_stem"].split()
        if rng.random() < 0.7 and len(src) > 6:
            src[rng.randrange(len(src))] = rng.choice(VOCAB)
            pool.append(_question(rng, 99, base=" ".join(src)))
        cand = _question(rng, 500, base=" ".join(src) if rng.random() < 0.5 else None)
        got = dd.evaluate_duplicate(cand, pool, threshold=0.75, soft_threshold=0.60)
        best, ref, _, is_dup, is_soft = _exact_evaluate(cand, pool, 0.75, 0.60)
        assert got.is_duplicate == is_dup
        assert got.is_soft_warning == is_soft
        if is_dup or is_soft:
            assert got.similarity_score == best
            assert got.matched_question_id == ref["id"]


def test_prune_default_is_exact():
    a, b = "What is the enzyme substrate binding?", "Which neuron membrane potential applies?"
    assert dd.compute_stem_similarity(a, b) == dd.compute_stem_similarity(a, b, prune=False)
    assert dd.compute_stem_similarity(a, b, prune=True) >= dd.compute_stem_similarity(a, b) - 1e-4


async def test_large_pool_scored_in_thread(monkeypatch):
    rng = random.Random(7)
    pool = [_question(rng, i) for i in range(eh._DEDUP_THREAD_POOL_MIN + 5)]
    cand = _question(rng, 900)
    calls = []

    async def fake_to_thread(fn, *args, **kwargs):
        calls.append(fn)
        return fn(*args, **kwargs)

    monkeypatch.setattr(eh.asyncio, "to_thread", fake_to_thread)
    big = await eh._evaluate_duplicate_async(cand, pool, threshold=0.75, soft_threshold=0.6)
    small = await eh._evaluate_duplicate_async(cand, pool[:5], threshold=0.75, soft_threshold=0.6)
    assert len(calls) == 1
    assert big.similarity_score == dd.evaluate_duplicate(cand, pool, 0.75, 0.6).similarity_score
    assert small.is_duplicate is False


async def test_clear_in_flight_batch():
    await eh.register_in_flight_draft("b-x", {"question_stem": "s"}, 0)
    await eh.register_in_flight_draft("b-x", {"question_stem": "t"}, 1)
    assert await eh.get_in_flight_drafts("b-x", 5)
    await eh.clear_in_flight_batch("b-x")
    assert await eh.get_in_flight_drafts("b-x", 5) == []
    await eh.clear_in_flight_batch(None)  # no-op


def test_litellm_is_not_imported_until_used():
    code = (
        "import sys, app.agents.base as b, app.main;"
        "assert 'litellm' not in sys.modules, 'eager litellm import';"
        "assert b.litellm is sys.modules['litellm']"
    )
    out = subprocess.run(
        [sys.executable, "-c", code],
        cwd=BACKEND,
        env={"PYTHONPATH": str(BACKEND), "OFFLINE_MODE": "true", "PATH": ""},
        capture_output=True,
        text=True,
    )
    assert out.returncode == 0, out.stderr
