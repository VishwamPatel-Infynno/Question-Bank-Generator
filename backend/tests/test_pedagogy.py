from pathlib import Path

import pytest
from app.schemas import (
    CONTENT_DOMAINS,
    PRIMARY_TRAPS,
    QUESTION_TYPES,
    Difficulty,
    GenerationRequest,
    MCATSection,
    get_skills_for_section,
    get_taxonomy_data,
)


def _base_module():
    """call_llm_validated resolves call_llm in app.agents.base, so patch it there."""
    import app.agents.base as base_mod

    return base_mod


def test_option_symmetry_and_anti_guessability_engine():
    """Validates calculate_option_symmetry, balance_and_shuffle_options, and remap_explanation_keys."""
    from app.agents.option_balancer import (
        balance_and_shuffle_options,
        calculate_option_symmetry,
        remap_explanation_keys,
    )
    from app.schemas import OptionChoice, QuestionDraft

    # 1. Test balanced options (tight word counts)
    balanced_opts = [
        OptionChoice(
            id="A",
            text="Antibiotic therapy was stepped down within 48 hours for culture-negative cases.",
        ),
        OptionChoice(
            id="B",
            text="Clinical guidelines recommended procalcitonin testing to guide empirical treatment.",
        ),
        OptionChoice(
            id="C",
            text="Clinicians routinely continued broad-spectrum coverage due to diagnostic anxiety.",
        ),
        OptionChoice(
            id="D",
            text="Mortality rates showed no statistically significant difference across clinical wards.",
        ),
    ]
    sym_balanced = calculate_option_symmetry(balanced_opts, "A")
    assert sym_balanced["is_balanced"] is True
    assert sym_balanced["status"] == "Balanced"
    assert sym_balanced["disparity_ratio"] <= 1.25
    assert sym_balanced["symmetry_score"] >= 90

    # 2. Test length disparity where correct answer is the longest option (test-wiseness flaw)
    biased_opts = [
        OptionChoice(id="A", text="Brief choice."),  # 2 words
        OptionChoice(id="B", text="Another short choice here."),  # 4 words
        OptionChoice(
            id="C",
            text="This is a remarkably comprehensive, nuanced, and detailed correct answer explaining all clinical subtleties thoroughly.",
        ),  # 15 words
        OptionChoice(id="D", text="Third short item."),  # 3 words
    ]
    sym_biased = calculate_option_symmetry(biased_opts, "C")
    assert sym_biased["is_balanced"] is False
    assert sym_biased["is_correct_longest"] is True
    assert sym_biased["disparity_ratio"] > 3.0
    assert sym_biased["status"] == "High Disparity"
    assert sym_biased["symmetry_score"] <= 60

    # 3. Test explanation remapping with cyclic/swapped keys
    # Mapping: A -> C, B -> A, C -> B, D -> D
    mapping = {"A": "C", "B": "A", "C": "B", "D": "D"}
    expl_input = (
        "Analysis of choices:\n"
        "- Option A is INCORRECT (Extreme Trap).\n"
        "- Option B is CORRECT because of theorem 1.\n"
        "- Key C is INCORRECT (Partial Match).\n"
        "- Distractor D is false.\n"
        "Therefore, Choice B is the right conclusion."
    )
    remapped_expl = remap_explanation_keys(expl_input, mapping)
    assert "- Option C is INCORRECT" in remapped_expl
    assert "- Option A is CORRECT" in remapped_expl
    assert "- Key B is INCORRECT" in remapped_expl
    assert "Therefore, Choice A is the right conclusion." in remapped_expl

    # 4. Test balance_and_shuffle_options on draft
    draft = QuestionDraft(
        stimulus_text="Clinical vignette...",
        question_stem="Which option is valid?",
        options=balanced_opts,
        correct_answer_id="B",
        correct_answer_ids=["B"],
        explanation="Option B is correct because the guidelines support it.",
    )
    shuffled_draft, sym = balance_and_shuffle_options(draft, seed=42)
    assert len(shuffled_draft.options) == 4
    # Ensure options have IDs A, B, C, D in order
    assert [o.id for o in shuffled_draft.options] == ["A", "B", "C", "D"]
    # Check that correct_answer_id is one of A, B, C, D
    assert shuffled_draft.correct_answer_id in ("A", "B", "C", "D")
    # Verify explanation stays in sync with the new key letter
    assert f"Option {shuffled_draft.correct_answer_id} is correct" in shuffled_draft.explanation
    assert sym["is_balanced"] is True

    # 5. Test numeric options QR ordering (sorted numerically ascending)
    qr_opts = [
        OptionChoice(id="A", text="£45.50"),
        OptionChoice(id="B", text="£12.00"),
        OptionChoice(id="C", text="£89.99"),
        OptionChoice(id="D", text="£24.50"),
    ]
    qr_draft = QuestionDraft(
        stimulus_text="Cost calculation scenario...",
        question_stem="What is the total prescription cost?",
        options=qr_opts,
        correct_answer_id="B",
        correct_answer_ids=["B"],
        explanation="Option B is correct: £12.00 is the final total.",
    )
    balanced_qr, _qr_sym = balance_and_shuffle_options(qr_draft)
    # Check ascending numeric order: 12.00, 24.50, 45.50, 89.99
    assert balanced_qr.options[0].text == "£12.00"
    assert balanced_qr.options[0].id == "A"
    assert balanced_qr.options[1].text == "£24.50"
    assert balanced_qr.options[2].text == "£45.50"
    assert balanced_qr.options[3].text == "£89.99"
    # Old B (£12.00) is now at index 0 (letter A)
    assert balanced_qr.correct_answer_id == "A"
    assert "Option A is correct: £12.00 is the final total." in balanced_qr.explanation


