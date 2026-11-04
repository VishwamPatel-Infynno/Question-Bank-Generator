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
    <div className="batch-job-header">
      <div className="batch-job-header-left">
        <span className={`batch-job-set-title ${isJobRunning ? 'running' : ''}`}>
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
              className="worker-queue-badge active-slot batch-job-badge-replenish"
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
              <span className="batch-job-pulse-dot" />
              <span>Active Worker Slot</span>
            </span>
          )
        )}

        {isJobDone && (
          <span className="badge badge-success batch-job-status-badge">
            <CheckCircle2 size={11} />
            <span>Completed</span>
          </span>
        )}

        {isJobFailed && (
          <span className="badge badge-danger batch-job-status-badge">
            <AlertCircle size={11} />
            <span>Failed</span>
          </span>
        )}

        {((isJobFailed || (isJobDone && job.actual_count < targetCount)) && (job.trial_count >= 3)) && (
          <span
            className="badge badge-warning batch-job-status-badge"
            title="All 3 autonomous replenishment trials completed"
          >
            3/3 TRIALS EXHAUSTED
          </span>
        )}
      </div>

      <span className={`batch-job-count-text ${isJobDone ? 'done' : ''}`}>
        {job.actual_count} / {targetCount} Qs
      </span>
    </div>
  );
}
