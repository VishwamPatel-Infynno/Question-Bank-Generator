import { memo } from 'react';
import { EMPTY_ARRAY } from '../../constants';

/**
 * AuditIterationTimeline
 *
 * Renders the multi-round refinement and scoring progression timeline
 * for questions that underwent multiple self-critique/regeneration cycles.
 */
function AuditIterationTimeline({ history = EMPTY_ARRAY }) {
  if (!history || history.length <= 1) return null;

  return (
    <div className="audit-section-block">
      <h4 className="audit-section-title">
        Refinement History
      </h4>
      <div className="audit-history-timeline">
        {history.map((h, idx) => (
          <div key={h.iteration || `history-${idx}`} className="audit-history-item">
            <div className="audit-history-row">
              <span className="badge badge-cyan">Round {h.iteration}</span>
              <span className="audit-history-score">
                Score: {h.review?.total_score || 'N/A'}/100
              </span>
            </div>
            <span className="audit-history-status">
              {h.review?.passed ? '✓ Met High Quality' : 'Polished in Refinement Round'}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

export default memo(AuditIterationTimeline);
