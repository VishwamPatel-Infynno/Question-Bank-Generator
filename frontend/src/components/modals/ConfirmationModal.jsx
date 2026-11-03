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

  const accentColor = isDanger
    ? 'var(--status-danger, #f43f5e)'
    : isWarning
    ? 'var(--status-warning, #f59e0b)'
    : 'var(--brand-primary, #335ACF)';

  const accentBg = isDanger
    ? 'rgba(244, 63, 94, 0.1)'
    : isWarning
    ? 'rgba(245, 158, 11, 0.1)'
    : 'rgba(51, 90, 207, 0.1)';

  const accentBorder = isDanger
    ? 'rgba(244, 63, 94, 0.3)'
    : isWarning
    ? 'rgba(245, 158, 11, 0.3)'
    : 'rgba(51, 90, 207, 0.3)';

  const confirmBtnBg = isDanger
    ? '#e11d48'
    : isWarning
    ? '#d97706'
    : 'var(--brand-primary, #335ACF)';

  const iconElement = (
    <div
      style={{
        width: '36px',
        height: '36px',
        borderRadius: 'var(--radius-md, 10px)',
        background: accentBg,
        border: `1px solid ${accentBorder}`,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        color: accentColor,
        flexShrink: 0
      }}
    >
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
        className="btn-secondary"
        style={{
          padding: '8px 16px',
          fontSize: '0.825rem',
          fontWeight: 600,
          cursor: isProcessing ? 'not-allowed' : 'pointer',
          opacity: isProcessing ? 0.6 : 1
        }}
      >
        {cancelLabel}
      </button>

      <button
        type="button"
        id="btn-confirm-action"
        onClick={onConfirm}
        disabled={isProcessing}
        style={{
          padding: '8px 18px',
          fontSize: '0.825rem',
          fontWeight: 600,
          color: '#ffffff',
          backgroundColor: confirmBtnBg,
          border: `1px solid ${accentBorder}`,
          borderRadius: 'var(--radius-sm, 8px)',
          cursor: isProcessing ? 'not-allowed' : 'pointer',
          display: 'inline-flex',
          alignItems: 'center',
          gap: '8px',
          boxShadow: '0 2px 8px rgba(0, 0, 0, 0.25)',
          opacity: isProcessing ? 0.8 : 1,
          transition: 'all 0.15s ease-out'
        }}
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
      ariaLabelledBy="confirm-modal-title"
    >
      <div
        id="confirm-modal-desc"
        style={{
          fontSize: '0.875rem',
          lineHeight: 1.6,
          color: 'var(--text-secondary, #cbd5e1)'
        }}
      >
        {typeof description === 'string' ? <p style={{ margin: 0 }}>{description}</p> : description}
      </div>

      {isDanger && (
        <div
          style={{
            marginTop: '16px',
            padding: '10px 14px',
            borderRadius: 'var(--radius-sm, 8px)',
            background: 'rgba(244, 63, 94, 0.08)',
            border: '1px solid rgba(244, 63, 94, 0.2)',
            fontSize: '0.78rem',
            color: 'var(--status-danger, #f43f5e)',
            display: 'flex',
            alignItems: 'center',
            gap: '8px'
          }}
        >
          <AlertTriangle size={14} style={{ flexShrink: 0 }} />
          <span>This action will permanently delete these records and cannot be undone.</span>
        </div>
      )}
    </Modal>
  );
}
