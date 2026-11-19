"""
Unit tests for AI Copilot API endpoints (/api/ai/*).
"""

from app.core.config import config
from app.main import app
from fastapi.testclient import TestClient

client = TestClient(app)


def test_enhance_instructions_endpoint(monkeypatch):
    monkeypatch.setattr(config, "OFFLINE_MODE", True)
    payload = {
        "instructions": "make it tough on enzyme kinetics",
        "section": "bio_biochem",
        "topic": "Enzymology",
        "difficulty": "high",
    }
    response = client.post("/api/ai/enhance-instructions", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "enhanced_instructions" in data
    assert "AAMC CALIBRATED MANDATE" in data["enhanced_instructions"]
    assert "enzyme kinetics" in data["enhanced_instructions"]


def test_refine_question_simplify_explanation(monkeypatch):
    monkeypatch.setattr(config, "OFFLINE_MODE", True)
    payload = {
        "question": {
            "question_stem": "Which enzyme catalyzes the committed step in glycolysis?",
            "options": [
                {"id": "A", "text": "Phosphofructokinase-1"},
                {"id": "B", "text": "Hexokinase"},
                {"id": "C", "text": "Pyruvate kinase"},
                {"id": "D", "text": "Aldolase"},
            ],
            "correct_answer_id": "A",
            "explanation": "PFK-1 catalyzes F6P to F-1,6-BP.",
        },
        "instruction": "simplify explanation for a beginner",
        "action": "simplify_explanation",
    }
    response = client.post("/api/ai/refine-question", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "question" in data
    assert "SIMPLIFIED EXPLANATION:" in data["question"]["explanation"]


def test_audit_passage_endpoint():
    passage = (
        "Researchers analyzed the kinetic parameters of human lactate dehydrogenase across various pH buffers.\n\n"
        "At pH 7.4, the initial velocity reached 45.2 umol/min with a Michaelis constant Km of 1.2 mM.\n\n"
        "Spectrophotometric tracking at 340 nm verified NADH oxidation over 5 minutes.\n\n"
        "In contrast, acidic conditions at pH 6.2 resulted in a 40% reduction in Vmax.\n\n"
        "These empirical observations suggest allosteric sensitivity to proton concentration in ischemic skeletal muscle."
    )
    payload = {"passage_text": passage}
    response = client.post("/api/ai/audit-passage", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["word_count"] > 30
    assert data["sentence_count"] >= 4
    assert data["empirical_density_score"] >= 3
    assert data["aamc_alignment_score"] >= 70
    assert len(data["diagnostics"]) >= 2


def test_study_guide_endpoint(monkeypatch):
    monkeypatch.setattr(config, "OFFLINE_MODE", True)
    payload = {
        "questions": [
            {
                "question_stem": "What is the primary function of the nephron loop of Henle?",
                "options": [
                    {"id": "A", "text": "Establishing a hyperosmotic medullary gradient"},
                    {"id": "B", "text": "Filtration of serum proteins into Bowman space"},
                    {"id": "C", "text": "Aldosterone-mediated sodium excretion"},
                    {"id": "D", "text": "Secretion of erythropoietin into cortical capillaries"},
                ],
                "correct_answer_id": "A",
                "subtopic": "Renal Physiology",
            }
        ]
    }
    response = client.post("/api/ai/study-guide", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "title" in data
    assert len(data["flashcards"]) == 1
    assert "loop of Henle" in data["flashcards"][0]["front"]
    assert "markdown_guide" in data
