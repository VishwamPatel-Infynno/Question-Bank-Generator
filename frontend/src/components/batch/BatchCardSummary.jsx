import { memo } from 'react';
import {
  Clock,
  ChevronDown,
  ChevronRight,
  Trash2,
  Square,
  RotateCcw,
  CheckCircle2,
  AlertCircle
} from 'lucide-react';
import { BATCH_STATUS, formatDifficulty, getSectionBadgeClass, getSectionShortLabel, isStoppedStatus, MCAT_SECTION_LABELS } from '../../constants';
import { formatCostUsd, formatDateTime, formatTokenCount } from '../../utils';
import { LiveStopwatch } from '../common';

function getStatusBadge(status, stageBadge = null) {
  switch (status) {
    case BATCH_STATUS.IN_PROGRESS:
      return (
        <span className="badge batch-summary-badge-inprogress">
          <span className="batch-summary-pulse-dot" />
          {stageBadge || 'In Progress'}
        </span>
      );
    case BATCH_STATUS.COMPLETED:
      return (
        <span className="badge badge-success batch-summary-status-badge">
          <CheckCircle2 size={12} />
          Completed
        </span>
      );
    case BATCH_STATUS.PARTIALLY_COMPLETED:
      return (
        <span className="badge badge-warning batch-summary-status-badge">
          <AlertCircle size={12} />
          Partially Complete
        </span>
      );
    case BATCH_STATUS.CANCELLED:
    case BATCH_STATUS.STOPPED:
      return (
        <span className="badge badge-neutral batch-summary-status-badge">
          <Square size={11} />
          Stopped
        </span>
      );
    case BATCH_STATUS.FAILED:
      return (
        <span className="badge badge-danger batch-summary-status-badge">
          <AlertCircle size={12} />
          Failed
        </span>
      );
    default:
      return (
        <span className="badge badge-neutral">
          {status || 'Pending'}
        </span>
      );
  }
}

function BatchCardSummary({
  batch,
  secColor,
  isExpanded,
  isMiniSet,
  isCompleted,
  isInProgress,
  completedJobs,
  totalJobs,
  actualTotal,
  totalTarget,
  progressPercent,
  stageInfo,
  isStopping = false,
  isRetrying = false,
  onStopBatch,
  onRetryBatch,
  onDeleteBatch
}) {
  const sectionClass = getSectionBadgeClass(batch.section);
  const stagePillClass = stageInfo.isAuditing
    ? 'auditing'
    : stageInfo.isRefilling
      ? 'refilling'
      : 'generating';

  return (
    <div className="batch-summary-row">
      {/* Left: Section color pill & Title */}
      <div className="batch-summary-left">
        <div
          className="batch-summary-accent-bar"
          style={{ background: secColor }}
        />
        <div>
          <div className="batch-summary-badges-row">
            {isMiniSet ? (
              <span className="badge badge-purple batch-summary-badge-text">
                🎯 5 Questions
              </span>
            ) : (
              <span className="badge badge-cyan batch-summary-badge-text">
                📚 50 Questions
              </span>
            )}
            <span
              className={`badge ${sectionClass} batch-summary-badge-text`}
              style={{
                background: `${secColor}15`,
                color: secColor,
                border: `1px solid ${secColor}30`
              }}
            >
              {getSectionShortLabel(batch.section) || MCAT_SECTION_LABELS[batch.section] || batch.section}
            </span>
            <span className="badge-minimal batch-summary-badge-text">
              {formatDifficulty(batch.difficulty)}
            </span>
            <span className="badge-minimal batch-summary-badge-text">
              {batch.passage_mode === 'single_passage' ? 'Passage Set' : 'Standalone'}
            </span>
          </div>
          <div className="batch-summary-title">
            {batch.subtopic || 'All Topics'}
          </div>
          <div className="batch-summary-meta">
            <Clock size={11} />
            <span>{formatDateTime(batch.created_at)}</span>
            {isInProgress && (
              <>
                <span>•</span>
                <span className="batch-summary-meta-stopwatch">
                  <span>Elapsed:</span>
                  <LiveStopwatch isRunning={true} />
                </span>
              </>
            )}
            <span>•</span>
            <span>ID: {batch.id.slice(0, 8)}</span>
          </div>
        </div>
      </div>

      {/* Center: Progress & Metrics */}
      <div className="batch-summary-center">
        <div className="batch-summary-progress-header">
          <span className="batch-summary-progress-label">
            {completedJobs} / {totalJobs} {totalJobs === 1 ? 'Set' : 'Sets'} Completed
          </span>
          <span className={`batch-summary-progress-val ${isCompleted ? 'done' : ''}`}>
            {actualTotal} / {totalTarget} Questions ({progressPercent}%)
          </span>
        </div>

        {/* Progress Bar Track */}
        <div className="batch-summary-progress-track">
          <div
            className={`batch-summary-progress-fill ${batch.status === BATCH_STATUS.FAILED ? 'failed' : isCompleted ? 'done' : ''}`}
            style={{ width: `${progressPercent}%` }}
          />
        </div>

        <div className="batch-summary-sub-metrics">
          <div className="batch-summary-sub-metrics-left">
            <span>Tokens: {formatTokenCount(batch.total_tokens)}</span>
            <span>•</span>
            <span>Cost: {formatCostUsd(batch.cost_usd)}</span>
          </div>
          <div>
            {isInProgress ? (
              <span className={`badge batch-summary-stage-pill ${stagePillClass}`}>
                {stageInfo.stageBadge}
              </span>
            ) : (
              <span className="batch-summary-stage-text">
                {stageInfo.stageBadge}
              </span>
            )}
          </div>
        </div>
      </div>

      {/* Right: Status Pill & Controls */}
      <div className="batch-summary-right">
        {getStatusBadge(batch.status, isInProgress ? stageInfo.stageBadge : null)}

        {/* Stop Batch button for in_progress runs */}
        {batch.status === BATCH_STATUS.IN_PROGRESS && (
          <button
            type="button"
            onClick={(e) => {
              e.stopPropagation();
              if (onStopBatch) onStopBatch(batch.id);
            }}
            disabled={isStopping}
            className="batch-summary-stop-btn"
            title="Stop background batch"
          >
            <Square size={11} />
            <span>{isStopping ? 'Stopping...' : 'Stop'}</span>
          </button>
        )}

        {/* Resume Sets button: strictly reserved for batches manually stopped mid-run */}
        {isStoppedStatus(batch.status) && (
          <button
            type="button"
            onClick={(e) => {
              e.stopPropagation();
              if (onRetryBatch) onRetryBatch(batch.id);
            }}
            disabled={isRetrying}
            className="batch-summary-resume-btn"
            title="Resume incomplete sets from where you stopped"
          >
            <RotateCcw size={11} />
            <span>{isRetrying ? 'Resuming...' : 'Resume Sets'}</span>
          </button>
        )}

        <button
          type="button"
          onClick={(e) => onDeleteBatch(e, batch.id)}
          className="batch-summary-del-btn"
          title="Delete batch log"
        >
          <Trash2 size={14} />
        </button>

        <div className="batch-summary-chevron">
          {isExpanded ? <ChevronDown size={18} /> : <ChevronRight size={18} />}
        </div>
      </div>
    </div>
  );
}

export default memo(BatchCardSummary);
