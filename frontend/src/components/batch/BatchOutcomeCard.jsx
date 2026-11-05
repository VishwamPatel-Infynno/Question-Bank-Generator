import { memo } from 'react';
import {
  CheckCircle2,
  AlertCircle,
  Square,
  Sparkles,
  ArrowRight,
  RotateCcw
} from 'lucide-react';
import { BATCH_STATUS, isStoppedStatus } from '../../constants';

function BatchOutcomeCard({
  batch,
  actualTotal,
  totalTarget,
  isCompleted,
  isRetrying = false,
  onRetryBatch,
  onNavigateToBank,
  onNavigateToValidated
}) {
  if (isCompleted) {
    return (
      <div className="batch-outcome-card completed" onClick={(e) => e.stopPropagation()}>
        <div className="batch-outcome-left">
          <div className="batch-outcome-icon success">
            <CheckCircle2 size={22} />
          </div>
          <div>
            <div className="batch-outcome-title">
              All {actualTotal} Questions Successfully Generated &amp; Verified
            </div>
            <div className="batch-outcome-subtitle">
              Questions passed the &ge; 90 quality standard and are staged in your Review Queue ready for review or publishing.
            </div>
          </div>
        </div>
        <div className="batch-outcome-actions">
          {onNavigateToValidated && (
            <button
              type="button"
              onClick={() => onNavigateToValidated()}
              className="btn-primary batch-outcome-btn-primary"
            >
              <Sparkles size={13} />
              <span>Open Review Queue ({actualTotal})</span>
              <ArrowRight size={13} />
            </button>
          )}
          {onNavigateToBank && (
            <button
              type="button"
              onClick={() => onNavigateToBank()}
              className="btn-secondary batch-outcome-btn-secondary"
            >
              View Question Bank
            </button>
          )}
        </div>
      </div>
    );
  }

  if (batch.status === BATCH_STATUS.PARTIALLY_COMPLETED) {
    return (
      <div className="batch-outcome-card warning" onClick={(e) => e.stopPropagation()}>
        <div className="batch-outcome-left">
          <div className="batch-outcome-icon warning">
            <AlertCircle size={22} />
          </div>
          <div>
            <div className="batch-outcome-title">
              {actualTotal} / {totalTarget} Questions Delivered ({Math.max(0, totalTarget - actualTotal)} Shortfall)
            </div>
            <div className="batch-outcome-subtitle">
              All 3 autonomous replenishment trials concluded. {actualTotal} valid questions were safely preserved and promoted to the Review Queue.
            </div>
          </div>
        </div>
        <div className="batch-outcome-actions">
          {onNavigateToValidated && (
            <button
              type="button"
              onClick={() => onNavigateToValidated()}
              className="btn-primary batch-outcome-btn-primary"
            >
              <span>Review Valid Questions ({actualTotal})</span>
              <ArrowRight size={13} />
            </button>
          )}
          {onNavigateToBank && (
            <button
              type="button"
              onClick={() => onNavigateToBank()}
              className="btn-secondary batch-outcome-btn-secondary"
            >
              View Question Bank
            </button>
          )}
        </div>
      </div>
    );
  }

  if (isStoppedStatus(batch.status)) {
    return (
      <div className="batch-outcome-card stopped" onClick={(e) => e.stopPropagation()}>
        <div className="batch-outcome-left">
          <div className="batch-outcome-icon stopped">
            <Square size={20} />
          </div>
          <div>
            <div className="batch-outcome-title">
              Batch Generation Paused by User
            </div>
            <div className="batch-outcome-subtitle">
              {actualTotal} / {totalTarget} questions generated and preserved safely. Incomplete sets can be resumed anytime.
            </div>
          </div>
        </div>
        <div className="batch-outcome-actions">
          {onRetryBatch && (
            <button
              type="button"
              onClick={() => onRetryBatch(batch.id)}
              disabled={isRetrying}
              className="btn-secondary batch-outcome-btn-secondary"
            >
              <RotateCcw size={12} />
              <span>{isRetrying ? 'Resuming...' : 'Resume Incomplete Sets'}</span>
            </button>
          )}
          {actualTotal > 0 && onNavigateToValidated && (
            <button
              type="button"
              onClick={() => onNavigateToValidated()}
              className="btn-primary batch-outcome-btn-secondary"
            >
              Review Generated ({actualTotal})
            </button>
          )}
        </div>
      </div>
    );
  }

  return null;
}

export default memo(BatchOutcomeCard);
