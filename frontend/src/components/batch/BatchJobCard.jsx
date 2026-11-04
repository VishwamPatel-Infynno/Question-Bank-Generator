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
  const isJobDone = job.status === 'completed';
  const isJobRunning = job.status === 'running';
  const isJobFailed = job.status === 'failed';
  const isJobPending = job.status === 'pending';
  const targetCount = job.target_count || 5;

  const counts = computeJobQuestionCounts(jobQuestions);
  const hasPassage = hasJobPassage(jobQuestions);
  const hasDiagram = hasJobDiagram(jobQuestions);
  const sortedQuestions = sortJobQuestions(jobQuestions);
  const visibleQuestions = jobQuestions.filter((q) => q.status !== 'discarded');

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
      {isExpanded && sortedQuestions.length > 0 && (
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
