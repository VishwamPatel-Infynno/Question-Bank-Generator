import { getQuestionVisual, detectVisualModality, getModalityMetadata } from '../../utils';
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
    return detectVisualModality(question, rawDescription, isSvg);
  }, [question, rawDescription, isSvg]);

  const modalityMeta = useMemo(() => {
    return getModalityMetadata(detectedModality, isSvg);
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
              className={`badge ${modalityMeta.badgeClass} stimulus-type-badge`}
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
                aria-label="Copy raw SVG vector markup to clipboard"
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
              aria-label="Expand diagram to fullscreen inspect mode"
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
          onKeyDown={(e) => {
            if (e.key === 'Enter' || e.key === ' ') {
              e.preventDefault();
              setIsLightboxOpen(true);
            }
          }}
          className="stimulus-stage-light"
          role="button"
          tabIndex={0}
          title="Click or press Enter to expand full resolution diagram"
          aria-label="Click or press Enter to expand full resolution diagram"
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
        badgeClass={modalityMeta.badgeClass}
        onCopySvg={handleCopySvg}
        copiedSvg={copiedSvg}
      />
    </>
  );
}
