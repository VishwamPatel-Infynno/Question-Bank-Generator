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
        className={`modal-card-theme ${className}`.trim()}
        onClick={(e) => e.stopPropagation()}
        style={{
          width: '100%',
          maxWidth,
          maxHeight: '90vh',
          display: 'flex',
          flexDirection: 'column',
          boxShadow: '0 24px 48px -12px rgba(0, 0, 0, 0.35)',
          ...cardStyle
        }}
      >
        {/* Modal Header */}
        {(title || onClose) && (
          <div
            className="modal-header"
            style={{
              padding: '18px 24px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              borderBottom: '1px solid var(--border-light, rgba(255, 255, 255, 0.08))',
              gap: '12px'
            }}
          >
            <div
              className="modal-title-group"
              style={{ display: 'flex', alignItems: 'center', gap: '12px', minWidth: 0 }}
            >
              {icon && (
                <div
                  style={{
                    width: '36px',
                    height: '36px',
                    borderRadius: 'var(--radius-sm, 6px)',
                    background: 'var(--brand-light, rgba(51, 90, 207, 0.1))',
                    border: '1px solid var(--border-brand, rgba(51, 90, 207, 0.25))',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    color: 'var(--brand-primary, #335ACF)',
                    flexShrink: 0
                  }}
                >
                  {icon}
                </div>
              )}
              <div style={{ minWidth: 0 }}>
                {title && (
                  <h2
                    id={ariaLabelledBy}
                    className="modal-title"
                    style={{
                      fontSize: '1.05rem',
                      fontWeight: 700,
                      margin: 0,
                      color: 'var(--text-primary)',
                      lineHeight: 1.3
                    }}
                  >
                    {title}
                  </h2>
                )}
                {subtitle && (
                  <p
                    style={{
                      fontSize: '0.78rem',
                      color: 'var(--text-muted)',
                      margin: '2px 0 0 0',
                      lineHeight: 1.4
                    }}
                  >
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
                className="btn-ghost"
                style={{
                  padding: '6px',
                  borderRadius: 'var(--radius-sm, 6px)',
                  color: 'var(--text-muted)',
                  cursor: isProcessing ? 'not-allowed' : 'pointer',
                  opacity: isProcessing ? 0.5 : 1
                }}
                title="Close modal (Escape)"
                aria-label="Close modal"
              >
                <X size={18} />
              </button>
            )}
          </div>
        )}

        {/* Modal Body */}
        <div
          className="modal-body"
          style={{
            padding: '24px',
            overflowY: 'auto',
            flex: 1
          }}
        >
          {children}
        </div>

        {/* Modal Footer */}
        {footer && (
          <div
            className="modal-footer"
            style={{
              padding: '16px 24px',
              borderTop: '1px solid var(--border-light, rgba(255, 255, 255, 0.08))',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'flex-end',
              gap: '10px'
            }}
          >
            {footer}
          </div>
        )}
      </div>
    </div>
  );
}

