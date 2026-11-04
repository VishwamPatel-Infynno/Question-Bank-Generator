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
      className="lightbox-overlay"
      onClick={handleClose}
    >
      {/* Modal Header Strip */}
      <div
        className="lightbox-header"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="lightbox-header-info">
          <span className="lightbox-header-title">
            Figure Inspector
          </span>
          <span className="badge badge-purple lightbox-type-badge">
            {visualType}
          </span>
          <span className="lightbox-zoom-indicator">
            Zoom: {Math.round(zoomLevel * 100)}%
          </span>
        </div>

        {/* Modal Controls */}
        <div className="lightbox-controls">
          <button
            type="button"
            onClick={handleZoomIn}
            className="btn-secondary lightbox-btn"
            title="Zoom in (+25%)"
          >
            <ZoomIn size={13} />
            <span>Zoom In</span>
          </button>

          <button
            type="button"
            onClick={handleZoomOut}
            className="btn-secondary lightbox-btn"
            title="Zoom out (-25%)"
          >
            <ZoomOut size={13} />
            <span>Zoom Out</span>
          </button>

          <button
            type="button"
            onClick={handleResetZoom}
            className="btn-secondary lightbox-btn"
            title="Reset zoom to 100%"
          >
            <RotateCcw size={13} />
            <span>Reset</span>
          </button>

          {isSvg && onCopySvg && (
            <button
              type="button"
              onClick={onCopySvg}
              className="btn-secondary lightbox-btn"
              title="Copy SVG markup"
            >
              {copiedSvg ? <Check size={13} color="var(--status-success)" /> : <FileCode size={13} />}
              <span>{copiedSvg ? 'Copied' : 'Copy SVG'}</span>
            </button>
          )}

          <button
            type="button"
            onClick={handleClose}
            className="btn-secondary lightbox-btn"
            title="Close lightbox (Esc)"
          >
            <X size={14} />
            <span>Close</span>
          </button>
        </div>
      </div>

      {/* Modal Content Stage */}
      <div
        className="lightbox-stage"
        onClick={(e) => e.stopPropagation()}
      >
        <div
          className="lightbox-canvas"
          style={{ transform: `scale(${zoomLevel})` }}
        >
          {isSvg ? (
            <div
              className="lightbox-svg-inner"
              dangerouslySetInnerHTML={{ __html: svgContent }}
            />
          ) : (
            <img
              src={imageUrl}
              alt={rawDescription || 'Figure or diagram'}
              className="lightbox-img"
            />
          )}
        </div>

        {/* Modal Caption */}
        {rawDescription && (
          <div className="lightbox-caption-pill">
            Fig: {rawDescription}
          </div>
        )}
      </div>
    </div>
  );
}

export default memo(VisualStimulusLightboxModal);
