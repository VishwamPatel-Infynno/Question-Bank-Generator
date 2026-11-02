import React from 'react';
import {
  Layers,
  CheckCircle2,
  AlertCircle,
  Clock,
  ChevronDown,
  ChevronRight,
  Trash2,
  Square,
  RotateCcw
} from 'lucide-react';
import { MCAT_SECTION_LABELS, formatDifficulty, getSectionColor } from '../../constants/mcat';
import { formatCostUsd, formatTokenCount } from '../../utils';
import BatchJobCard from './BatchJobCard';

function getStatusBadge(status) {
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
          In Progress
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

const EMPTY_JOB_IDS = {};

function BatchCard({
  batch,
  isExpanded,
  onToggleExpand,
  onDeleteBatch,
  onStopBatch,
  onRetryBatch,
  isStopping = false,
  isRetrying = false,
  detail,
  loadingDetail,
  expandedJobIds = EMPTY_JOB_IDS,
  onToggleJob,
  onNavigateToBank,
  onNavigateToValidated,
  onOpenAudit,
  onSaveToBank,
  onRestoreQuestion
}) {
  const secColor = getSectionColor(batch.section);
  const totalJobs = batch.total_jobs || 10;
  const completedJobs = batch.completed_jobs || 0;
  const totalTarget = batch.target_count || 50;
  const actualTotal = batch.actual_count || 0;
  const isMiniSet = totalJobs === 1 || totalTarget === 5;
  const isCompleted = batch.status === 'completed';
  const isInProgress = batch.status === 'in_progress';

  // Strictly monotonic progress tracking while batch is in progress:
  // Caps running batches at 95% to leave headroom for deduplication and refills,
  // preventing premature 100% flashes and avoiding backwards percentage drops.
  const [highestProgress, setHighestProgress] = React.useState(0);

  const rawPercent = Math.round((actualTotal / Math.max(1, totalTarget)) * 100);
  const runningCapped = Math.min(95, Math.max(0, rawPercent));

  if (isInProgress && runningCapped > highestProgress) {
    setHighestProgress(runningCapped);
  } else if (isCompleted && highestProgress !== 100) {
    setHighestProgress(100);
  }

  const progressPercent = isCompleted
    ? 100
    : isInProgress
      ? Math.max(highestProgress, runningCapped)
      : Math.min(100, Math.max(0, rawPercent));

  return (
    <div
      style={{
        background: 'var(--bg-surface)',
        border: isExpanded
          ? '1px solid var(--border-brand)'
          : '1px solid var(--border-light)',
        borderRadius: 'var(--radius-md)',
        boxShadow: isExpanded ? 'var(--infynno-glow)' : 'var(--shadow-sm)',
        overflow: 'hidden',
        transition: 'all var(--transition-normal)'
      }}
    >
      {/* Batch Summary Row */}
      <div
        onClick={() => onToggleExpand(batch.id)}
        style={{
          padding: '16px 20px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          flexWrap: 'wrap',
          gap: '16px',
          cursor: 'pointer',
          background: isExpanded ? 'var(--bg-surface-elevated)' : 'transparent',
          borderBottom: isExpanded ? '1px solid var(--border-light)' : 'none'
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
                gap: '6px'
              }}
            >
              <Clock size={11} />
              <span>{new Date(batch.created_at).toLocaleString()}</span>
              <span>•</span>
              <span>ID: {batch.id.slice(0, 8)}</span>
            </div>
          </div>
        </div>

        {/* Center: Progress & Metrics */}
        <div style={{ minWidth: '220px', flex: 1 }}>
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
            <span style={{ fontWeight: 700, color: 'var(--brand-primary)' }}>
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
              gap: '10px',
              fontSize: '0.7rem',
              color: 'var(--text-muted)',
              marginTop: '4px'
            }}
          >
            <span>Tokens: {formatTokenCount(batch.total_tokens)}</span>
            <span>•</span>
            <span>Cost: {formatCostUsd(batch.cost_usd)}</span>
          </div>
        </div>

        {/* Right: Status Pill & Controls */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          {getStatusBadge(batch.status)}

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

          {/* Retry Incomplete Jobs button for partially completed, stopped, or failed batches */}
          {(batch.status === 'partially_completed' || batch.status === 'failed' || batch.status === 'cancelled' || batch.status === 'stopped') && (
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
              title="Retry incomplete or failed jobs in this batch"
            >
              <RotateCcw size={11} />
              <span>{isRetrying ? 'Retrying...' : 'Retry Incomplete Sets'}</span>
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

      {/* Expanded Batch Detail: Question Sets */}
      {isExpanded && (
        <div style={{ padding: '20px', background: 'var(--bg-canvas)' }}>
          {loadingDetail && !detail ? (
            <div
              style={{
                textAlign: 'center',
                padding: '30px',
                color: 'var(--text-muted)'
              }}
            >
              <div
                style={{
                  width: '22px',
                  height: '22px',
                  border: '2px solid var(--border-medium)',
                  borderTopColor: 'var(--brand-primary)',
                  borderRadius: '50%',
                  animation: 'spin 0.8s linear infinite',
                  margin: '0 auto 8px'
                }}
              />
              <span style={{ fontSize: '0.8rem' }}>Loading question sets...</span>
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between'
                }}
              >
                <div
                  style={{
                    fontSize: '0.825rem',
                    fontWeight: 700,
                    color: 'var(--text-primary)',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '8px'
                  }}
                >
                  <Layers size={15} style={{ color: 'var(--brand-primary)' }} />
                  <span>
                    Question Sets ({detail?.jobs?.length || 0} sets &bull; 5 questions each):
                  </span>
                </div>
                <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
                  Generating sets in parallel
                </div>
              </div>

              {/* Jobs Grid */}
              {!detail?.jobs || detail.jobs.length === 0 ? (
                <div
                  style={{
                    textAlign: 'center',
                    padding: '24px',
                    color: 'var(--text-muted)',
                    fontSize: '0.8rem',
                    background: 'var(--bg-surface)',
                    borderRadius: 'var(--radius-sm)',
                    border: '1px dashed var(--border-medium)'
                  }}
                >
                  No question sets recorded for this practice batch.
                </div>
              ) : (
                <div
                  style={{
                    display: 'grid',
                    gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))',
                    gap: '12px'
                  }}
                >
                  {detail.jobs.map((job) => (
                    <BatchJobCard
                      key={job.id}
                      job={job}
                      isExpanded={Boolean(expandedJobIds[job.id])}
                      onToggleExpand={onToggleJob}
                      onNavigateToBank={onNavigateToBank}
                      onNavigateToValidated={onNavigateToValidated}
                      onOpenAudit={onOpenAudit}
                      onSaveToBank={onSaveToBank}
                      onRestoreQuestion={onRestoreQuestion}
                    />
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default React.memo(BatchCard);
