import { AlertTriangle, Trash2, Info, Loader2 } from 'lucide-react';
import { Modal } from '../common';

/**
 * ConfirmationModal
 *
 * Enterprise-grade, WCAG AA compliant confirmation modal replacing raw browser window.confirm.
 * Built on the unified Modal primitive. Enforces focus trapping, Escape key dismissal,
 * dual-theme styling, contextual item counts, and loading states.
 */
export default function ConfirmationModal({
  isOpen,
  onClose,
  onConfirm,
  title = 'Confirm Action',
  description = 'Are you sure you want to proceed? This action cannot be undone.',
  confirmLabel = 'Confirm',
  cancelLabel = 'Cancel',
  variant = 'danger', // 'danger' | 'warning' | 'info'
  itemCount = null,
  itemLabel = 'item',
  isProcessing = false
}) {
  const isDanger = variant === 'danger';
  const isWarning = variant === 'warning';

  const iconElement = (
    <div className={`confirm-modal-icon-wrap ${variant}`}>
      {isDanger ? (
        <Trash2 size={18} />
      ) : isWarning ? (
        <AlertTriangle size={18} />
      ) : (
        <Info size={18} />
      )}
    </div>
  );

  const subtitle = typeof itemCount === 'number'
    ? `Target: ${itemCount} ${itemLabel}${itemCount !== 1 ? 's' : ''}`
    : undefined;

  const footer = (
    <>
      <button
        type="button"
        id="btn-cancel-confirmation"
        onClick={onClose}
        disabled={isProcessing}
        className="btn-secondary confirm-modal-cancel-btn"
      >
        {cancelLabel}
      </button>

      <button
        type="button"
        id="btn-confirm-action"
        onClick={onConfirm}
        disabled={isProcessing}
        className={`confirm-modal-action-btn ${variant}`}
      >
        {isProcessing ? (
          <>
            <Loader2 size={14} className="spin-animate" />
            <span>Processing...</span>
          </>
        ) : (
          <span>{confirmLabel}</span>
        )}
      </button>
    </>
  );

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={title}
      subtitle={subtitle}
      icon={iconElement}
      maxWidth="480px"
      isProcessing={isProcessing}
      footer={footer}
    >
      <div
        id="confirm-modal-desc"
        className="confirm-modal-desc"
      >
        {typeof description === 'string' ? <p className="confirm-modal-text-p">{description}</p> : description}
      </div>

      {isDanger && (
        <div className="confirm-modal-warning-callout">
          <AlertTriangle size={14} className="confirm-modal-warning-icon" />
          <span>This action will permanently delete these records and cannot be undone.</span>
        </div>
      )}
    </Modal>
  );
}
