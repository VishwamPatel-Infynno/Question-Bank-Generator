import { getQuestionVisual } from '../../utils';
import { useState, useMemo } from 'react';
import { useCopyToClipboard } from '../../hooks';
import {
  Maximize2,
  Copy,
  Check,
  Image as ImageIcon
} from 'lucide-react';
import VisualStimulusLightboxModal from './VisualStimulusLightboxModal';
import SafeSvg from '../common/SafeSvg';

/**
 * VisualStimulusViewer:
 * Publication-grade renderer for AAMC MCAT visual stimulus diagrams & medical images
 * (Radiology X-ray/CT/MRI, Histopathology H&E, Gross Anatomy, Cellular Electron Microscopy,
 * Physiological ECG Traces, Clinical Pathology, and Vector SVGs).
 * Features modality badging, high-contrast viewing, and click-to-zoom fullscreen inspection.
 */
export default function VisualStimulusViewer({
  question = null,
  imageUrl: directImageUrl = null,
  imageSvg: directImageSvg = null,
  imageDescription: directImageDescription = '',
  headerTitle = null,
  badgeExtra = null,
  actionsExtra = null,
  isEditing = false,
  editedDescription = '',
  onDescriptionChange = null,
  compact = false
}) {
  const [isLightboxOpen, setIsLightboxOpen] = useState(false);
  const { copiedKey, copy } = useCopyToClipboard();
  const copiedSvg = copiedKey === true;

  // Extract visual data from direct props or question or stage outcomes (supporting both discrete and passage stimuli)
  const visual = getQuestionVisual(question);
  const svgContent = directImageSvg || visual.svg || null;
  const imageUrl = directImageUrl || visual.url || null;
  const rawDescription = isEditing
    ? (editedDescription ?? directImageDescription ?? question?.image_description ?? '')
    : (directImageDescription || visual.description || question?.visual_clinical_description || '');

  const isSvg = Boolean(svgContent);

  // Intelligent Medical Modality Classification & Visual Metadata
  const detectedModality = useMemo(() => {
    const explicit = (
      question?.visual_medical_category ||
      question?.image_modality ||
      question?.stage_outcomes?.visual_stimulus?.modality ||
      question?.stage_outcomes?.passage_visual_stimulus?.modality ||
      ''
    ).toLowerCase();

    if (explicit) return explicit;

    const textToScan = `${rawDescription} ${question?.question_stem || ''}`.toLowerCase();
    if (/\b(x-ray|xray|radiograph|radiography|chest film|ct scan|computed tomography|mri|magnetic resonance|t1|t2|flair|ultrasound|sonogram|fluoroscopy|pet scan|hounsfield|axial slice|coronal section)\b/i.test(textToScan)) {
      return 'radiology';
    }
    if (/\b(histolog|histopatholog|h&e|hematoxylin|eosin|biopsy|tissue section|micrograph|stained slide|epitheli|endotheli|glomerul|intercalated disc|sarcomere|myocyte|squamous|columnar|cuboidal|cytoarchitect|cytolog|smear)\b/i.test(textToScan)) {
      return 'histology';
    }
    if (/\b(gross anatom|anatomical dissection|cadaver|organ system|organ dissection|circle of willis|brachial plexus|mediastinum|coronary arter|cranial nerve|netter|medical atlas|gross specimen)\b/i.test(textToScan)) {
      return 'gross_anatomy';
    }
    if (/\b(electron microscop|electron micrograph|tem\b|sem\b|transmission electron|scanning electron|ultrastructur|mitochondri.*cristae|endoplasmic reticulum|golgi apparatus|synaptic vesicle|cilia axoneme)\b/i.test(textToScan)) {
      return 'cellular_microscopy';
    }
    if (/\b(ecg\b|ekg\b|electrocardiogram|rhythm strip|lead ii|lead [iv]|p wave|qrs|t wave|action potential|depolarization trace|eeg\b|spirometr|flow-volume loop)\b/i.test(textToScan)) {
      return 'physiology_trace';
    }
    if (/\b(clinical presentation|clinical photograph|dermatolog|skin lesion|erythema|melanoma|rash|ophthalmolog|fundoscop|retinal photograph|optic disc|jaundice|cyanosis)\b/i.test(textToScan)) {
      return 'clinical_pathology';
    }
    return isSvg ? 'svg_diagram' : 'scientific_diagram';
  }, [question, rawDescription, isSvg]);

  const modalityMeta = useMemo(() => {
    switch (detectedModality) {
      case 'radiology':
        return {
          label: 'Radiology (X-Ray / CT / MRI)',
          badgeStyle: { background: 'rgba(59, 130, 246, 0.16)', color: '#60a5fa', border: '1px solid rgba(59, 130, 246, 0.32)' },
          isDarkContainer: true,
        };
      case 'histology':
        return {
          label: 'Histopathology (H&E)',
          badgeStyle: { background: 'rgba(236, 72, 153, 0.16)', color: '#f472b6', border: '1px solid rgba(236, 72, 153, 0.32)' },
          isDarkContainer: false,
        };
      case 'gross_anatomy':
        return {
          label: 'Gross Anatomy Specimen',
          badgeStyle: { background: 'rgba(245, 158, 11, 0.16)', color: '#fbbf24', border: '1px solid rgba(245, 158, 11, 0.32)' },
          isDarkContainer: false,
        };
      case 'cellular_microscopy':
        return {
          label: 'Electron Microscopy (TEM/SEM)',
          badgeStyle: { background: 'rgba(168, 85, 247, 0.16)', color: '#c084fc', border: '1px solid rgba(168, 85, 247, 0.32)' },
          isDarkContainer: true,
        };
      case 'physiology_trace':
        return {
          label: 'Physiology / ECG Trace',
          badgeStyle: { background: 'rgba(239, 68, 68, 0.16)', color: '#f87171', border: '1px solid rgba(239, 68, 68, 0.32)' },
          isDarkContainer: false,
        };
      case 'clinical_pathology':
        return {
          label: 'Clinical Pathology Photograph',
          badgeStyle: { background: 'rgba(16, 185, 129, 0.16)', color: '#34d399', border: '1px solid rgba(16, 185, 129, 0.32)' },
          isDarkContainer: false,
        };
      case 'svg_diagram':
        return {
          label: 'SVG Vector Diagram',
          badgeStyle: {},
          isDarkContainer: false,
        };
      default:
        return {
          label: isSvg ? 'SVG Vector Diagram' : 'Scientific Figure',
          badgeStyle: {},
          isDarkContainer: false,
        };
    }
  }, [detectedModality, isSvg]);

  if (!svgContent && !imageUrl) {
    return null;
  }

  const visualType = modalityMeta.label;

  const handleCopySvg = (e) => {
    e?.stopPropagation();
    if (!svgContent) return;
    copy(svgContent);
  };

  // Compact Thumbnail View for list cards
  if (compact) {
    return (
      <div className="stimulus-compact-box">
        <div className="stimulus-compact-header">
          <span className="stimulus-compact-title">
            Figure / Diagram
          </span>
          <span className="badge badge-purple stimulus-compact-badge">
            {isSvg ? 'SVG' : 'Diagram'}
          </span>
        </div>
        <div className="stimulus-compact-preview">
          {isSvg ? (
            <SafeSvg className="stimulus-svg-wrap" svg={svgContent} />
          ) : (
            <img
              src={imageUrl}
              alt={rawDescription || 'Figure diagram'}
              className="stimulus-compact-img"
            />
          )}
        </div>
      </div>
    );
  }

  // Full Interactive Inline Viewer
  return (
    <>
      <div className="stimulus-card">
        {/* Stimulus Header Bar */}
        <div className="stimulus-header">
          <div className="stimulus-title-wrap">
            <span className="stimulus-title-label">
              <ImageIcon size={13} color="var(--brand-primary)" />
              {headerTitle || 'Figure / Diagram'}
            </span>
            {badgeExtra}
            <span
              className="badge badge-purple stimulus-type-badge"
              style={modalityMeta.badgeStyle}
            >
              {visualType}
            </span>
          </div>

          {/* Action Toolbar */}
          <div className="stimulus-toolbar">
            {isSvg && (
              <button
                type="button"
                onClick={handleCopySvg}
                className="btn-secondary stimulus-tool-btn"
                title="Copy raw SVG vector markup to clipboard"
              >
                {copiedSvg ? <Check size={11} color="var(--status-success)" /> : <Copy size={11} />}
                <span>{copiedSvg ? 'Copied' : 'Copy SVG'}</span>
              </button>
            )}

            <button
              type="button"
              onClick={() => setIsLightboxOpen(true)}
              className="btn-secondary stimulus-tool-btn"
              title="Expand diagram to fullscreen inspect mode"
            >
              <Maximize2 size={11} />
              <span>Fullscreen</span>
            </button>

            {actionsExtra}
          </div>
        </div>

        {/* Visual Render Container (Always Light-Themed for Standard Psychometric Contrast) */}
        <div
          onClick={() => setIsLightboxOpen(true)}
          className="stimulus-stage-light"
          title="Click to expand full resolution diagram"
        >
          {isSvg ? (
            <SafeSvg className="stimulus-svg-wrap" svg={svgContent} />
          ) : (
            <img
              src={imageUrl}
              alt={rawDescription || 'AAMC MCAT Stimulus Diagram'}
              className="stimulus-img"
            />
          )}
        </div>

        {/* Stimulus Caption / Description */}
        <div>
          {isEditing ? (
            <div>
              <label className="stimulus-caption-label">
                Diagram Description / Clinical Caption:
              </label>
              <input
                type="text"
                value={editedDescription}
                onChange={(e) => onDescriptionChange && onDescriptionChange(e.target.value)}
                placeholder="e.g. Set A vs Set B geometric pattern rules..."
                className="stimulus-caption-input"
              />
            </div>
          ) : (
            rawDescription && (
              <div className="stimulus-caption-text">
                Fig 1: {rawDescription}
              </div>
            )
          )}
        </div>
      </div>

      {/* Fullscreen Lightbox Modal */}
      <VisualStimulusLightboxModal
        isOpen={isLightboxOpen}
        onClose={() => setIsLightboxOpen(false)}
        svgContent={svgContent}
        imageUrl={imageUrl}
        rawDescription={rawDescription}
        visualType={visualType}
        onCopySvg={handleCopySvg}
        copiedSvg={copiedSvg}
      />
    </>
  );
}
