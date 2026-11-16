import { memo } from 'react';
import { EMPTY_ARRAY } from '../../constants';

/**
 * AuditMetricsGrid
 *
 * Renders the 5 high-level token and quality metric cards
 * within the Question Quality Review modal.
 */
function AuditMetricsGrid({ metrics = EMPTY_ARRAY }) {
  if (!metrics.length) return null;

  return (
    <div className="audit-metrics-grid">
      {metrics.map((m) => (
        <div key={m.label} className="audit-metric-card">
          <div className="audit-metric-label">{m.label}</div>
          <div className={`audit-metric-value ${m.tone}`}>{m.value}</div>
        </div>
      ))}
    </div>
  );
}

export default memo(AuditMetricsGrid);
