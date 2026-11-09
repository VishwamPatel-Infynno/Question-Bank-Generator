"""
Unit and Integration Tests for AAMC MCAT Medical Imaging Engine.

Tests modality detection, medical prompt synthesis, and image generation pipeline
for Radiology, Histopathology, Gross Anatomy, Cellular Microscopy, Physiological Traces,
and Clinical Pathology.
"""

import pytest
from app.agents.image_generator import generate_image_stimulus
from app.agents.medical_imaging import (
    MedicalModality,
    detect_medical_modality,
    get_modality_display_name,
    synthesize_medical_prompt,
)
from app.core.config import config
from app.schemas import Difficulty, GenerationRequest, MCATSection, OptionChoice, QuestionDraft


def test_detect_medical_modality_radiology():
    test_cases = [
        "A posteroanterior (PA) chest X-ray demonstrating right middle lobe consolidation",
        "Axial CT scan of the brain showing hyperdense middle cerebral artery sign",
        "Sagittal T2-weighted MRI of the lumbar spine revealing L4-L5 disc herniation",
        "Echocardiogram sonogram revealing mitral valve prolapse with regurgitant jet",
        "Fluoroscopy radiograph showing barium swallow transit delay",
    ]
    for prompt in test_cases:
        modality = detect_medical_modality(prompt)
        assert modality == MedicalModality.RADIOLOGY, f"Failed for prompt: {prompt}"


def test_detect_medical_modality_histology():
    test_cases = [
        "Histopathology biopsy slide with H&E staining of the small intestine showing blunted villi",
        "Light micrograph of skeletal muscle stained with hematoxylin and eosin",
        "Histological section of renal cortex demonstrating glomerulus and Bowman capsule",
        "Tissue section showing ciliated pseudostratified columnar epithelium and goblet cells",
        "Peripheral blood smear revealing sickle-shaped erythrocytes and Howell-Jolly bodies",
    ]
    for prompt in test_cases:
        modality = detect_medical_modality(prompt)
        assert modality == MedicalModality.HISTOLOGY, f"Failed for prompt: {prompt}"


def test_detect_medical_modality_gross_anatomy():
    test_cases = [
        "Gross anatomical dissection of the human heart revealing the four chambers and coronary sulcus",
        "Medical atlas illustration of the circle of Willis and cerebral arterial supply",
        "Cadaveric dissection of the anterior thigh showing the femoral triangle boundaries",
        "Gross organ specimen of the liver showing the falciform ligament and biliary tree",
    ]
    for prompt in test_cases:
        modality = detect_medical_modality(prompt)
        assert modality == MedicalModality.GROSS_ANATOMY, f"Failed for prompt: {prompt}"


def test_detect_medical_modality_cellular_microscopy():
    test_cases = [
        "Transmission electron micrograph (TEM) showing high-magnification mitochondrial cristae",
        "Scanning electron micrograph (SEM) showing respiratory tract cilia axoneme ultrastructure",
        "Electron microscopy view of rough endoplasmic reticulum and ribosome studded membranes",
        "High-resolution TEM of a neuromuscular junction with synaptic vesicles and postsynaptic density",
    ]
    for prompt in test_cases:
        modality = detect_medical_modality(prompt)
        assert modality == MedicalModality.CELLULAR_MICROSCOPY, f"Failed for prompt: {prompt}"


def test_detect_medical_modality_physiology_trace():
    test_cases = [
        "Standard 12-lead ECG rhythm strip demonstrating ST-segment elevation in leads II, III, and aVF",
        "Lead II electrocardiogram strip showing prolonged PR interval consistent with first-degree AV block",
        "Ventricular cardiac action potential curve tracing phases 0 through 4 with rapid depolarization",
        "Spirometry flow-volume loop demonstrating an obstructive ventilatory defect with reduced FEV1",
    ]
    for prompt in test_cases:
        modality = detect_medical_modality(prompt)
        assert modality == MedicalModality.PHYSIOLOGY_TRACE, f"Failed for prompt: {prompt}"


