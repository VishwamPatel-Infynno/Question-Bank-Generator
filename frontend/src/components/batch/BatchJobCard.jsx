import React from 'react';
import {
  FileText,
  ChevronDown,
  ChevronRight,
  Layers,
  BookOpen,
  Image as ImageIcon,
  Trash2,
  CheckCircle2,
  AlertCircle,
  Clock,
  RotateCcw,
  Check
} from 'lucide-react';
import { formatCostUsd, formatTokenCount } from '../../utils';
import { LiveStopwatch } from '../common';
import BatchQuestionItem from './BatchQuestionItem';

export default function BatchJobCard({
  job,
  isExpanded = false,
  onToggleExpand,
  onNavigateToBank,
  onNavigateToValidated,
  onOpenAudit,
  onSaveToBank,
  onRestoreQuestion
}) {
  if (!job) return null;

  const jobQuestions = job.questions || [];
  const isJobDone = job.status === 'completed';
  const isJobRunning = job.status === 'running';
  const isJobFailed = job.status === 'failed';
  const isJobPending = job.status === 'pending';
  const targetCount = job.target_count || 5;

  // Compute status counts for questions in this job
  const resolveStatus = (q) => {
    if (q.status === 'discarded') return 'discarded';
    if (q.is_deleted) return 'deleted';
    if (q.status) return q.status;
    const score = q.final_score ?? 95;
    if (score > 90) return 'ai_validated';
    if (score > 85) return 'batch_only';
    return 'below_threshold';
  };

  // Only genuine user deletions from the bank count as deleted; discarded duplicates never count as deleted
  const deletedCount = jobQuestions.filter((q) => Boolean(q.is_deleted) && q.status !== 'discarded').length;
  const validatedCount = jobQuestions.filter((q) => !q.is_deleted && resolveStatus(q) === 'ai_validated').length;
  const batchOnlyCount = jobQuestions.filter((q) => !q.is_deleted && resolveStatus(q) === 'batch_only').length;
  const inBankCount = jobQuestions.filter((q) => !q.is_deleted && resolveStatus(q) === 'in_bank').length;
  const discardedCount = jobQuestions.filter((q) => !q.is_deleted && resolveStatus(q) === 'discarded').length;
  const belowCount = jobQuestions.filter((q) => !q.is_deleted && resolveStatus(q) === 'below_threshold').length;

  const hasPassageInJob = jobQuestions.some(
    (q) => Boolean(q.stimulus_text && q.stimulus_text.trim().length > 0)
  );
  const hasDiagramInJob = jobQuestions.some(
    (q) =>
      Boolean(
        q.image_url ||
          q.image_svg ||
          q.stage_outcomes?.visual_stimulus?.image_url ||
          q.stage_outcomes?.visual_stimulus?.image_svg ||
          q.stage_outcomes?.passage_visual_stimulus?.image_url ||
          q.stage_outcomes?.passage_visual_stimulus?.image_svg
      )
  );

  // Filter out any discarded duplicate questions so they never appear in the job questions list
  const visibleQuestions = jobQuestions.filter((q) => q.status !== 'discarded');

  // Present kept questions (>85) first, then below threshold (<=85)
  const sortedQuestions = [...visibleQuestions].sort((a, b) => {
    const isKeptA = resolveStatus(a) !== 'below_threshold';
    const isKeptB = resolveStatus(b) !== 'below_threshold';
    if (isKeptA && !isKeptB) return -1;
    if (!isKeptA && isKeptB) return 1;
    return 0;
  });

  return (
    <div
      style={{
        background: 'var(--bg-surface)',
        border: isJobRunning
          ? '1px solid rgba(51, 90, 207, 0.4)'
          : isJobDone
            ? '1px solid var(--border-light)'
            : '1px solid var(--border-light)',
        borderRadius: 'var(--radius-sm)',
        padding: '12px 14px',
        display: 'flex',
        flexDirection: 'column',
        gap: '8px',
        transition: 'border-color var(--transition-fast)'
      }}
    >
      {/* Job Card Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
          <span
            style={{
              fontWeight: 800,
              fontSize: '0.8rem',
              color: isJobRunning ? 'var(--brand-primary)' : 'var(--text-primary)'
            }}
          >
            Set #{job.job_number}
          </span>

          {/* Worker Queue vs Active Slot vs Finished State */}
          {isJobPending && (
            <span
              className="worker-queue-badge queued"
              title="Job is queued waiting for an available concurrency slot from the global worker pool (max 4 concurrent jobs)"
            >
              <Clock size={11} />
              <span>Queued in Worker Pool</span>
            </span>
          )}

          {isJobRunning && (
            job.trial_count > 1 ? (
              <span
                className="worker-queue-badge active-slot"
                style={{
                  background: 'rgba(245, 158, 11, 0.12)',
                  color: 'var(--status-warning)',
                  borderColor: 'rgba(245, 158, 11, 0.3)'
                }}
                title={`Autonomous in-set replenishment trial ${job.trial_count} of 3`}
              >
                <RotateCcw size={11} />
                <span>Replenishing Slot (Trial {job.trial_count}/3)</span>
              </span>
            ) : (
              <span
                className="worker-queue-badge active-slot"
                title="Active worker slot executing LangGraph generation workflow"
              >
                <span
                  style={{
                    width: '5px',
                    height: '5px',
                    borderRadius: '50%',
                    background: 'var(--brand-primary)',
                    animation: 'pulse 1.5s infinite'
                  }}
                />
                <span>Active Worker Slot</span>
              </span>
            )
          )}

          {isJobDone && (
            <span
              className="badge badge-success"
              style={{
                fontSize: '0.675rem',
                padding: '1px 6px',
                display: 'inline-flex',
                alignItems: 'center',
                gap: '4px'
              }}
            >
              <CheckCircle2 size={11} />
              <span>Completed</span>
            </span>
          )}

          {isJobFailed && (
            <span
              className="badge badge-danger"
              style={{
                fontSize: '0.675rem',
                padding: '1px 6px',
                display: 'inline-flex',
                alignItems: 'center',
                gap: '4px'
              }}
            >
              <AlertCircle size={11} />
              <span>Failed</span>
            </span>
          )}

          {((isJobFailed || (isJobDone && job.actual_count < targetCount)) && (job.trial_count >= 3)) && (
            <span
              className="badge"
              style={{
                fontSize: '0.65rem',
                padding: '1px 6px',
                background: 'rgba(245, 158, 11, 0.12)',
                color: 'var(--status-warning)',
                border: '1px solid rgba(245, 158, 11, 0.25)'
              }}
              title="All 3 autonomous replenishment trials completed"
            >
              3/3 TRIALS EXHAUSTED
            </span>
          )}
        </div>

        <span
          style={{
            fontSize: '0.725rem',
            fontWeight: 600,
            color: isJobDone ? 'var(--status-success)' : 'var(--text-muted)'
          }}
        >
          {job.actual_count} / {targetCount} Qs
        </span>
      </div>

      {/* 5-Question Visual Progress Strip */}
      <div className="job-q-pill-strip" role="group" aria-label={`Question progress for Set ${job.job_number}`}>
        {Array.from({ length: targetCount }).map((_, idx) => {
          const qNum = idx + 1;
          const matchedQ = visibleQuestions[idx];
          if (matchedQ) {
            const st = resolveStatus(matchedQ);
            const score = matchedQ.final_score ?? 95;
            const isBank = st === 'in_bank';
            return (
              <span
                key={matchedQ.id || idx}
                className={`job-q-pill ${isBank ? 'in-bank' : 'done'}`}
                title={`Question ${qNum}: Score ${score}/100 • ${isBank ? 'In Question Bank' : 'Ready for Review'}`}
              >
                <Check size={10} />
                <span>Q{qNum} ({score})</span>
              </span>
            );
          }
          if (isJobRunning && idx === visibleQuestions.length) {
            return (
              <span
                key={idx}
                className="job-q-pill active"
                title={`Question ${qNum}: Currently generating passage, stem & distractors`}
              >
                <span
                  style={{
                    width: '4px',
                    height: '4px',
                    borderRadius: '50%',
                    background: 'var(--brand-primary)',
                    animation: 'pulse 1.2s infinite'
                  }}
                />
                <span>Q{qNum} drafting</span>
              </span>
            );
          }
          return (
            <span
              key={idx}
              className="job-q-pill pending"
              title={`Question ${qNum}: Pending in set`}
            >
              <span>Q{qNum}</span>
            </span>
          );
        })}
      </div>

      {/* Job Details / Telemetry */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          fontSize: '0.7rem',
          color: 'var(--text-muted)'
        }}
      >
        <span>Tokens: {formatTokenCount(job.total_tokens)}</span>
        <span>{formatCostUsd(job.cost_usd)}</span>
        {isJobRunning ? (
          <span
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '4px',
              color: 'var(--brand-primary)',
              fontWeight: 600
            }}
          >
            <LiveStopwatch isRunning={true} /> elapsed
          </span>
        ) : job.completed_at ? (
          <span>
            Finished{' '}
            {new Date(job.completed_at).toLocaleTimeString([], {
              hour: '2-digit',
              minute: '2-digit'
            })}
          </span>
        ) : null}
      </div>

      {job.error_message && (
        <div
          style={{
            fontSize: '0.72rem',
            color: 'var(--status-danger)',
            background: 'rgba(244, 63, 94, 0.08)',
            padding: '6px 8px',
            borderRadius: 'var(--radius-xs)'
          }}
        >
          Error: {job.error_message}
        </div>
      )}

      {jobQuestions.length > 0 && (
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', flexWrap: 'wrap', fontSize: '0.675rem' }}>
          {validatedCount > 0 && (
            <span
              style={{
                background: 'rgba(79, 48, 185, 0.1)',
                color: 'var(--brand-primary)',
                padding: '2px 7px',
                borderRadius: '4px',
                fontWeight: 700
              }}
            >
              {validatedCount} Ready for Review
            </span>
          )}
          {batchOnlyCount > 0 && (
            <span
              style={{
                background: 'rgba(51, 90, 207, 0.12)',
                color: 'var(--brand-primary)',
                border: '1px solid rgba(51, 90, 207, 0.25)',
                padding: '2px 7px',
                borderRadius: '4px',
                fontWeight: 700,
                display: 'inline-flex',
                alignItems: 'center',
                gap: '3px'
              }}
            >
              <Layers size={10} /> {batchOnlyCount} Good Quality
            </span>
          )}
          {inBankCount > 0 && (
            <span
              style={{
                background: 'rgba(16, 185, 129, 0.1)',
                color: 'var(--status-success)',
                padding: '2px 7px',
                borderRadius: '4px',
                fontWeight: 700
              }}
            >
              {inBankCount} in Question Bank
            </span>
          )}
          {discardedCount > 0 && (
            <span
              style={{
                background: 'rgba(244, 63, 94, 0.1)',
                color: 'var(--status-danger)',
                padding: '2px 7px',
                borderRadius: '4px',
                fontWeight: 700
              }}
            >
              {discardedCount} Discarded
            </span>
          )}
          {belowCount > 0 && (
            <span
              style={{
                background: 'var(--status-warning-bg, rgba(245, 158, 11, 0.1))',
                color: 'var(--status-warning, #d97706)',
                border: '1px solid var(--status-warning-border, rgba(245, 158, 11, 0.25))',
                padding: '2px 7px',
                borderRadius: '4px',
                fontWeight: 700
              }}
            >
              {belowCount} Needs Polish (&le;85)
            </span>
          )}
          {deletedCount > 0 && (
            <span
              style={{
                background: 'rgba(239, 68, 68, 0.1)',
                color: 'var(--status-danger, #ef4444)',
                border: '1px solid rgba(239, 68, 68, 0.25)',
                padding: '2px 7px',
                borderRadius: '4px',
                fontWeight: 700,
                display: 'inline-flex',
                alignItems: 'center',
                gap: '3px'
              }}
            >
              <Trash2 size={10} /> {deletedCount} Deleted from Bank
            </span>
          )}
          {hasPassageInJob && (
            <span
              style={{
                background: 'rgba(51, 90, 207, 0.08)',
                color: 'var(--brand-primary)',
                border: '1px solid rgba(51, 90, 207, 0.2)',
                padding: '2px 7px',
                borderRadius: '4px',
                fontWeight: 700,
                display: 'inline-flex',
                alignItems: 'center',
                gap: '3px'
              }}
            >
              <BookOpen size={10} /> Reading Passage
            </span>
          )}
          {hasDiagramInJob && (
            <span
              style={{
                background: 'rgba(79, 48, 185, 0.08)',
                color: 'var(--brand-primary)',
                border: '1px solid rgba(79, 48, 185, 0.2)',
                padding: '2px 7px',
                borderRadius: '4px',
                fontWeight: 700,
                display: 'inline-flex',
                alignItems: 'center',
                gap: '3px'
              }}
            >
              <ImageIcon size={10} /> Figure / Diagram
            </span>
          )}
        </div>
      )}

      {/* Action button: Expand/Hide questions */}
      {jobQuestions.length > 0 && (
        <div>
          <button
            type="button"
            onClick={() => onToggleExpand && onToggleExpand(job.id)}
            className="btn-secondary"
            style={{
              width: '100%',
              padding: '5px 8px',
              fontSize: '0.725rem',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '6px',
              marginTop: '4px'
            }}
          >
            <FileText size={12} />
            <span>
              {isExpanded
                ? 'Hide Questions in this Set'
                : `View ${jobQuestions.length} Questions in this Set`}
            </span>
            {isExpanded ? <ChevronDown size={13} /> : <ChevronRight size={13} />}
          </button>
        </div>
      )}

      {/* Expanded Questions inside Job */}
      {isExpanded && visibleQuestions.length > 0 && (
        <div
          style={{
            marginTop: '8px',
            paddingTop: '8px',
            borderTop: '1px solid var(--border-light)',
            display: 'flex',
            flexDirection: 'column',
            gap: '10px'
          }}
        >
          {sortedQuestions.map((q, qIdx) => (
            <BatchQuestionItem
              key={q.id || qIdx}
              question={q}
              index={qIdx}
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
  );
}
