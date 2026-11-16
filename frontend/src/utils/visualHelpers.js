/**
 * visualHelpers.js - Intelligent Medical Modality Classification & Visual Metadata Resolution
 *
 * Classifies AAMC MCAT visual stimuli into domain modalities (Radiology, Histopathology,
 * Gross Anatomy, Electron Microscopy, Physiology/ECG Traces, Clinical Pathology, and SVGs)
 * and resolves corresponding presentation styling (badges, labels, high-contrast dark backgrounds).
 */

const RADIOLOGY_PATTERN =
  /\b(x-ray|xray|radiograph|radiography|chest film|ct scan|computed tomography|mri|magnetic resonance|t1|t2|flair|ultrasound|sonogram|fluoroscopy|pet scan|hounsfield|axial slice|coronal section)\b/i;

const HISTOLOGY_PATTERN =
  /\b(histolog|histopatholog|h&e|hematoxylin|eosin|biopsy|tissue section|micrograph|stained slide|epitheli|endotheli|glomerul|intercalated disc|sarcomere|myocyte|squamous|columnar|cuboidal|cytoarchitect|cytolog|smear)\b/i;

const GROSS_ANATOMY_PATTERN =
  /\b(gross anatom|anatomical dissection|cadaver|organ system|organ dissection|circle of willis|brachial plexus|mediastinum|coronary arter|cranial nerve|netter|medical atlas|gross specimen)\b/i;

const CELLULAR_MICROSCOPY_PATTERN =
  /\b(electron microscop|electron micrograph|tem\b|sem\b|transmission electron|scanning electron|ultrastructur|mitochondri.*cristae|endoplasmic reticulum|golgi apparatus|synaptic vesicle|cilia axoneme)\b/i;

const PHYSIOLOGY_TRACE_PATTERN =
  /\b(ecg\b|ekg\b|electrocardiogram|rhythm strip|lead ii|lead [iv]|p wave|qrs|t wave|action potential|depolarization trace|eeg\b|spirometr|flow-volume loop)\b/i;

const CLINICAL_PATHOLOGY_PATTERN =
  /\b(clinical presentation|clinical photograph|dermatolog|skin lesion|erythema|melanoma|rash|ophthalmolog|fundoscop|retinal photograph|optic disc|jaundice|cyanosis)\b/i;

/**
 * Detects the medical or scientific modality of a visual stimulus.
 * Checks explicit model/schema attributes first, then falls back to calibrated regex pattern matching.
 *
 * @param {object|null} question - Question object.
 * @param {string} [rawDescription=''] - Description or caption for the figure.
 * @param {boolean} [isSvg=false] - Whether the visual stimulus is an inline SVG.
 * @returns {string} Detected modality key.
 */
export function detectVisualModality(question = null, rawDescription = '', isSvg = false) {
  const explicit = (
    question?.visual_medical_category ||
    question?.image_modality ||
    question?.stage_outcomes?.visual_stimulus?.modality ||
    question?.stage_outcomes?.passage_visual_stimulus?.modality ||
    ''
  ).toLowerCase();

  if (explicit) return explicit;

  const textToScan = `${rawDescription || ''} ${question?.question_stem || ''}`.toLowerCase();

  if (RADIOLOGY_PATTERN.test(textToScan)) return 'radiology';
  if (CELLULAR_MICROSCOPY_PATTERN.test(textToScan)) return 'cellular_microscopy';
  if (HISTOLOGY_PATTERN.test(textToScan)) return 'histology';
  if (GROSS_ANATOMY_PATTERN.test(textToScan)) return 'gross_anatomy';
  if (PHYSIOLOGY_TRACE_PATTERN.test(textToScan)) return 'physiology_trace';
  if (CLINICAL_PATHOLOGY_PATTERN.test(textToScan)) return 'clinical_pathology';

  return isSvg ? 'svg_diagram' : 'scientific_diagram';
}

/**
 * Resolves metadata (label, badgeClass, and isDarkContainer) for a detected modality.
 *
 * @param {string} detectedModality - Modality key returned from detectVisualModality.
 * @param {boolean} [isSvg=false] - Whether the stimulus is an inline SVG.
 * @returns {{ label: string, badgeClass: string, isDarkContainer: boolean }}
 */
export function getModalityMetadata(detectedModality, isSvg = false) {
  switch (detectedModality) {
    case 'radiology':
      return {
        label: 'Radiology (X-Ray / CT / MRI)',
        badgeClass: 'badge-cyan',
        isDarkContainer: true
      };
    case 'histology':
      return {
        label: 'Histopathology (H&E)',
        badgeClass: 'badge-purple',
        isDarkContainer: false
      };
    case 'gross_anatomy':
      return {
        label: 'Gross Anatomy Specimen',
        badgeClass: 'badge-amber',
        isDarkContainer: false
      };
    case 'cellular_microscopy':
      return {
        label: 'Electron Microscopy (TEM/SEM)',
        badgeClass: 'badge-indigo',
        isDarkContainer: true
      };
    case 'physiology_trace':
      return {
        label: 'Physiology / ECG Trace',
        badgeClass: 'badge-rose',
        isDarkContainer: false
      };
    case 'clinical_pathology':
      return {
        label: 'Clinical Pathology Photograph',
        badgeClass: 'badge-emerald',
        isDarkContainer: false
      };
    case 'svg_diagram':
      return {
        label: 'SVG Vector Diagram',
        badgeClass: 'badge-purple',
        isDarkContainer: false
      };
    default:
      return {
        label: isSvg ? 'SVG Vector Diagram' : 'Scientific Figure',
        badgeClass: 'badge-neutral',
        isDarkContainer: false
      };
  }
}