def test_detect_medical_modality_clinical_pathology():
    test_cases = [
        "Clinical photograph of an asymmetrical pigmented skin lesion with irregular borders on the arm",
        "Fundoscopic retinal photograph showing optic disc cupping and flame hemorrhages in diabetic retinopathy",
        "Clinical presentation photograph demonstrating erythema migrans bullseye rash on the torso",
    ]
    for prompt in test_cases:
        modality = detect_medical_modality(prompt)
        assert modality == MedicalModality.CLINICAL_PATHOLOGY, f"Failed for prompt: {prompt}"


def test_detect_medical_modality_scientific_diagram():
    test_cases = [
        "Lineweaver-Burk double reciprocal plot comparing uninhibited enzyme kinetics to competitive inhibition",
        "Biochemical pathway diagram depicting the citric acid cycle steps and dehydrogenase enzymes",
        "Optics ray tracing diagram showing image formation by a converging convex lens",
    ]
    for prompt in test_cases:
        modality = detect_medical_modality(prompt)
        assert modality == MedicalModality.SCIENTIFIC_DIAGRAM, f"Failed for prompt: {prompt}"


def test_get_modality_display_name():
    assert get_modality_display_name(MedicalModality.RADIOLOGY) == "Radiology (X-Ray / CT / MRI)"
    assert get_modality_display_name(MedicalModality.HISTOLOGY) == "Histopathology (H&E)"
    assert get_modality_display_name(MedicalModality.GROSS_ANATOMY) == "Gross Anatomy"
    assert (
        get_modality_display_name(MedicalModality.CELLULAR_MICROSCOPY)
        == "Cellular Microscopy (TEM/SEM)"
    )
    assert (
        get_modality_display_name(MedicalModality.PHYSIOLOGY_TRACE) == "Physiological Trace / ECG"
    )
    assert get_modality_display_name(MedicalModality.CLINICAL_PATHOLOGY) == "Clinical Pathology"
    assert get_modality_display_name(MedicalModality.SCIENTIFIC_DIAGRAM) == "Scientific Diagram"


def test_synthesize_medical_prompt_radiology():
    raw = "PA chest radiograph showing left pleural effusion"
    synthesized = synthesize_medical_prompt(raw, MedicalModality.RADIOLOGY)
    assert "Authentic clinical diagnostic medical imaging scan" in synthesized
    assert "dark/black background" in synthesized
    assert "PA chest radiograph showing left pleural effusion" in synthesized
    # Ensure legacy clean white background prefix is NOT present
    assert "clean white background" not in synthesized


def test_synthesize_medical_prompt_histology():
    raw = "H&E renal cortex biopsy showing glomerular crescents"
    synthesized = synthesize_medical_prompt(raw, MedicalModality.HISTOLOGY)
    assert "Hematoxylin and Eosin (H&E) staining" in synthesized
    assert "purple and deep blue basophilic cell nuclei" in synthesized
    assert "pink and eosinophilic cytoplasm" in synthesized
    assert "H&E renal cortex biopsy showing glomerular crescents" in synthesized


def test_synthesize_medical_prompt_physiology_trace():
    raw = "Lead II ECG showing ventricular tachycardia"
    synthesized = synthesize_medical_prompt(raw, MedicalModality.PHYSIOLOGY_TRACE)
    assert "millimeter grid lines" in synthesized
    assert "P waves, QRS complexes, and T waves" in synthesized
    assert "Lead II ECG showing ventricular tachycardia" in synthesized


def test_synthesize_medical_prompt_legacy_strip():
    raw = "High-quality educational test figure, scientific illustration, or medical diagram on clean white background: Chest X-ray"
    synthesized = synthesize_medical_prompt(raw, MedicalModality.RADIOLOGY)
    assert "clean white background" not in synthesized
    assert "Chest X-ray" in synthesized


