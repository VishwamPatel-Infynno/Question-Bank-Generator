import { AlertTriangle } from 'lucide-react';

/**
 * LoadError - shown when a list failed to load, so a network or server problem is never
 * mistaken for "there is nothing here".
 * @param {Object} props
 * @param {string} props.title - What failed, e.g. "Could not load the Question Bank".
 * @param {string} [props.message] - Error detail.
 * @param {() => void} props.onRetry - Retry callback.
 */
export default function LoadError({ title, message, onRetry }) {
  return (
    <div className="view-empty-state" role="alert">
      <div className="view-empty-icon-box load-error-icon">
        <AlertTriangle size={28} />
      </div>
      <div>
        <h3 className="view-empty-title">{title}</h3>
        <p className="view-empty-desc">
          {message || 'The server did not respond. Check that the backend is running and try again.'}
        </p>
      </div>
      {onRetry && (
        <div className="view-empty-actions">
          <button type="button" className="btn-primary" onClick={onRetry}>
            Try again
          </button>
        </div>
      )}
    </div>
  );
}
