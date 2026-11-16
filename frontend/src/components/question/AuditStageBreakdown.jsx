import { memo } from 'react';
import { EMPTY_ARRAY } from '../../constants';
import { formatCostUsd, formatDurationMs, formatTokenCount } from '../../utils';

/**
 * AuditStageBreakdown
 *
 * Renders the Cognitive/Visual Engine cost breakdown and pipeline latency
 * timing entries per agent stage.
 */
function AuditStageBreakdown({
  totalCost = 0,
  cognitiveCost = 0,
  visualCost = 0,
  hasVisual = false,
  totalTokens = 0,
  stageTimings = EMPTY_ARRAY,
  totalDurationMs = 0
}) {
  return (
    <>
      {totalCost > 0 && (
        <div className="audit-cost-breakdown">
          <div className="audit-cost-breakdown-details">
            <span>
              <strong className="audit-engine-title">Cognitive Engine:</strong>{' '}
              {formatCostUsd(cognitiveCost)} ({formatTokenCount(totalTokens)} tokens)
            </span>
            {hasVisual && (
              <span>
                <strong className="audit-engine-title">Visual Engine:</strong>{' '}
                {formatCostUsd(visualCost)} (High-Precision Figure)
              </span>
            )}
          </div>
        </div>
      )}

      {stageTimings.length > 0 && (
        <div className="audit-cost-breakdown">
          <div className="audit-cost-breakdown-details">
            <span>
              <strong className="audit-engine-title">Pipeline latency:</strong>{' '}
              {formatDurationMs(totalDurationMs)} model time
            </span>
            {stageTimings.map((entry, idx) => (
              <span key={`${entry.agent}-${entry.iteration}-${idx}`}>
                {entry.agent}
                {entry.iteration > 1 ? ` (v${entry.iteration})` : ''}: {formatDurationMs(entry.duration_ms)}
              </span>
            ))}
          </div>
        </div>
      )}
    </>
  );
}

export default memo(AuditStageBreakdown);