@pytest.mark.asyncio
async def test_generate_image_stimulus_modality_integration(monkeypatch):
    """Verifies generate_image_stimulus detects modality and populates usage details."""
    monkeypatch.setattr(config, "ACTIVE_IMAGE_PROVIDER", "deepinfra")
    monkeypatch.setattr(config, "DEEPINFRA_API_KEY", "mock_key")

    captured_prompt = None

    async def mock_call_flux(prompt, width, height, iters, api_key, model=None):
        nonlocal captured_prompt
        captured_prompt = prompt
        return ("data:image/png;base64,MOCK_DATA", 0.014)

    import app.agents.image_generator as img_gen_mod

    monkeypatch.setattr(img_gen_mod, "call_deepinfra_flux", mock_call_flux)

    draft = QuestionDraft(
        stimulus_text="Clinical vignette about a cardiac patient.",
        question_stem="Which structure is indicated in the chest radiograph?",
        options=[
            OptionChoice(id="A", text="Option A"),
            OptionChoice(id="B", text="Option B"),
            OptionChoice(id="C", text="Option C"),
            OptionChoice(id="D", text="Option D"),
        ],
        correct_answer_id="A",
        explanation="Option A is correct.",
        image_needed=True,
        image_prompt_or_type="Posteroanterior chest X-ray demonstrating cardiomegaly and pulmonary edema",
    )
    req = GenerationRequest(
        section=MCATSection.BIO_BIOCHEM,
        subtopic="Cardiovascular Physiology",
        difficulty=Difficulty.MEDIUM,
        allow_ai_images=True,
    )

    img_data, img_svg, img_desc, usage = await generate_image_stimulus(draft, req)

    assert img_data == "data:image/png;base64,MOCK_DATA"
    assert img_svg is None
    assert "cardiomegaly" in img_desc
    assert captured_prompt is not None
    assert "dark/black background" in captured_prompt
    assert "PACS radiology workstation" in captured_prompt

    assert usage is not None
    assert usage["details"]["modality"] == "radiology"
    assert usage["details"]["medical_modality"] == "radiology"


@pytest.mark.asyncio
async def test_generate_image_stimulus_modality_integration_openai(monkeypatch):
    """Verifies generate_image_stimulus detects modality and populates usage details when using OpenAI."""
    monkeypatch.setattr(config, "ACTIVE_IMAGE_PROVIDER", "openai")
    monkeypatch.setattr(config, "OPENAI_API_KEY", "mock_key")

    captured_prompt = None

    async def mock_call_openai(prompt, width, height, api_key, model=None, quality="auto"):
        nonlocal captured_prompt
        captured_prompt = prompt
        return ("data:image/png;base64,MOCK_DATA_OPENAI", 0.020)

    import app.agents.image_generator as img_gen_mod

    monkeypatch.setattr(img_gen_mod, "call_openai_image_api", mock_call_openai)

    draft = QuestionDraft(
        stimulus_text="Clinical vignette about a cardiac patient.",
        question_stem="Which structure is indicated in the chest radiograph?",
        options=[
            OptionChoice(id="A", text="Option A"),
            OptionChoice(id="B", text="Option B"),
            OptionChoice(id="C", text="Option C"),
            OptionChoice(id="D", text="Option D"),
        ],
        correct_answer_id="A",
        explanation="Option A is correct.",
        image_needed=True,
        image_prompt_or_type="Posteroanterior chest X-ray demonstrating cardiomegaly and pulmonary edema",
    )
    req = GenerationRequest(
        section=MCATSection.BIO_BIOCHEM,
        subtopic="Cardiovascular Physiology",
        difficulty=Difficulty.MEDIUM,
        allow_ai_images=True,
    )

    img_data, img_svg, img_desc, usage = await generate_image_stimulus(draft, req)

    assert img_data == "data:image/png;base64,MOCK_DATA_OPENAI"
    assert img_svg is None
    assert "cardiomegaly" in img_desc
    assert captured_prompt is not None
    assert "dark/black background" in captured_prompt
    assert "PACS radiology workstation" in captured_prompt

    assert usage is not None
    assert usage["details"]["modality"] == "radiology"
    assert usage["details"]["medical_modality"] == "radiology"
