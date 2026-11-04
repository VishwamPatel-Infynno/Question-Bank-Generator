import React from 'react';
import { Clock, RotateCcw, CheckCircle2, AlertCircle } from 'lucide-react';

/**
 * BatchJobHeader - Set number, status/worker queue badges, and question counts for a job.
 */
export default function BatchJobHeader({
  job,
  targetCount = 5,
  isJobRunning = false,
  isJobDone = false,
  isJobFailed = false,
  isJobPending = false
}) {
  return (
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
  );
}

