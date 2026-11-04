import { useState, useEffect, useCallback, memo } from 'react';
import {
  ZoomIn,
  ZoomOut,
  RotateCcw,
  Check,
  X,
  FileCode
} from 'lucide-react';

/**
 * VisualStimulusLightboxModal:
 * Fullscreen lightbox modal for inspecting MCAT visual diagrams and figures with zoom and pan controls.
 *
 * @param {Object} props
 * @param {boolean} props.isOpen - Whether the modal is visible.
 * @param {() => void} props.onClose - Dismiss callback.
 * @param {string|null} [props.svgContent] - SVG markup string.
 * @param {string|null} [props.imageUrl] - Image URL.
 * @param {string} [props.rawDescription] - Figure description / caption.
 * @param {string} [props.visualType] - Label for diagram type badge.
 * @param {() => void} [props.onCopySvg] - Copy SVG callback.
 * @param {boolean} [props.copiedSvg] - Copy confirmation state.
 * @returns {JSX.Element|null}
 */
function VisualStimulusLightboxModal({
  isOpen,
  onClose,
  svgContent = null,
  imageUrl = null,
  rawDescription = '',
  visualType = 'Figure',
  onCopySvg = null,
  copiedSvg = false
}) {
  const [zoomLevel, setZoomLevel] = useState(1.0);
  const isSvg = Boolean(svgContent);

  // Handle escape key to close lightbox
  const handleKeyDown = useCallback(
    (e) => {
      if (e.key === 'Escape' && isOpen) {
        onClose();
        setZoomLevel(1.0);
      }
    },
    [isOpen, onClose]
  );

  useEffect(() => {
    if (isOpen) {
      window.addEventListener('keydown', handleKeyDown);
      return () => window.removeEventListener('keydown', handleKeyDown);
    }
  }, [isOpen, handleKeyDown]);

  if (!isOpen) {
    return null;
  }

  const handleZoomIn = (e) => {
    e?.stopPropagation();
    setZoomLevel((prev) => Math.min(2.5, Number((prev + 0.25).toFixed(2))));
  };

  const handleZoomOut = (e) => {
    e?.stopPropagation();
    setZoomLevel((prev) => Math.max(0.5, Number((prev - 0.25).toFixed(2))));
  };

  const handleResetZoom = (e) => {
    e?.stopPropagation();
    setZoomLevel(1.0);
  };

  const handleClose = () => {
    onClose();
    setZoomLevel(1.0);
  };

  return (
    <div
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        backgroundColor: 'rgba(5, 8, 15, 0.88)',
        backdropFilter: 'blur(6px)',
        zIndex: 9999,
        display: 'flex',
        flexDirection: 'column',
        padding: '24px',
        animation: 'fadeIn 0.15s ease-out'
      }}
      onClick={handleClose}
    >
      {/* Modal Header Strip */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          paddingBottom: '16px',
          borderBottom: '1px solid var(--border-light)',
          background: 'transparent'
        }}
        onClick={(e) => e.stopPropagation()}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <span style={{ fontSize: '0.9rem', fontWeight: 700, color: 'var(--text-primary)' }}>
            Figure Inspector
          </span>
          <span className="badge badge-purple" style={{ fontSize: '0.675rem' }}>
            {visualType}
          </span>
          <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
            Zoom: {Math.round(zoomLevel * 100)}%
          </span>
        </div>

        {/* Modal Controls */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <button
            type="button"
            onClick={handleZoomIn}
            className="btn-secondary"
            style={{ padding: '6px 12px', fontSize: '0.75rem', gap: '4px' }}
            title="Zoom in (+25%)"
          >
            <ZoomIn size={13} />
            <span>Zoom In</span>
          </button>

          <button
            type="button"
            onClick={handleZoomOut}
            className="btn-secondary"
            style={{ padding: '6px 12px', fontSize: '0.75rem', gap: '4px' }}
            title="Zoom out (-25%)"
          >
            <ZoomOut size={13} />
            <span>Zoom Out</span>
          </button>

          <button
            type="button"
            onClick={handleResetZoom}
            className="btn-secondary"
            style={{ padding: '6px 12px', fontSize: '0.75rem', gap: '4px' }}
            title="Reset zoom to 100%"
          >
            <RotateCcw size={13} />
            <span>Reset</span>
          </button>

          {isSvg && onCopySvg && (
            <button
              type="button"
              onClick={onCopySvg}
              className="btn-secondary"
              style={{ padding: '6px 12px', fontSize: '0.75rem', gap: '4px' }}
              title="Copy SVG markup"
            >
              {copiedSvg ? <Check size={13} color="var(--status-success)" /> : <FileCode size={13} />}
              <span>{copiedSvg ? 'Copied' : 'Copy SVG'}</span>
            </button>
          )}

          <button
            type="button"
            onClick={handleClose}
            className="btn-secondary"
            style={{ padding: '6px 12px', fontSize: '0.75rem', gap: '4px' }}
            title="Close lightbox (Esc)"
          >
            <X size={14} />
            <span>Close</span>
          </button>
        </div>
      </div>

      {/* Modal Content Stage */}
      <div
        style={{
          flex: 1,
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'center',
          alignItems: 'center',
          overflow: 'auto',
          padding: '20px'
        }}
        onClick={(e) => e.stopPropagation()}
      >
        <div
          style={{
            background: '#ffffff',
            borderRadius: 'var(--radius-md)',
            padding: '24px',
            boxShadow: 'var(--shadow-lg)',
            transform: `scale(${zoomLevel})`,
            transformOrigin: 'center center',
            transition: 'transform 0.15s ease-out',
            maxWidth: '90vw',
            maxHeight: '75vh',
            display: 'flex',
            justifyContent: 'center',
            alignItems: 'center',
            overflow: 'auto'
          }}
        >
          {isSvg ? (
            <div
              style={{
                width: '760px',
                maxWidth: '100%',
                display: 'flex',
                justifyContent: 'center'
              }}
              dangerouslySetInnerHTML={{ __html: svgContent }}
            />
          ) : (
            <img
              src={imageUrl}
              alt={rawDescription || 'Visual Stimulus'}
              style={{
                maxWidth: '85vw',
                maxHeight: '70vh',
                objectFit: 'contain'
              }}
            />
          )}
        </div>

        {/* Modal Caption */}
        {rawDescription && (
          <div
            style={{
              marginTop: '16px',
              color: 'var(--text-primary)',
              fontSize: '0.85rem',
              fontWeight: 500,
              textAlign: 'center',
              background: 'var(--bg-surface-elevated)',
              padding: '6px 16px',
              borderRadius: 'var(--radius-full)',
              border: '1px solid var(--border-light)'
            }}
          >
            Fig: {rawDescription}
          </div>
        )}
      </div>
    </div>
  );
}

export default memo(VisualStimulusLightboxModal);
