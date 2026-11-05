import React from 'react';
import { FileText, ChevronDown, ChevronRight } from 'lucide-react';
import {
  computeJobQuestionCounts,
  hasJobPassage,
  hasJobDiagram,
  sortJobQuestions
} from '../../utils';
import BatchJobHeader from './BatchJobHeader';
import BatchJobPillStrip from './BatchJobPillStrip';
import BatchJobTelemetryBadges from './BatchJobTelemetryBadges';
import BatchQuestionItem from './BatchQuestionItem';
import { JOB_STATUS, QUESTION_STATUS } from '../../constants';

/**
 * BatchJobCard - Coordinates an individual question set (e.g. Set #1 of 10) in a batch card.
 */
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
  const isJobDone = job.status === JOB_STATUS.COMPLETED;
  const isJobRunning = job.status === JOB_STATUS.RUNNING;
  const isJobFailed = job.status === JOB_STATUS.FAILED;
  const isJobPending = job.status === JOB_STATUS.PENDING;
  const targetCount = job.target_count || 5;

  const counts = computeJobQuestionCounts(jobQuestions);
  const hasPassage = hasJobPassage(jobQuestions);
  const hasDiagram = hasJobDiagram(jobQuestions);
  const sortedQuestions = sortJobQuestions(jobQuestions);
  const visibleQuestions = jobQuestions.filter((q) => q.status !== QUESTION_STATUS.DISCARDED);

  return (
    <div className={`batch-job-card ${isJobRunning ? 'running' : ''}`}>
      {/* Job Card Header */}
      <BatchJobHeader
        job={job}
        targetCount={targetCount}
        isJobRunning={isJobRunning}
        isJobDone={isJobDone}
        isJobFailed={isJobFailed}
        isJobPending={isJobPending}
      />

      {/* 5-Question Visual Progress Strip */}
      <BatchJobPillStrip
        jobId={job.id}
        jobNumber={job.job_number}
        targetCount={targetCount}
        visibleQuestions={visibleQuestions}
        isJobRunning={isJobRunning}
      />

      {/* Telemetry and Feature Badges */}
      <BatchJobTelemetryBadges
        job={job}
        isJobRunning={isJobRunning}
        counts={counts}
        hasPassage={hasPassage}
        hasDiagram={hasDiagram}
        totalQuestionsCount={jobQuestions.length}
      />

      {/* Action button: Expand/Hide questions */}
      {jobQuestions.length > 0 && (
        <div>
          <button
            type="button"
            onClick={() => onToggleExpand && onToggleExpand(job.id)}
            className="btn-secondary batch-job-toggle-btn"
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
      {isExpanded && sortedQuestions.length > 0 && (
        <div className="batch-job-expanded-list">
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
