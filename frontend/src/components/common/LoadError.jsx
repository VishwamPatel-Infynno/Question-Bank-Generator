import { AlertTriangle } from 'lucide-react';
import EmptyState from './EmptyState';

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
    <EmptyState
      role="alert"
      icon={<AlertTriangle size={28} />}
      iconTone="load-error-icon"
      title={title}
      description={
        message || 'The server did not respond. Check that the backend is running and try again.'
      }
    >
      {onRetry && (
        <button type="button" className="btn-primary" onClick={onRetry}>
          Try again
        </button>
      )}
    </EmptyState>
  );
}