@pytest.mark.asyncio
async def test_smart_ai_trap_and_explanation_breakdown(monkeypatch):
    import app.agents.generator as gen_mod
    from app.agents.base import LLMNotConfiguredError
    from app.agents.mock_fixtures import get_mock_draft
    from app.workflow.graph import run_workflow

    async def mock_fail_call_llm(*_args, **_kwargs):
        # Offline mode: no credentials configured, so agents use their heuristic fixtures.
        raise LLMNotConfiguredError("Fast fallback to mock draft in unit test")

    monkeypatch.setattr(gen_mod, "call_llm", mock_fail_call_llm)
    monkeypatch.setattr(_base_module(), "call_llm", mock_fail_call_llm)
    # Draft/regenerate calls go through call_llm_validated, which resolves call_llm in base
    import app.agents.base as base_mod

    monkeypatch.setattr(base_mod, "call_llm", mock_fail_call_llm)

    # 1. Automatic Smart AI Trap Choice resolution on draft
    req_auto = GenerationRequest(
        section=MCATSection.CARS,
        difficulty=Difficulty.HARD,
        primary_trap="Automatic",
        passage_required="Yes",
    )
    draft_auto = get_mock_draft(req_auto)
    assert draft_auto.primary_trap is not None
    assert draft_auto.primary_trap != "Automatic"
    assert "Winning Strategy" not in draft_auto.explanation

    # 2. End-to-end workflow assigns Smart AI primary trap to final Question
    res = await run_workflow(req_auto)
    assert res.question is not None
    assert res.question.primary_trap is not None
    assert res.question.primary_trap != "Automatic"
    assert "Winning Strategy" not in res.question.explanation

    # 3. Explicit trap selection is preserved
    req_explicit = GenerationRequest(
        section=MCATSection.CHEM_PHYS,
        difficulty=Difficulty.MEDIUM,
        primary_trap="Calculation_Formula_Trap",
        passage_required="No",
    )
    res_explicit = await run_workflow(req_explicit)
    assert res_explicit.question is not None
    assert res_explicit.question.primary_trap == "Calculation_Formula_Trap"


@pytest.mark.asyncio
async def test_manager_dependent_taxonomy_integration():
    """Validates the official manager-provided MCAT Dependent Taxonomy integration."""
    from app.main import app
    from httpx import ASGITransport, AsyncClient

    # 1. Verify Taxonomy Data Structure
    tax = get_taxonomy_data()
    assert tax["schema_version"] == "1.0"
    assert tax["exam"]["id"] == "MCAT"
    assert len(tax["sections"]) == 4

    # 2. Verify Skills Mapping
    cp_skills = get_skills_for_section("CP")
    assert len(cp_skills) == 4
    cp_skill_ids = [s["id"] for s in cp_skills]
    assert cp_skill_ids == ["S1", "S2", "S3", "S4"]

    cars_skills = get_skills_for_section("CARS")
    assert len(cars_skills) == 3
    cars_skill_ids = [s["id"] for s in cars_skills]
    assert cars_skill_ids == ["CARS1", "CARS2", "CARS3"]

    # 3. Verify Options Counts
    assert len(CONTENT_DOMAINS) == 33
    assert len(PRIMARY_TRAPS) == 25
    assert len(QUESTION_TYPES) == 8

    # 4. Verify API Endpoints
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # GET /api/taxonomy
        resp_tax = await client.get("/api/taxonomy")
        assert resp_tax.status_code == 200
        tax_payload = resp_tax.json()
        assert tax_payload["exam"]["id"] == "MCAT"
        assert len(tax_payload["sections"]) == 4

        # GET /api/sections
        resp_sec = await client.get("/api/sections")
        assert resp_sec.status_code == 200
        sec_payload = resp_sec.json()
        sections = sec_payload["sections"]
        assert len(sections) == 4
        cp_sec = next(s for s in sections if s["code"] == "CP")
        assert len(cp_sec["subjects"]) == 5
        assert len(cp_sec["skills"]) == 4

    # 5. Verify GenerationRequest Hierarchy Lineage & Dynamic Batch Size
    req = GenerationRequest(
        section="chem_phys",
        subject="General Chemistry",
        unit="Atomic Structure and Periodicity",
        topic="Atomic Structure",
        subtopic="Protons, neutrons, and electrons",
        aamc_skill="S1",
        subskill="Identify or recognize a scientific concept",
        question_type="DISCRETE_MCQ",
        likely_mistake_pattern="Uses the wrong reference value in a calculation",
        content_domains=["Atomic and Molecular Structure"],
        questions_to_generate=3,
    )
    assert req.questions_to_generate == 3
    assert req.subject == "General Chemistry"
    assert req.subskill == "Identify or recognize a scientific concept"


def test_taxonomy_json_parity_between_backend_and_frontend():
    """Verify that backend and frontend taxonomy JSON files stay 100% in sync with zero drift."""
    backend_path = (
        Path(__file__).resolve().parent.parent / "app" / "data" / "mcat_dependent_taxonomy.json"
    )
    frontend_path = (
        Path(__file__).resolve().parent.parent.parent
        / "frontend"
        / "src"
        / "constants"
        / "mcat_dependent_taxonomy.json"
    )

    assert backend_path.exists(), f"Backend taxonomy JSON file must exist at {backend_path}"
    assert frontend_path.exists(), f"Frontend taxonomy JSON file must exist at {frontend_path}"

    backend_content = backend_path.read_text(encoding="utf-8")
    frontend_content = frontend_path.read_text(encoding="utf-8")

    assert backend_content == frontend_content, (
        "Taxonomy JSON in backend/app/data and frontend/src/constants must be byte-for-byte identical"
    )
