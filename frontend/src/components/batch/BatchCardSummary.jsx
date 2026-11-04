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
import { MCAT_SECTION_LABELS, formatDifficulty } from '../../constants/mcat';
import { formatCostUsd, formatTokenCount } from '../../utils';
import { LiveStopwatch } from '../common';

function getStatusBadge(status, stageBadge = null) {
  switch (status) {
    case 'in_progress':
      return (
        <span className="badge batch-summary-badge-inprogress">
          <span className="batch-summary-pulse-dot" />
          {stageBadge || 'In Progress'}
        </span>
      );
    case 'completed':
      return (
        <span className="badge badge-success batch-summary-status-badge">
          <CheckCircle2 size={12} />
          Completed
        </span>
      );
    case 'partially_completed':
      return (
        <span className="badge badge-warning batch-summary-status-badge">
          <AlertCircle size={12} />
          Partially Complete
        </span>
      );
    case 'cancelled':
    case 'stopped':
      return (
        <span className="badge badge-neutral batch-summary-status-badge">
          <Square size={11} />
          Stopped
        </span>
      );
    case 'failed':
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
  const sectionClass = `badge-sec-${batch.section?.toLowerCase() || 'cp'}`;
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
              {MCAT_SECTION_LABELS[batch.section] || batch.section}
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
            <span>{new Date(batch.created_at).toLocaleString()}</span>
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
            className={`batch-summary-progress-fill ${batch.status === 'failed' ? 'failed' : isCompleted ? 'done' : ''}`}
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
        {batch.status === 'in_progress' && (
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
        {(batch.status === 'cancelled' || batch.status === 'stopped') && (
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
          className="btn-icon batch-summary-del-btn"
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
