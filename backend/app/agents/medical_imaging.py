"""
Medical Imaging Modality Detection & Clinical Prompt Synthesis Engine for AAMC MCAT.

Provides domain-specific taxonomy, automated modality classification, and photorealistic
diffusion prompt synthesis for medical imaging (Radiology, Histopathology, Gross Anatomy,
Cellular Electron Microscopy, Physiological Traces, and Clinical Pathology) alongside
scientific biochemical diagrams.
"""

import re
from enum import Enum


class MedicalModality(str, Enum):
    RADIOLOGY = "radiology"
    HISTOLOGY = "histology"
    GROSS_ANATOMY = "gross_anatomy"
    CELLULAR_MICROSCOPY = "cellular_microscopy"
    PHYSIOLOGY_TRACE = "physiology_trace"
    CLINICAL_PATHOLOGY = "clinical_pathology"
    SCIENTIFIC_DIAGRAM = "scientific_diagram"


# Regular expression patterns for robust medical modality classification
RADIOLOGY_PATTERNS = re.compile(
    r"\b("
    r"x-ray|xray|radiograph|radiography|chest\s+film|ct\s+scan|computed\s+tomography|"
    r"mri|magnetic\s+resonance|t1-weighted|t2-weighted|flair|angiogram|angiography|"
    r"ultrasound|sonogram|echocardiogram|echo|fluoroscopy|pet\s+scan|radiopaque|radiolucent|"
    r"hounsfield|axial\s+slice|coronal\s+section|sagittal\s+view|contrast-enhanced"
    r")\b",
    re.IGNORECASE,
)

HISTOLOGY_PATTERNS = re.compile(
    r"\b("
    r"histolog\w*|histopatholog\w*|h&e|hematoxylin|eosin|biopsy|tissue\s+section|"
    r"light\s+microscop\w*|light\s+micrograph|stained\s+slide|epitheli\w*|endotheli\w*|"
    r"connective\s+tissue|cartilage|bone\s+trabeculae|osteocyte|fibroblast|lymph\s+node|"
    r"glomerul\w*|renal\s+tubule|intercalated\s+disc|sarcomere|myocyte|smooth\s+muscle|"
    r"striated\s+muscle|adipocyte|goblet\s+cell|squamous|columnar|cuboidal|crypt|villi|"
    r"cytoarchitect\w*|cytolog\w*|smear|papanicolaou|gram\s+stain"
    r")\b",
    re.IGNORECASE,
)

GROSS_ANATOMY_PATTERNS = re.compile(
    r"\b("
    r"gross\s+anatom\w*|anatomical\s+dissection|cadaver\w*|organ\s+system|organ\s+dissection|"
    r"cross-section\s+of\s+the\s+heart|circle\s+of\s+willis|brachial\s+plexus|femoral\s+triangle|"
    r"mediastinum|coronary\s+arter\w*|peritoneum|retroperitoneal|cranial\s+nerve|"
    r"cerebral\s+cortex|brainstem|cerebellum|spinal\s+cord|ventricle|nephron\s+vasculature|"
    r"hepatic\s+portal|biliary\s+tree|pulmonary\s+trunk|aortic\s+arch|mesentery|"
    r"netter|medical\s+atlas|gross\s+specimen"
    r")\b",
    re.IGNORECASE,
)

CELLULAR_MICROSCOPY_PATTERNS = re.compile(
    r"\b("
    r"electron\s+microscop\w*|electron\s+micrograph|tem\b|sem\b|transmission\s+electron|"
    r"scanning\s+electron|ultrastructur\w*|organelle|mitochondri\w*\s+cristae|endoplasmic\s+reticulum|"
    r"golgi\s+apparatus|ribosome|lysosome|peroxisome|centrosome|nuclear\s+pore|"
    r"cilia\s+axoneme|microtubule|actin\s+filament|synaptic\s+vesicle|postsynaptic\s+density|"
    r"desmosome|gap\s+junction|tight\s+junction|bacteriophage|capsid|viral\s+particle"
    r")\b",
    re.IGNORECASE,
)

PHYSIOLOGY_TRACE_PATTERNS = re.compile(
    r"\b("
    r"ecg\b|ekg\b|electrocardiogram|rhythm\s+strip|lead\s+ii|lead\s+[i|v][1-6]?|"
    r"p\s+wave|qrs\s+complex|t\s+wave|pr\s+interval|st\s+segment|qt\s+interval|"
    r"action\s+potential|cardiac\s+action\s+potential|membrane\s+potential\s+curve|"
    r"depolarization\s+trace|eeg\b|electroencephalogram|spirometr\w*|spirogram|"
    r"fev1|fvc|flow-volume\s+loop|pulse\s+tracing|arterial\s+pressure\s+waveform"
    r")\b",
    re.IGNORECASE,
)

CLINICAL_PATHOLOGY_PATTERNS = re.compile(
    r"\b("
    r"clinical\s+presentation|clinical\s+photograph|dermatolog\w*|skin\s+lesion|erythema|"
    r"macule|papule|pustule|melanoma|basal\s+cell|rash|ophthalmolog\w*|fundoscop\w*|"
    r"retinal\s+photograph|optic\s+disc|macula|fundus|cataract|diabetic\s+retinopathy|"
    r"papilledema|slit\s+lamp|corneal|scleral\s+icterus|jaundice|cyanosis|gangrene|"
    r"gross\s+pathology\s+lesion"
    r")\b",
    re.IGNORECASE,
)


