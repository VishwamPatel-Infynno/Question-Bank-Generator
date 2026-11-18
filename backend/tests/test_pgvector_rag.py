"""
test_pgvector_rag.py - Unit tests for pgvector RAG, deterministic embeddings, and semantic search.

Covers:
- Deterministic unit vector normalized mathematical projections
- Cosine distance and similarity mathematical invariants
- Question and passage semantic embedding generation
- Vector-backed deduplication and semantic collision checks
- RAG exemplar and anti-collision context extraction
- API endpoints: semantic-search, rag-context, check-duplicate, backfill-embeddings
"""

from __future__ import annotations

import math

import pytest
from app.core.config import config
from app.main import app
from app.schemas import GenerationRequest, MCATSection
from app.services.deduplication import evaluate_duplicate_rag
from app.services.embeddings import (
    cosine_distance,
    cosine_similarity,
    deterministic_unit_vector,
    embed_passage,
    embed_question,
    embed_text,
)
from app.services.rag import (
    RAGExemplarContext,
    SimilarQuestionResult,
    find_similar_questions,
    hybrid_search_questions,
    retrieve_rag_exemplar_context,
)
from httpx import ASGITransport, AsyncClient

# ── 1. Deterministic Unit Vector Math Tests ────────────────────────────────────


def test_deterministic_unit_vector_dimension_and_norm():
    """Deterministic unit vector must produce exactly 1536 dimensions with L2 norm of 1.0."""
    vec = deterministic_unit_vector(
        "What is the primary role of phosphofructokinase-1 in glycolysis?"
    )
    assert len(vec) == config.EMBEDDING_DIMENSION
    assert len(vec) == 1536

    # Verify Euclidean norm ||v||_2 = 1.0
    l2_norm = math.sqrt(sum(x * x for x in vec))
    assert pytest.approx(l2_norm, abs=1e-5) == 1.0


def test_deterministic_unit_vector_idempotency_and_distinctness():
    """Identical input yields identical vector; distinct concepts yield distinct vectors."""
    text_a = "Enzyme kinetics: Michaelis-Menten constant Km and Vmax."
    text_b = "Enzyme kinetics: Michaelis-Menten constant Km and Vmax."
    text_c = "Sociological theory of symbolic interactionism and dramaturgical analysis."

    vec_a = deterministic_unit_vector(text_a)
    vec_b = deterministic_unit_vector(text_b)
    vec_c = deterministic_unit_vector(text_c)

    # Identical text produces bitwise identical vector
    assert vec_a == vec_b

    # Distinct concepts produce distinct vectors
    sim_ac = cosine_similarity(vec_a, vec_c)
    assert sim_ac < 0.35  # Orthogonal/low similarity projection


def test_cosine_similarity_and_distance_invariants():
    """Validates cosine similarity and distance mathematical properties."""
    v1 = [1.0, 0.0, 0.0]
    v2 = [1.0, 0.0, 0.0]
    v3 = [0.0, 1.0, 0.0]
    v4 = [-1.0, 0.0, 0.0]

    # Self similarity = 1.0, distance = 0.0
    assert pytest.approx(cosine_similarity(v1, v2), abs=1e-6) == 1.0
    assert pytest.approx(cosine_distance(v1, v2), abs=1e-6) == 0.0

    # Orthogonal vectors: similarity = 0.0, distance = 1.0
    assert pytest.approx(cosine_similarity(v1, v3), abs=1e-6) == 0.0
    assert pytest.approx(cosine_distance(v1, v3), abs=1e-6) == 1.0

    # Opposite vectors: similarity = -1.0, distance = 2.0
    assert pytest.approx(cosine_similarity(v1, v4), abs=1e-6) == -1.0
    assert pytest.approx(cosine_distance(v1, v4), abs=1e-6) == 2.0

    # Dimension mismatch returns safe fallback
    assert cosine_similarity([1.0], [1.0, 2.0]) == 0.0
    assert cosine_distance([1.0], [1.0, 2.0]) == 1.0


