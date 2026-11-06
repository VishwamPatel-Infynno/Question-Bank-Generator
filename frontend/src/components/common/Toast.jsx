import React, { useEffect } from 'react';
import { CheckCircle2, AlertCircle, Info, X } from 'lucide-react';

function ToastItem({ toast, onDismiss }) {
  useEffect(() => {
    const timer = setTimeout(() => {
      onDismiss(toast.id);
    }, toast.duration || 4000);
    return () => clearTimeout(timer);
  }, [toast, onDismiss]);

  const icons = {
    success: <CheckCircle2 size={18} color="var(--status-success)" />,
    error: <AlertCircle size={18} color="var(--status-danger)" />,
    info: <Info size={18} color="var(--brand-primary)" />
  };

  const toastTypeClass = toast.type || 'info';

  return (
    <div className={`toast-card ${toastTypeClass}`}>
      <div className="toast-content-group">
        {icons[toast.type] || icons.info}
        <div>
          {toast.title && (
            <div className="toast-title">
              {toast.title}
            </div>
          )}
          <div className="toast-message">
            {toast.message}
          </div>
        </div>
      </div>

      <div className="toast-actions-group">
        {toast.action && (
          <button
            type="button"
            onClick={(e) => {
              e.stopPropagation();
              toast.action.onClick?.();
              onDismiss(toast.id);
            }}
            className="btn-primary toast-action-btn"
          >
            {toast.action.label}
          </button>
        )}

        <button
          onClick={() => onDismiss(toast.id)}
          className="toast-close-btn"
          title="Dismiss notification"
          aria-label="Dismiss notification"
        >
          <X size={14} />
        </button>
      </div>
    </div>
  );
}

export function ToastContainer({ toasts, onDismiss }) {
  if (!toasts || toasts.length === 0) return null;

  return (
    <div className="toast-viewport" role="status" aria-live="polite">
      {toasts.map((toast) => (
        <ToastItem key={toast.id} toast={toast} onDismiss={onDismiss} />
      ))}
    </div>
  );
}