def detect_medical_modality(
    prompt_text: str,
    section: str = "",
    topic: str = "",
    question_stem: str = "",
) -> MedicalModality:
    """
    Intelligently classifies the intended medical imaging modality based on prompt description,
    question stem, topic, and exam section context.
    """
    combined = f"{prompt_text} {question_stem} {topic} {section}".lower()

    # Prioritized classification rules
    if RADIOLOGY_PATTERNS.search(combined):
        return MedicalModality.RADIOLOGY

    if PHYSIOLOGY_TRACE_PATTERNS.search(combined):
        return MedicalModality.PHYSIOLOGY_TRACE

    if CELLULAR_MICROSCOPY_PATTERNS.search(combined):
        return MedicalModality.CELLULAR_MICROSCOPY

    if HISTOLOGY_PATTERNS.search(combined):
        return MedicalModality.HISTOLOGY

    if CLINICAL_PATHOLOGY_PATTERNS.search(combined):
        return MedicalModality.CLINICAL_PATHOLOGY

    if GROSS_ANATOMY_PATTERNS.search(combined):
        return MedicalModality.GROSS_ANATOMY

    # Fallback to standard scientific diagram (biochemical, physical, metabolic)
    return MedicalModality.SCIENTIFIC_DIAGRAM


def get_modality_display_name(modality: MedicalModality | str) -> str:
    """Returns human-friendly, professional label for the modality."""
    modality_str = modality.value if isinstance(modality, MedicalModality) else str(modality)
    labels = {
        MedicalModality.RADIOLOGY.value: "Radiology (X-Ray / CT / MRI)",
        MedicalModality.HISTOLOGY.value: "Histopathology (H&E)",
        MedicalModality.GROSS_ANATOMY.value: "Gross Anatomy",
        MedicalModality.CELLULAR_MICROSCOPY.value: "Cellular Microscopy (TEM/SEM)",
        MedicalModality.PHYSIOLOGY_TRACE.value: "Physiological Trace / ECG",
        MedicalModality.CLINICAL_PATHOLOGY.value: "Clinical Pathology",
        MedicalModality.SCIENTIFIC_DIAGRAM.value: "Scientific Diagram",
    }
    return labels.get(modality_str, "Scientific Figure")


def synthesize_medical_prompt(
    raw_prompt: str,
    modality: MedicalModality,
) -> str:
    """
    Constructs an optimized, photorealistic diffusion prompt tailored for medical fidelity.
    Ensures correct diagnostic background, staining protocols, lighting, and anatomical views.
    """
    cleaned_prompt = raw_prompt.strip()
    # Strip any conflicting legacy prefixes if present
    cleaned_prompt = re.sub(
        r"^high-quality\s+educational\s+test\s+figure[^:]*:\s*",
        "",
        cleaned_prompt,
        flags=re.IGNORECASE,
    )

    if modality == MedicalModality.RADIOLOGY:
        return (
            "Authentic clinical diagnostic medical imaging scan, official PACS radiology workstation film. "
            "High-resolution grayscale contrast, anatomically correct radiologic windowing, authentic dark/black background, "
            "standard radiological orientation and projection view (e.g. AP, lateral, or axial CT/MRI slice), "
            "crisp bone and soft tissue delineation, diagnostic medical board exam quality: "
            f"{cleaned_prompt}"
        )

    if modality == MedicalModality.HISTOLOGY:
        return (
            "High-resolution medical histopathology light micrograph, authentic laboratory tissue biopsy slide. "
            "Standard Hematoxylin and Eosin (H&E) staining, vivid purple and deep blue basophilic cell nuclei, "
            "rich pink and eosinophilic cytoplasm, clear extracellular matrix architecture, 200x-400x magnification field, "
            "flawless cellular morphology, clinical pathology publication standard: "
            f"{cleaned_prompt}"
        )

    if modality == MedicalModality.GROSS_ANATOMY:
        return (
            "Highly detailed medical anatomical illustration, master medical atlas Netter and Gray's anatomy standard. "
            "Photorealistic cadaveric and surgical accuracy, true-to-life human anatomical structures, clean surgical illumination, "
            "distinct vascular, muscular, and neural pathways, authentic medical textbook illustration: "
            f"{cleaned_prompt}"
        )

    if modality == MedicalModality.CELLULAR_MICROSCOPY:
        return (
            "Authentic cellular electron micrograph, transmission electron microscopy (TEM) or scanning electron microscopy (SEM). "
            "High-magnification subcellular ultrastructure, crisp organelle lipid bilayer membranes, nanometer-scale detail, "
            "authentic grayscale microscopy texture, biological cytology peer-reviewed journal quality: "
            f"{cleaned_prompt}"
        )

    if modality == MedicalModality.PHYSIOLOGY_TRACE:
        return (
            "Standard clinical 12-lead electrocardiogram (ECG/EKG) rhythm strip or physiological recording. "
            "Authentic medical recording paper with precise pink and red millimeter grid lines (1mm small boxes, 5mm large boxes). "
            "Crisp continuous black waveform trace, clearly defined P waves, QRS complexes, and T waves, diagnostic cardiology calibration: "
            f"{cleaned_prompt}"
        )

    if modality == MedicalModality.CLINICAL_PATHOLOGY:
        return (
            "High-resolution clinical diagnostic photograph, authentic medical presentation. "
            "Natural clinical lighting, true-to-life dermatology or ophthalmologic fundoscopy appearance, "
            "diagnostic pathognomonic features, medical education and board examination standard: "
            f"{cleaned_prompt}"
        )

    # Default: Scientific Diagram / Reaction Scheme
    return (
        "High-contrast educational scientific illustration, clean vector schematic on neutral background. "
        "Clear anatomical or biochemical pathways, crisp molecular or laboratory labeling, publication-grade AAMC MCAT figure: "
        f"{cleaned_prompt}"
    )
