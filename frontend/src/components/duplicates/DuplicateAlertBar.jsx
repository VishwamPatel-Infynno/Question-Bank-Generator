import { AlertTriangle, CheckCircle2, GitCompare, Loader2 } from 'lucide-react';
import { canCompare, getDuplicateState } from '../../utils';

/**
 * DuplicateAlertBar
 *
 * Inline notice shown above a question that is flagged as a duplicate or similar to another one,
 * with Compare and "Override and approve" actions. Once overridden it shows a calm note instead.
 *
 * @param {Object} props
 * @param {Object} props.question - Question record (reads duplicate_info).
 * @param {(question: Object) => void} [props.onCompare]
 * @param {(question: Object) => void} [props.onOverride]
 * @param {boolean} [props.isOverriding]
 */
export default function DuplicateAlertBar({ question, onCompare, onOverride, isOverriding = false }) {
  const { level, percent, info } = getDuplicateState(question);
  if (level === 'none') return null;

  if (level === 'overridden') {
    return (
      <div className="dup-alert-bar overridden" role="status">
        <CheckCircle2 size={14} aria-hidden="true" />
        <span className="dup-alert-text">
          You approved this question even though it looks like another one.
        </span>
      </div>
    );
  }

  const title =
    level === 'high'
      ? `This looks like a duplicate (${percent}% similar)`
      : `This is similar to another question (${percent}% similar)`;

  return (
    <div className={`dup-alert-bar ${level}`} role="alert">
      <AlertTriangle size={14} className="dup-alert-icon" aria-hidden="true" />
      <div className="dup-alert-body">
        <p className="dup-alert-title">{title}</p>
        {info?.match_reason && <p className="dup-alert-reason">{info.match_reason}</p>}
      </div>
      <div className="dup-alert-actions">
        {onCompare && canCompare(question) && (
          <button type="button" className="btn-secondary dup-alert-btn" onClick={() => onCompare(question)}>
            <GitCompare size={12} aria-hidden="true" />
            <span>Compare</span>
          </button>
        )}
        {onOverride && (
          <button
            type="button"
            className="btn-primary dup-alert-btn"
            onClick={() => onOverride(question)}
            disabled={isOverriding}
          >
            {isOverriding ? <Loader2 size={12} className="spin-animate" aria-hidden="true" /> : null}
            <span>Override and approve</span>
          </button>
        )}
      </div>
    </div>
  );
}
