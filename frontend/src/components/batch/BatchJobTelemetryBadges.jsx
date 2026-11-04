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

      {totalQuestionsCount > 0 && (
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
                background: 'var(--status-danger-bg)',
                color: 'var(--status-danger)',
                border: '1px solid var(--status-danger-border)',
                padding: '2px 7px',
                borderRadius: 'var(--radius-xs)',
                fontWeight: 700,
                display: 'inline-flex',
                alignItems: 'center',
                gap: '3px'
              }}
            >
              <Trash2 size={10} /> {deletedCount} Deleted from Bank
            </span>
          )}
          {hasPassage && (
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
          {hasDiagram && (
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
    </>
  );
}