# ── 2. Embeddings Services Tests ──────────────────────────────────────────────


@pytest.mark.asyncio
async def test_embed_text_caching_and_empty():
    """embed_text caches results and handles empty strings gracefully."""
    empty_vec = await embed_text("")
    assert len(empty_vec) == 1536
    assert all(x == 0.0 for x in empty_vec)

    query = "Renal physiology and countercurrent multiplication."
    v1 = await embed_text(query)
    v2 = await embed_text(query)
    assert v1 == v2
    assert len(v1) == 1536


@pytest.mark.asyncio
async def test_embed_question_and_passage():
    """embed_question and embed_passage composite strings correctly."""
    q_data = {
        "section": "bio_biochem",
        "subtopic": "Enzymology",
        "question_stem": "How does competitive inhibition affect the apparent Km and Vmax?",
        "options": [
            {"id": "A", "text": "Increases Km without altering Vmax"},
            {"id": "B", "text": "Decreases Km and decreases Vmax"},
        ],
        "explanation": "A competitive inhibitor competes for the substrate binding pocket.",
    }
    q_vec = await embed_question(q_data)
    assert len(q_vec) == 1536
    assert pytest.approx(math.sqrt(sum(x * x for x in q_vec)), abs=1e-5) == 1.0

    p_data = {
        "topic": "Microbiology",
        "passage_text": "Gram-negative bacteria possess an outer membrane rich in LPS.",
    }
    p_vec = await embed_passage(p_data)
    assert len(p_vec) == 1536


# ── 3. RAG Semantic Search & Exemplar Retrieval Tests ─────────────────────────


@pytest.mark.asyncio
async def test_retrieve_rag_exemplar_context_structure():
    """retrieve_rag_exemplar_context returns structured exemplars and avoidance stems."""
    req = GenerationRequest(
        section=MCATSection.BIO_BIOCHEM,
        subtopic="Metabolic Pathways",
        thematic_angle="Glycolytic regulation",
    )

    rag_ctx = await retrieve_rag_exemplar_context(req, limit=3)
    assert isinstance(rag_ctx, RAGExemplarContext)
    assert isinstance(rag_ctx.exemplars, list)
    assert isinstance(rag_ctx.avoidance_stems, list)
    assert isinstance(rag_ctx.common_traps, list)
    assert isinstance(rag_ctx.prompt_context, str)

    # Dictionary serialization
    ctx_dict = rag_ctx.to_dict()
    assert "exemplars" in ctx_dict
    assert "prompt_context" in ctx_dict


@pytest.mark.asyncio
async def test_find_and_hybrid_search_questions():
    """find_similar_questions and hybrid_search_questions execute and return structured items."""
    query = "action potential depolarization voltage-gated sodium channels"

    results = await find_similar_questions(query, section="bio_biochem", limit=5)
    assert isinstance(results, list)
    for r in results:
        assert isinstance(r, SimilarQuestionResult)
        assert 0.0 <= r.similarity <= 1.0
        assert r.retrieval_method in ("vector", "pgvector_cosine")

    hybrid_results = await hybrid_search_questions(query, section="bio_biochem", limit=5)
    assert isinstance(hybrid_results, list)
    for hr in hybrid_results:
        assert isinstance(hr, SimilarQuestionResult)
        assert 0.0 <= hr.similarity <= 1.0


# ── 4. Deduplication with RAG Tests ───────────────────────────────────────────


