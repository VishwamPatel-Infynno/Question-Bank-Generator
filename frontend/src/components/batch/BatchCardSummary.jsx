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
        <span
          className="badge"
          style={{
            background: 'rgba(51, 90, 207, 0.15)',
            color: 'var(--brand-primary)',
            border: '1px solid rgba(51, 90, 207, 0.3)',
            display: 'inline-flex',
            alignItems: 'center',
            gap: '6px'
          }}
        >
          <span
            style={{
              width: '6px',
              height: '6px',
              borderRadius: '50%',
              background: 'var(--brand-primary)',
              animation: 'pulse 1.5s infinite'
            }}
          />
          {stageBadge || 'In Progress'}
        </span>
      );
    case 'completed':
      return (
        <span
          className="badge badge-success"
          style={{ display: 'inline-flex', alignItems: 'center', gap: '4px' }}
        >
          <CheckCircle2 size={12} />
          Completed
        </span>
      );
    case 'partially_completed':
      return (
        <span
          className="badge badge-warning"
          style={{ display: 'inline-flex', alignItems: 'center', gap: '4px' }}
        >
          <AlertCircle size={12} />
          Partially Complete
        </span>
      );
    case 'cancelled':
    case 'stopped':
      return (
        <span
          className="badge badge-neutral"
          style={{ display: 'inline-flex', alignItems: 'center', gap: '4px' }}
        >
          <Square size={11} />
          Stopped
        </span>
      );
    case 'failed':
      return (
        <span
          className="badge badge-danger"
          style={{ display: 'inline-flex', alignItems: 'center', gap: '4px' }}
        >
          <AlertCircle size={12} />
          Failed
        </span>
      );
    default:
      return (
        <span className="badge badge-neutral" style={{ textTransform: 'capitalize' }}>
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
  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        flexWrap: 'wrap',
        gap: '16px'
      }}
    >
      {/* Left: Section color pill & Title */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '14px', flex: '1 1 320px' }}>
        <div
          style={{
            width: '4px',
            height: '42px',
            borderRadius: '2px',
            background: secColor
          }}
        />
        <div>
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              marginBottom: '3px',
              flexWrap: 'wrap'
            }}
          >
            {isMiniSet ? (
              <span
                className="badge badge-purple"
                style={{ fontSize: '0.7rem', fontWeight: 700 }}
              >
                🎯 5 Questions
              </span>
            ) : (
              <span
                className="badge badge-cyan"
                style={{ fontSize: '0.7rem', fontWeight: 700 }}
              >
                📚 50 Questions
              </span>
            )}
            <span
              className="badge"
              style={{
                fontSize: '0.7rem',
                fontWeight: 700,
                padding: '2px 8px',
                background: `${secColor}15`,
                color: secColor,
                border: `1px solid ${secColor}30`
              }}
            >
              {MCAT_SECTION_LABELS[batch.section] || batch.section}
            </span>
            <span
              className="badge-minimal"
              style={{ fontSize: '0.7rem', textTransform: 'capitalize' }}
            >
              {formatDifficulty(batch.difficulty)}
            </span>
            <span className="badge-minimal" style={{ fontSize: '0.7rem' }}>
              {batch.passage_mode === 'single_passage' ? 'Passage Set' : 'Standalone'}
            </span>
          </div>
          <div
            style={{
              fontSize: '0.92rem',
              fontWeight: 700,
              color: 'var(--text-primary)'
            }}
          >
            {batch.subtopic || 'All Topics'}
          </div>
          <div
            style={{
              fontSize: '0.72rem',
              color: 'var(--text-muted)',
              marginTop: '2px',
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              flexWrap: 'wrap'
            }}
          >
            <Clock size={11} />
            <span>{new Date(batch.created_at).toLocaleString()}</span>
            {isInProgress && (
              <>
                <span>•</span>
                <span
                  style={{
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: '4px',
                    color: 'var(--brand-primary)',
                    fontWeight: 700
                  }}
                >
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
      <div style={{ minWidth: '240px', flex: 1 }}>
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            fontSize: '0.76rem',
            marginBottom: '5px'
          }}
        >
          <span style={{ fontWeight: 600, color: 'var(--text-primary)' }}>
            {completedJobs} / {totalJobs} {totalJobs === 1 ? 'Set' : 'Sets'} Completed
          </span>
          <span
            style={{
              fontWeight: 700,
              color: isCompleted ? 'var(--status-success)' : 'var(--brand-primary)'
            }}
          >
            {actualTotal} / {totalTarget} Questions ({progressPercent}%)
          </span>
        </div>

        {/* Progress Bar Track */}
        <div
          style={{
            height: '6px',
            width: '100%',
            borderRadius: '3px',
            background: 'var(--border-light)',
            overflow: 'hidden'
          }}
        >
          <div
            style={{
              height: '100%',
              width: `${progressPercent}%`,
              background:
                batch.status === 'failed'
                  ? 'var(--status-danger)'
                  : isCompleted
                    ? 'var(--status-success)'
                    : 'var(--infynno-gradient)',
              borderRadius: '3px',
              transition: 'width 0.4s ease'
            }}
          />
        </div>

        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            fontSize: '0.7rem',
            color: 'var(--text-muted)',
            marginTop: '5px'
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span>Tokens: {formatTokenCount(batch.total_tokens)}</span>
            <span>•</span>
            <span>Cost: {formatCostUsd(batch.cost_usd)}</span>
          </div>
          <div>
            {isInProgress ? (
              <span
                className="badge"
                style={{
                  fontSize: '0.66rem',
                  fontWeight: 700,
                  background: stageInfo.isAuditing
                    ? 'rgba(51, 90, 207, 0.12)'
                    : stageInfo.isRefilling
                      ? 'rgba(245, 158, 11, 0.12)'
                      : 'rgba(79, 48, 185, 0.1)',
                  color: stageInfo.isRefilling
                    ? 'var(--status-warning)'
                    : 'var(--brand-primary)',
                  border: '1px solid currentColor'
                }}
              >
                {stageInfo.stageBadge}
              </span>
            ) : (
              <span style={{ fontSize: '0.68rem', color: 'var(--text-secondary)' }}>
                {stageInfo.stageBadge}
              </span>
            )}
          </div>
        </div>
      </div>

      {/* Right: Status Pill & Controls */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
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
            style={{
              background: 'rgba(239, 68, 68, 0.08)',
              color: 'var(--status-danger)',
              border: '1px solid rgba(239, 68, 68, 0.25)',
              borderRadius: 'var(--radius-sm)',
              padding: '4px 8px',
              fontSize: '0.72rem',
              fontWeight: 600,
              cursor: 'pointer',
              display: 'inline-flex',
              alignItems: 'center',
              gap: '4px'
            }}
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
            style={{
              background: 'rgba(51, 90, 207, 0.08)',
              color: 'var(--brand-primary)',
              border: '1px solid rgba(51, 90, 207, 0.25)',
              borderRadius: 'var(--radius-sm)',
              padding: '4px 8px',
              fontSize: '0.72rem',
              fontWeight: 600,
              cursor: 'pointer',
              display: 'inline-flex',
              alignItems: 'center',
              gap: '4px'
            }}
            title="Resume incomplete sets from where you stopped"
          >
            <RotateCcw size={11} />
            <span>{isRetrying ? 'Resuming...' : 'Resume Sets'}</span>
          </button>
        )}

        <button
          type="button"
          onClick={(e) => onDeleteBatch(e, batch.id)}
          className="btn-icon"
          style={{ color: 'var(--text-muted)', padding: '5px' }}
          title="Delete batch log"
        >
          <Trash2 size={14} />
        </button>

        <div style={{ color: 'var(--text-muted)' }}>
          {isExpanded ? <ChevronDown size={18} /> : <ChevronRight size={18} />}
        </div>
      </div>
    </div>
  );
}

export default memo(BatchCardSummary);
