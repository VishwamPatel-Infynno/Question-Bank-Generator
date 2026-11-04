import { X } from 'lucide-react';
import { useFocusTrap } from '../../hooks';

/**
 * Modal
 *
 * Enterprise-grade, WCAG AA compliant reusable modal dialog primitive.
 * Enforces keyboard focus trapping (Tab / Shift+Tab), Escape key dismissal,
 * backdrop click dismissal, smooth scale-in animation, and dual-theme styling.
 *
 * @param {Object} props
 * @param {boolean} props.isOpen - Whether the modal is visible.
 * @param {() => void} props.onClose - Callback triggered to close the modal.
 * @param {string} [props.title] - Optional title for the header.
 * @param {string} [props.subtitle] - Optional subtitle/description under the title.
 * @param {React.ReactNode} [props.icon] - Optional icon element to display in the header.
 * @param {string} [props.maxWidth='560px'] - Max width of the modal card (e.g. '480px', '560px', '820px').
 * @param {boolean} [props.isProcessing=false] - When true, disables closing and dismiss interactions.
 * @param {React.ReactNode} [props.children] - Modal body content.
 * @param {React.ReactNode} [props.footer] - Optional modal footer content.
 * @param {string} [props.ariaLabelledBy='modal-dialog-title'] - Accessibility label ID.
 * @param {string} [props.className] - Optional extra class name for the card.
 * @param {Object} [props.cardStyle] - Optional inline style overrides for the card.
 */
const DEFAULT_CARD_STYLE = Object.freeze({});

export default function Modal({
  isOpen,
  onClose,
  title,
  subtitle,
  icon,
  maxWidth = '560px',
  isProcessing = false,
  children,
  footer,
  ariaLabelledBy = 'modal-dialog-title',
  className = '',
  cardStyle = DEFAULT_CARD_STYLE
}) {
  const modalRef = useFocusTrap({ isActive: Boolean(isOpen), onClose });

  if (!isOpen) return null;

  const handleBackdropClick = (e) => {
    if (e.target === e.currentTarget && !isProcessing && onClose) {
      onClose();
    }
  };

  const sizeClass = maxWidth === '420px' ? 'modal-sm'
    : maxWidth === '520px' || maxWidth === '560px' ? 'modal-md'
    : maxWidth === '720px' ? 'modal-lg'
    : maxWidth === '900px' ? 'modal-xl'
    : '';
  const customMaxWidthStyle = sizeClass ? {} : (maxWidth ? { maxWidth } : {});

  return (
    <div
      className="modal-backdrop-theme"
      role="dialog"
      aria-modal="true"
      aria-labelledby={title ? ariaLabelledBy : undefined}
      onClick={handleBackdropClick}
    >
      <div
        ref={modalRef}
        className={`modal-card-theme modal-card-base ${sizeClass || 'modal-md'} ${className}`.trim()}
        onClick={(e) => e.stopPropagation()}
        style={{
          ...customMaxWidthStyle,
          ...cardStyle
        }}
      >
        {/* Modal Header */}
        {(title || onClose) && (
          <div className="modal-header modal-header-wrap">
            <div className="modal-title-group">
              {icon && (
                <div className="modal-header-icon-wrap">
                  {icon}
                </div>
              )}
              <div className="modal-title-text-box">
                {title && (
                  <h2
                    id={ariaLabelledBy}
                    className="modal-title modal-title-text"
                  >
                    {title}
                  </h2>
                )}
                {subtitle && (
                  <p className="modal-subtitle-text">
                    {subtitle}
                  </p>
                )}
              </div>
            </div>

            {onClose && (
              <button
                type="button"
                onClick={onClose}
                disabled={isProcessing}
                className="btn-ghost modal-close-btn"
                title="Close modal (Escape)"
                aria-label="Close modal"
              >
                <X size={18} />
              </button>
            )}
          </div>
        )}

        {/* Modal Body */}
        <div className="modal-body modal-body-wrap">
          {children}
        </div>

        {/* Modal Footer */}
        {footer && (
          <div className="modal-footer modal-footer-wrap">
            {footer}
          </div>
        )}
      </div>
    </div>
  );
}

