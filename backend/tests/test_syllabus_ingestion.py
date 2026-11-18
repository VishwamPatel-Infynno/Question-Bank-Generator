"""
test_syllabus_ingestion.py - Unit and integration tests for syllabus ingestion and taxonomy mapping.
"""

import io

import pytest
from app.main import app
from app.services.syllabus_ingestion import (
    extract_text_from_file_bytes,
    ingest_and_map_syllabus,
)
from httpx import ASGITransport, AsyncClient


@pytest.mark.asyncio
async def test_extract_text_from_plain_text():
    sample = "Syllabus: Biochemistry 101\nCourse objectives: Amino acid properties, Michaelis-Menten kinetics."
    extracted = extract_text_from_file_bytes(sample.encode("utf-8"), filename="syllabus.txt")
    assert "Michaelis-Menten kinetics" in extracted
    assert "Biochemistry 101" in extracted


@pytest.mark.asyncio
async def test_deterministic_taxonomy_bio_biochem():
    text = (
        "Cellular biology and biochemistry syllabus covering enzyme kinetics, "
        "glycolysis, amino acid side chains, protein structure, and DNA transcription."
    )
    res = await ingest_and_map_syllabus(text, title="Bio Syllabus")
    assert res["section"] == "bio_biochem"
    assert "Biological" in res["section_name"]
    assert res["confidence"] >= 0.70
    assert len(res["suggested_batches"]) >= 1
    assert "thematic_angle" in res["suggested_batches"][0]


@pytest.mark.asyncio
async def test_deterministic_taxonomy_chem_phys():
    text = (
        "General physics and organic chemistry covering electric circuits, optics, "
        "thermodynamics, reaction mechanisms, and acid base titrations."
    )
    res = await ingest_and_map_syllabus(text, title="Physics Syllabus")
    assert res["section"] == "chem_phys"
    assert "Chemical and Physical" in res["section_name"]
    assert res["confidence"] >= 0.70


@pytest.mark.asyncio
async def test_deterministic_taxonomy_psych_soc():
    text = (
        "Introductory psychology and sociology covering operant conditioning, social stratification, "
        "memory consolidation, cognitive dissonance, and identity formation."
    )
    res = await ingest_and_map_syllabus(text, title="Psych Syllabus")
    assert res["section"] == "psych_soc"
    assert "Psychological" in res["section_name"]


@pytest.mark.asyncio
async def test_api_ingest_syllabus_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/ai/ingest-syllabus",
            json={
                "content": "Medical school preparatory syllabus on enzyme inhibition, competitive inhibitors, and Vmax changes.",
                "title": "Enzymes Syllabus",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["section"] in ("bio_biochem", "chem_phys")
        assert "topic" in data
        assert "suggested_batches" in data
        assert len(data["suggested_batches"]) >= 1


@pytest.mark.asyncio
async def test_api_ingest_syllabus_file_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        file_content = b"Syllabus on Classical Mechanics, Fluid Dynamics, Bernoulli principle, and Archimedes buoyancy."
        files = {
            "file": ("physics_syllabus.txt", io.BytesIO(file_content), "text/plain"),
        }
        resp = await client.post(
            "/api/ai/ingest-syllabus-file",
            files=files,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["section"] == "chem_phys"
        assert "confidence" in data
        assert "suggested_instructions" in data
