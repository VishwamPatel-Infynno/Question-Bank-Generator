import React from 'react';
import { Layers, BookOpen, Image as ImageIcon, Trash2 } from 'lucide-react';
import { formatCostUsd, formatTokenCount } from '../../utils';
import { LiveStopwatch } from '../common';

const EMPTY_COUNTS = {};

/**
 * BatchJobTelemetryBadges - Displays token metrics, costs, execution stopwatch, and question status breakdown badges.
 */
export default function BatchJobTelemetryBadges({
  job,
  isJobRunning = false,
  counts = EMPTY_COUNTS,
  hasPassage = false,
  hasDiagram = false,
  totalQuestionsCount = 0
}) {
  const {
    validatedCount = 0,
    batchOnlyCount = 0,
    inBankCount = 0,
    discardedCount = 0,
    belowCount = 0,
    deletedCount = 0
  } = counts;

  return (
    <>
      {/* Job Details / Telemetry */}
      <div className="batch-job-telemetry-row">
        <span>Tokens: {formatTokenCount(job.total_tokens)}</span>
        <span>{formatCostUsd(job.cost_usd)}</span>
        {isJobRunning ? (
          <span className="batch-job-elapsed-time">
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
        <div className="batch-job-error-callout">
          Error: {job.error_message}
        </div>
      )}

      {totalQuestionsCount > 0 && (
        <div className="batch-job-badge-list">
          {validatedCount > 0 && (
            <span className="batch-job-tag validated">
              {validatedCount} Ready for Review
            </span>
          )}
          {batchOnlyCount > 0 && (
            <span className="batch-job-tag batch-only">
              <Layers size={10} /> {batchOnlyCount} Good Quality
            </span>
          )}
          {inBankCount > 0 && (
            <span className="batch-job-tag in-bank">
              {inBankCount} in Question Bank
            </span>
          )}
          {discardedCount > 0 && (
            <span className="batch-job-tag discarded">
              {discardedCount} Discarded
            </span>
          )}
          {belowCount > 0 && (
            <span className="batch-job-tag below">
              {belowCount} Needs Polish (&le;85)
            </span>
          )}
          {deletedCount > 0 && (
            <span className="batch-job-tag deleted">
              <Trash2 size={10} /> {deletedCount} Deleted from Bank
            </span>
          )}
          {hasPassage && (
            <span className="batch-job-feature-tag">
              <BookOpen size={10} /> Reading Passage
            </span>
          )}
          {hasDiagram && (
            <span className="batch-job-feature-tag">
              <ImageIcon size={10} /> Figure / Diagram
            </span>
          )}
        </div>
      )}
    </>
  );
}
