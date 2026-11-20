import { memo } from 'react';
import { AlertTriangle, CheckCircle2, Copy } from 'lucide-react';
import { canCompare, getDuplicateState } from '../../utils';

const LEVEL_VIEW = {
  high: { cls: 'badge-rose', Icon: AlertTriangle },
  similar: { cls: 'badge-amber', Icon: Copy },
  overridden: { cls: 'badge-emerald overridden', Icon: CheckCircle2 }
};

/**
 * DuplicateRiskBadge
 *
 * Small status pill for a question's duplicate state: "Duplicate Risk (88%)", "Similar (65%)" or
 * "Overridden". Renders nothing when the question has no duplicate signal. When `onClick` is given
 * and a comparison is possible it is a button that opens the compare view.
 *
 * @param {Object} props
 * @param {Object} props.question - Question record (reads duplicate_info).
 * @param {(question: Object) => void} [props.onClick] - Opens the compare view.
 */
function DuplicateRiskBadge({ question, onClick }) {
  const { level, percent } = getDuplicateState(question);
  if (level === 'none') return null;

  const { cls, Icon } = LEVEL_VIEW[level];
  const label =
    level === 'high' ? `Duplicate Risk (${percent}%)` : level === 'similar' ? `Similar (${percent}%)` : 'Overridden';
  const className = `badge dup-risk-badge ${cls}`;
  const content = (
    <>
      <Icon size={10} aria-hidden="true" />
      <span>{label}</span>
    </>
  );

  if (onClick && canCompare(question)) {
    return (
      <button
        type="button"
        className={`${className} dup-risk-badge-btn`}
        onClick={() => onClick(question)}
        aria-label={`${label}. Compare with the original question`}
        title="Compare with the original question"
      >
        {content}
      </button>
    );
  }
  return <span className={className}>{content}</span>;
}

export default memo(DuplicateRiskBadge);
