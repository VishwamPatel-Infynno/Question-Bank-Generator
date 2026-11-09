"""The seven canned mock drafts must stay byte-identical when their source representation changes."""

import hashlib
import json

import pytest
from app.agents.mock_fixtures import _build_raw_mock_draft
from app.schemas import GenerationRequest, MCATSection

# sha256 (first 16 hex chars) of the canonical JSON dump of each (section, direct-independent) draft
EXPECTED_DIGESTS = {
    (MCATSection.CHEM_PHYS, False): "833c039431d7c765",
    (MCATSection.CHEM_PHYS, True): "ab5b9d54d9add114",
    (MCATSection.CARS, False): "f0086809fc823955",
    (MCATSection.BIO_BIOCHEM, False): "54569cda51c086d3",
    (MCATSection.BIO_BIOCHEM, True): "0e5f56f052d8e4c7",
    (MCATSection.PSYCH_SOC, False): "e27244f2996658ea",
    (MCATSection.PSYCH_SOC, True): "81c14cd3fe1bf339",
}


def _digest(section: MCATSection, direct_independent: bool) -> str:
    fields = {"section": section, "subtopic": "x", "difficulty": "Medium"}
    if direct_independent:
        fields["passage_required"] = "No"
    draft = _build_raw_mock_draft(GenerationRequest(**fields))
    canonical = json.dumps(draft.model_dump(), sort_keys=True, default=str)
    return hashlib.sha256(canonical.encode()).hexdigest()[:16]


@pytest.mark.parametrize(("section", "direct_independent"), sorted(EXPECTED_DIGESTS, key=str))
def test_mock_draft_snapshot(section, direct_independent):
    assert _digest(section, direct_independent) == EXPECTED_DIGESTS[(section, direct_independent)]


def test_cars_is_always_passage_based():
    """CARS has no direct-independent variant: asking for one yields the passage draft."""
    cars = GenerationRequest(
        section="CARS", subtopic="x", difficulty="Medium", passage_required="No"
    )
    assert _build_raw_mock_draft(cars).stimulus_text
    assert _digest(MCATSection.CARS, True) == EXPECTED_DIGESTS[(MCATSection.CARS, False)]