@pytest.mark.asyncio
async def test_evaluate_duplicate_rag_identical_detection():
    """evaluate_duplicate_rag flags duplicate questions with high similarity."""
    candidate = {
        "section": "bio_biochem",
        "subtopic": "Enzyme Kinetics",
        "question_stem": "Which change occurs to Km and Vmax in competitive inhibition?",
        "options": [
            {"id": "A", "text": "Km increases, Vmax remains unchanged."},
            {"id": "B", "text": "Km decreases, Vmax increases."},
            {"id": "C", "text": "Km remains unchanged, Vmax decreases."},
            {"id": "D", "text": "Both Km and Vmax decrease."},
        ],
        "explanation": "Competitive inhibitors bind only to free enzyme, increasing apparent Km.",
    }

    ref_pool = [
        {
            "id": "ref-001",
            "section": "bio_biochem",
            "subtopic": "Enzyme Kinetics",
            "question_stem": "Which change occurs to Km and Vmax in competitive inhibition?",
            "options": [
                {"id": "A", "text": "Km increases, Vmax remains unchanged."},
                {"id": "B", "text": "Km decreases, Vmax increases."},
                {"id": "C", "text": "Km remains unchanged, Vmax decreases."},
                {"id": "D", "text": "Both Km and Vmax decrease."},
            ],
            "explanation": "Competitive inhibitors bind only to free enzyme.",
        }
    ]

    result = await evaluate_duplicate_rag(candidate, ref_pool, threshold=0.85)
    assert result.is_duplicate is True
    assert result.similarity_score >= 0.85
    assert result.matched_question_id == "ref-001"


# ── 5. API Endpoints Integration Tests ────────────────────────────────────────


@pytest.mark.asyncio
async def test_api_questions_semantic_search():
    """POST /api/questions/semantic-search performs semantic query."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Test vector-only search
        res = await client.post(
            "/api/questions/semantic-search",
            json={
                "query": "DNA replication Okazaki fragments DNA polymerase",
                "section": "bio_biochem",
                "limit": 5,
                "hybrid": False,
            },
        )
        assert res.status_code == 200
        data = res.json()
        assert data["success"] is True
        assert "count" in data
        assert "results" in data
        assert isinstance(data["results"], list)

        # Test hybrid search
        res_hybrid = await client.post(
            "/api/questions/semantic-search",
            json={
                "query": "DNA replication Okazaki fragments",
                "section": "bio_biochem",
                "limit": 5,
                "hybrid": True,
            },
        )
        assert res_hybrid.status_code == 200
        assert res_hybrid.json()["success"] is True


@pytest.mark.asyncio
async def test_api_questions_rag_context():
    """POST /api/questions/rag-context returns prompt grounding context."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        res = await client.post(
            "/api/questions/rag-context",
            json={
                "section": "chem_phys",
                "subtopic": "Thermodynamics",
                "thematic_angle": "Calorimetry and enthalpy",
                "limit": 3,
            },
        )
        assert res.status_code == 200
        data = res.json()
        assert data["success"] is True
        assert "rag_context" in data
        assert "exemplars" in data["rag_context"]
        assert "avoidance_stems" in data["rag_context"]


@pytest.mark.asyncio
async def test_api_questions_check_duplicate_pgvector():
    """POST /api/questions/check-duplicate evaluates candidate stem against bank with pgvector."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        res = await client.post(
            "/api/questions/check-duplicate",
            json={
                "section": "bio_biochem",
                "subtopic": "Enzymology",
                "question_stem": "What is the primary thermodynamic effect of catalyst addition?",
                "options": [
                    {"id": "A", "text": "Lowers activation energy without altering delta G."},
                    {"id": "B", "text": "Makes delta G more negative."},
                ],
            },
        )
        assert res.status_code == 200
        data = res.json()
        assert data["success"] is True
        assert "duplicate_check" in data
        assert "similarity_score" in data["duplicate_check"]


@pytest.mark.asyncio
async def test_api_questions_backfill_embeddings():
    """POST /api/questions/backfill-embeddings triggers batch backfilling."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        res = await client.post(
            "/api/questions/backfill-embeddings",
            json={"batch_size": 25},
        )
        assert res.status_code == 200
        data = res.json()
        assert data["success"] is True
        assert "backfilled" in data
