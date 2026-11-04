import { useState } from 'react';
import {
  Maximize2,
  Copy,
  Check,
  Image as ImageIcon
} from 'lucide-react';
import VisualStimulusLightboxModal from './VisualStimulusLightboxModal';

/**
 * VisualStimulusViewer:
 * Publication-grade renderer for AAMC MCAT visual stimulus diagrams (Vector SVG & AI FLUX Images).
 * Supports inline display, compact list thumbnail mode, click-to-zoom lightbox modal,
 * and inline description editing in Quick Edit mode.
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
  const [copiedSvg, setCopiedSvg] = useState(false);

  // Extract visual data from direct props or question or stage outcomes (supporting both discrete and passage stimuli)
  const svgContent =
    directImageSvg ||
    question?.image_svg ||
    question?.stage_outcomes?.visual_stimulus?.image_svg ||
    question?.stage_outcomes?.passage_visual_stimulus?.image_svg ||
    null;
  const imageUrl =
    directImageUrl ||
    question?.image_url ||
    question?.stage_outcomes?.visual_stimulus?.image_url ||
    question?.stage_outcomes?.passage_visual_stimulus?.image_url ||
    null;
  const rawDescription = isEditing
    ? (editedDescription ?? directImageDescription ?? question?.image_description ?? '')
    : (directImageDescription ||
       question?.image_description ||
       question?.stage_outcomes?.visual_stimulus?.image_description ||
       question?.stage_outcomes?.passage_visual_stimulus?.image_description ||
       '');

  if (!svgContent && !imageUrl) {
    return null;
  }

  const isSvg = Boolean(svgContent);
  const visualType = isSvg ? 'SVG Vector Diagram' : 'Scientific Figure';

  const handleCopySvg = (e) => {
    e?.stopPropagation();
    if (!svgContent) return;
    navigator.clipboard.writeText(svgContent);
    setCopiedSvg(true);
    setTimeout(() => setCopiedSvg(false), 2000);
  };

  // Compact Thumbnail View for list cards
  if (compact) {
    return (
      <div
        style={{
          background: '#ffffff',
          border: '1px solid var(--border-medium)',
          borderRadius: 'var(--radius-sm)',
          overflow: 'hidden',
          padding: '6px',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          gap: '4px',
          maxHeight: '120px'
        }}
      >
        <div style={{ width: '100%', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <span style={{ fontSize: '0.625rem', fontWeight: 700, color: '#0f172a', textTransform: 'uppercase' }}>
            Figure / Diagram
          </span>
          <span className="badge badge-purple" style={{ fontSize: '0.575rem', padding: '1px 5px' }}>
            {isSvg ? 'SVG' : 'Diagram'}
          </span>
        </div>
        <div
          style={{ width: '100%', maxHeight: '85px', overflow: 'hidden', display: 'flex', justifyContent: 'center' }}
        >
          {isSvg ? (
            <div
              style={{ width: '100%', height: '100%', display: 'flex', justifyContent: 'center', pointerEvents: 'none' }}
              dangerouslySetInnerHTML={{ __html: svgContent }}
            />
          ) : (
            <img
              src={imageUrl}
              alt={rawDescription || 'Figure diagram'}
              style={{ maxHeight: '85px', maxWidth: '100%', objectFit: 'contain' }}
            />
          )}
        </div>
      </div>
    );
  }

  // Full Interactive Inline Viewer
  return (
    <>
      <div
        className="visual-stimulus-card"
        style={{
          background: 'var(--bg-surface-elevated)',
          border: '1px solid var(--border-light)',
          borderRadius: 'var(--radius-md)',
          padding: '14px 16px',
          display: 'flex',
          flexDirection: 'column',
          gap: '10px'
        }}
      >
        {/* Stimulus Header Bar */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            flexWrap: 'wrap',
            gap: '8px'
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span
              style={{
                fontSize: '0.725rem',
                fontWeight: 700,
                color: 'var(--text-muted)',
                textTransform: 'uppercase',
                letterSpacing: '0.5px',
                display: 'flex',
                alignItems: 'center',
                gap: '5px'
              }}
            >
              <ImageIcon size={13} color="var(--brand-primary)" />
              {headerTitle || 'Figure / Diagram'}
            </span>
            {badgeExtra}
            <span
              className="badge badge-purple"
              style={{ fontSize: '0.625rem', padding: '2px 6px', fontWeight: 600 }}
            >
              {visualType}
            </span>
          </div>

          {/* Action Toolbar */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            {isSvg && (
              <button
                type="button"
                onClick={handleCopySvg}
                className="btn-secondary"
                style={{ padding: '3px 8px', fontSize: '0.675rem', gap: '4px' }}
                title="Copy raw SVG vector markup to clipboard"
              >
                {copiedSvg ? <Check size={11} color="var(--status-success)" /> : <Copy size={11} />}
                <span>{copiedSvg ? 'Copied' : 'Copy SVG'}</span>
              </button>
            )}

            <button
              type="button"
              onClick={() => setIsLightboxOpen(true)}
              className="btn-secondary"
              style={{ padding: '3px 8px', fontSize: '0.675rem', gap: '4px' }}
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
          style={{
            background: '#ffffff',
            border: '1px solid #e2e8f0',
            borderRadius: 'var(--radius-sm)',
            padding: '12px',
            display: 'flex',
            justifyContent: 'center',
            alignItems: 'center',
            minHeight: '220px',
            maxHeight: '380px',
            overflow: 'hidden',
            cursor: 'zoom-in',
            position: 'relative'
          }}
          title="Click to expand full resolution diagram"
        >
          {isSvg ? (
            <div
              style={{
                width: '100%',
                maxHeight: '350px',
                display: 'flex',
                justifyContent: 'center',
                alignItems: 'center'
              }}
              dangerouslySetInnerHTML={{ __html: svgContent }}
            />
          ) : (
            <img
              src={imageUrl}
              alt={rawDescription || 'AAMC MCAT Stimulus Diagram'}
              style={{
                maxWidth: '100%',
                maxHeight: '350px',
                objectFit: 'contain',
                borderRadius: '4px'
              }}
            />
          )}
        </div>

        {/* Stimulus Caption / Description */}
        <div>
          {isEditing ? (
            <div>
              <label
                style={{
                  display: 'block',
                  fontSize: '0.65rem',
                  fontWeight: 600,
                  color: 'var(--text-muted)',
                  marginBottom: '2px'
                }}
              >
                Diagram Description / Clinical Caption:
              </label>
              <input
                type="text"
                value={editedDescription}
                onChange={(e) => onDescriptionChange && onDescriptionChange(e.target.value)}
                placeholder="e.g. Set A vs Set B geometric pattern rules..."
                style={{ width: '100%', fontSize: '0.8rem', padding: '4px 8px' }}
              />
            </div>
          ) : (
            rawDescription && (
              <div
                style={{
                  fontSize: '0.725rem',
                  fontStyle: 'italic',
                  color: 'var(--text-muted)',
                  textAlign: 'center',
                  paddingTop: '2px'
                }}
              >
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
