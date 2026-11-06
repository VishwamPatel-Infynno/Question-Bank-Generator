"""The seven canned mock drafts must stay byte-identical when their source representation changes."""

import hashlib
import json

import pytest
from app.agents.mock_fixtures import _build_raw_mock_draft
from app.schemas import GenerationRequest, MCATSection

# sha256 (first 16 hex chars) of the canonical JSON dump of each (section, direct-independent) draft
EXPECTED_DIGESTS = {
    (MCATSection.CHEM_PHYS, False): "e62fcf5976945e31",
    (MCATSection.CHEM_PHYS, True): "4b27df97ce9d2568",
    (MCATSection.CARS, False): "a956efc1292ba755",
    (MCATSection.BIO_BIOCHEM, False): "003e8ab99100f94f",
    (MCATSection.BIO_BIOCHEM, True): "9059954a9bfb30d8",
    (MCATSection.PSYCH_SOC, False): "a3d3f92b4d17988f",
    (MCATSection.PSYCH_SOC, True): "c23842c27aefe692",
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
