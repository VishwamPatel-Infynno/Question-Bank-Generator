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
  RotateCcw,
  ShieldCheck,
  Sparkles,
  ArrowRight
} from 'lucide-react';
import { MCAT_SECTION_LABELS, formatDifficulty, getSectionColor } from '../../constants/mcat';
import { formatCostUsd, formatTokenCount } from '../../utils';
import { LiveStopwatch } from '../common';
import BatchJobCard from './BatchJobCard';

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

const BATCH_LIFECYCLE_STAGES = [
  { id: 1, key: 'draft', label: '1. Drafting Sets', desc: 'Generating item drafts', icon: Layers },
  { id: 2, key: 'audit', label: '2. Duplicate Audit', desc: 'Clustering & quality checks', icon: ShieldCheck },
  { id: 3, key: 'refill', label: '3. In-Set Refill', desc: 'Autonomous replenishment', icon: RotateCcw },
  { id: 4, key: 'ready', label: '4. Ready for Review', desc: 'Promoted to Review Queue', icon: CheckCircle2 }
];

function getBatchStageInfo(batch, detail) {
  const isCompleted = batch.status === 'completed';
  const isPartial = batch.status === 'partially_completed';
  const isStopped = batch.status === 'stopped' || batch.status === 'cancelled';
  const isFailed = batch.status === 'failed';
  const isInProgress = batch.status === 'in_progress';

  const totalTarget = batch.target_count || 50;
  const actualTotal = batch.actual_count || 0;
  const completedJobs = batch.completed_jobs || 0;
  const totalJobs = batch.total_jobs || 10;

  const isRefilling = detail?.jobs?.some((j) => j.trial_count > 1 && j.status === 'running') || false;
  const hasEverRefilled = detail?.jobs?.some((j) => j.trial_count > 1) || false;

  const isAuditing = isInProgress && (completedJobs >= totalJobs || actualTotal >= totalTarget) && !isRefilling;

  let activeStep = 1;
  let stageBadge = 'Generating';
  let stageDescription = 'Generating questions across parallel sets';

  if (isCompleted) {
    activeStep = 4;
    stageBadge = 'Ready for Review';
    stageDescription = 'All sets generated & promoted to Review Queue';
  } else if (isPartial) {
    activeStep = 4;
    stageBadge = 'Trials Exhausted';
    stageDescription = 'Concluded with shortfalls after 3 replenishment trials';
  } else if (isStopped) {
    activeStep = 1;
    stageBadge = 'Stopped by User';
    stageDescription = 'Batch generation paused by user';
  } else if (isFailed) {
    activeStep = 1;
    stageBadge = 'Failed';
    stageDescription = batch.error_message || 'Batch encountered an unrecoverable error';
  } else if (isRefilling) {
    activeStep = 3;
    stageBadge = 'Autonomous Refill Active';
    stageDescription = 'Replenishing missing or duplicate slots in-set (Trial 2-3)';
  } else if (isAuditing) {
    activeStep = 2;
    stageBadge = 'Auditing Duplicates';
    stageDescription = 'Analyzing pairwise similarity (>75%) & quality thresholds';
  } else {
    activeStep = 1;
    stageBadge = 'Drafting Sets';
    stageDescription = `Drafting sets in parallel (${completedJobs}/${totalJobs} sets completed)`;
  }

  return {
    activeStep,
    stageBadge,
    stageDescription,
    isAuditing,
    isRefilling,
    hasEverRefilled
  };
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

  // Accurate true progress percentage without artificial 95% caps:
  const rawPercent = Math.min(100, Math.round((actualTotal / Math.max(1, totalTarget)) * 100));
  const progressPercent = isCompleted ? 100 : rawPercent;

  const stageInfo = getBatchStageInfo(batch, detail);

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
          flexDirection: 'column',
          gap: '14px',
          cursor: 'pointer',
          background: isExpanded ? 'var(--bg-surface-elevated)' : 'transparent',
          borderBottom: isExpanded ? '1px solid var(--border-light)' : 'none'
        }}
      >
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
              <span style={{ fontWeight: 700, color: isCompleted ? 'var(--status-success)' : 'var(--brand-primary)' }}>
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

        {/* ── Dual-Track Lifecycle Stepper ──────────────────────────────── */}
        <div className="batch-lifecycle-stepper" role="region" aria-label="Batch execution lifecycle">
          {BATCH_LIFECYCLE_STAGES.map((stage, idx) => {
            const StageIcon = stage.icon;
            let stepState = 'pending';

            if (isCompleted) {
              if (stage.id === 3 && !stageInfo.hasEverRefilled) {
                stepState = 'skipped';
              } else {
                stepState = 'completed';
              }
            } else if (batch.status === 'partially_completed') {
              if (stage.id < 4) {
                stepState = 'completed';
              } else {
                stepState = 'active';
              }
            } else if (isInProgress) {
              if (stage.id < stageInfo.activeStep) {
                stepState = 'completed';
              } else if (stage.id === stageInfo.activeStep) {
                stepState = 'active';
              } else {
                stepState = 'pending';
              }
            } else {
              // stopped or failed
              if (stage.id === 1) {
                stepState = actualTotal > 0 ? 'completed' : 'pending';
              } else {
                stepState = 'pending';
              }
            }

            return (
              <React.Fragment key={stage.id}>
                <div className={`stepper-step ${stepState}`} title={stage.desc}>
                  <div className="stepper-icon-pill">
                    {stepState === 'completed' ? (
                      <CheckCircle2 size={13} />
                    ) : (
                      <StageIcon size={12} />
                    )}
                  </div>
                  <div className="stepper-content">
                    <span className="stepper-title">{stage.label}</span>
                    <span className="stepper-subtitle">
                      {stepState === 'completed'
                        ? 'Done'
                        : stepState === 'active'
                          ? stageInfo.stageDescription
                          : stepState === 'skipped'
                            ? 'Fulfilled (No refill needed)'
                            : stage.desc}
                    </span>
                  </div>
                </div>
                {idx < BATCH_LIFECYCLE_STAGES.length - 1 && (
                  <ChevronRight size={14} className="stepper-arrow" />
                )}
              </React.Fragment>
            );
          })}
        </div>

        {/* ── Contextual Outcome Banners ───────────────────────────────── */}
        {isCompleted && (
          <div className="batch-outcome-card completed" onClick={(e) => e.stopPropagation()}>
            <div className="batch-outcome-left">
              <div style={{ color: 'var(--status-success)' }}>
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
                  className="btn-primary"
                  style={{
                    padding: '6px 14px',
                    fontSize: '0.78rem',
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: '6px'
                  }}
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
                  className="btn-secondary"
                  style={{ padding: '6px 12px', fontSize: '0.78rem' }}
                >
                  View Question Bank
                </button>
              )}
            </div>
          </div>
        )}

        {batch.status === 'partially_completed' && (
          <div className="batch-outcome-card warning" onClick={(e) => e.stopPropagation()}>
            <div className="batch-outcome-left">
              <div style={{ color: 'var(--status-warning)' }}>
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
                  className="btn-primary"
                  style={{
                    padding: '6px 14px',
                    fontSize: '0.78rem',
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: '6px'
                  }}
                >
                  <span>Review Valid Questions ({actualTotal})</span>
                  <ArrowRight size={13} />
                </button>
              )}
              {onNavigateToBank && (
                <button
                  type="button"
                  onClick={() => onNavigateToBank()}
                  className="btn-secondary"
                  style={{ padding: '6px 12px', fontSize: '0.78rem' }}
                >
                  View Question Bank
                </button>
              )}
            </div>
          </div>
        )}

        {(batch.status === 'stopped' || batch.status === 'cancelled') && (
          <div className="batch-outcome-card stopped" onClick={(e) => e.stopPropagation()}>
            <div className="batch-outcome-left">
              <div style={{ color: 'var(--text-secondary)' }}>
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
                  className="btn-secondary"
                  style={{
                    padding: '6px 12px',
                    fontSize: '0.78rem',
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: '6px'
                  }}
                >
                  <RotateCcw size={12} />
                  <span>{isRetrying ? 'Resuming...' : 'Resume Incomplete Sets'}</span>
                </button>
              )}
              {actualTotal > 0 && onNavigateToValidated && (
                <button
                  type="button"
                  onClick={() => onNavigateToValidated()}
                  className="btn-primary"
                  style={{ padding: '6px 12px', fontSize: '0.78rem' }}
                >
                  Review Generated ({actualTotal})
                </button>
              )}
            </div>
          </div>
        )}
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
