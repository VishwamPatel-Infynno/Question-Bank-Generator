import React, { useState } from 'react';
import {
  Layers,
  Zap,
  Square,
  Coins,
  Cpu,
  Clock,
  Activity,
  CheckCircle2
} from 'lucide-react';
import { MCAT_SECTION_LABELS } from '../../constants/mcat';
import { formatCostUsd, formatTokenCount } from '../../utils';
import { LiveStopwatch } from '../common';

const EMPTY_ARRAY = Object.freeze([]);

export default function ActiveMultiBatchMonitor({
  activeBatches = EMPTY_ARRAY,
  onCancelAll,
  isCancellingAll = false
}) {
  const [showConfirmCancel, setShowConfirmCancel] = useState(false);

  const totalJobs = activeBatches.reduce((acc, b) => acc + (b.total_jobs || 10), 0);
  const completedJobs = activeBatches.reduce((acc, b) => acc + (b.completed_jobs || 0), 0);
  const targetQuestions = activeBatches.reduce((acc, b) => acc + (b.target_count || 50), 0);
  const actualQuestions = activeBatches.reduce((acc, b) => acc + (b.actual_count || 0), 0);
  const totalTokens = activeBatches.reduce((acc, b) => acc + (b.total_tokens || 0), 0);
  const totalCost = activeBatches.reduce((acc, b) => acc + (b.cost_usd || 0.0), 0.0);

  const allCompleted = activeBatches.length > 0 && activeBatches.every((b) => b.status === 'completed');
  const overallProgressPct = allCompleted
    ? 100
    : targetQuestions > 0
      ? Math.min(100, Math.round((actualQuestions / targetQuestions) * 100))
      : 0;

  // Global Concurrency Worker Pool occupancy:
  // Server semaphore allows up to 4 concurrent jobs simultaneously across all batches.
  const remainingIncompleteJobs = Math.max(0, totalJobs - completedJobs);
  const activeWorkerSlots = Math.min(4, remainingIncompleteJobs);
  const queuedJobs = Math.max(0, remainingIncompleteJobs - activeWorkerSlots);

  if (!activeBatches || activeBatches.length === 0) {
    return null;
  }

  const batchCount = activeBatches.length;

  const handleConfirmCancel = () => {
    setShowConfirmCancel(false);
    if (onCancelAll) onCancelAll();
  };

  return (
    <div
      style={{
        background: 'var(--bg-surface)',
        border: '1px solid var(--border-light)',
        borderRadius: 'var(--radius-md)',
        padding: '16px 20px',
        position: 'relative',
        boxShadow: 'var(--shadow-xs)',
        display: 'flex',
        flexDirection: 'column',
        gap: '14px'
      }}
    >
      {/* Top Banner Row */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          flexWrap: 'wrap',
          gap: '12px'
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <div
            style={{
              width: '32px',
              height: '32px',
              borderRadius: 'var(--radius-xs)',
              background: 'var(--brand-light)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: 'var(--brand-primary)'
            }}
          >
            <Zap size={16} />
          </div>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
              <h2
                style={{
                  fontSize: '1.05rem',
                  fontWeight: 800,
                  color: 'var(--text-primary)',
                  margin: 0,
                  letterSpacing: '-0.01em'
                }}
              >
                Active Practice Batches
              </h2>
              <span
                style={{
                  background: 'rgba(51, 90, 207, 0.15)',
                  color: 'var(--brand-primary)',
                  border: '1px solid rgba(51, 90, 207, 0.3)',
                  borderRadius: '20px',
                  fontSize: '0.7rem',
                  fontWeight: 700,
                  padding: '2px 8px',
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '5px'
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
                {batchCount} {batchCount === 1 ? 'Batch Active' : 'Batches Active'}
              </span>

              <span
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '4px',
                  fontSize: '0.72rem',
                  color: 'var(--brand-primary)',
                  fontWeight: 700,
                  background: 'var(--bg-surface-elevated)',
                  border: '1px solid var(--border-light)',
                  borderRadius: '12px',
                  padding: '2px 8px'
                }}
              >
                <Clock size={11} />
                <span>Elapsed:</span>
                <LiveStopwatch isRunning={true} />
              </span>
            </div>
            <p
              style={{
                fontSize: '0.78rem',
                color: 'var(--text-secondary)',
                margin: '2px 0 0 0'
              }}
            >
              Generating question sets safely in parallel. You can leave this page anytime without losing progress.
            </p>
          </div>
        </div>

        {/* Action Controls */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          {!showConfirmCancel ? (
            <button
              type="button"
              onClick={() => setShowConfirmCancel(true)}
              disabled={isCancellingAll}
              style={{
                background: 'var(--status-danger-bg, rgba(239, 68, 68, 0.08))',
                color: 'var(--status-danger, #ef4444)',
                border: '1px solid var(--status-danger-border, rgba(239, 68, 68, 0.25))',
                borderRadius: 'var(--radius-sm, 6px)',
                padding: '6px 12px',
                fontSize: '0.78rem',
                fontWeight: 600,
                cursor: 'pointer',
                display: 'inline-flex',
                alignItems: 'center',
                gap: '6px',
                transition: 'all 0.2s ease'
              }}
              title="Stop all currently running background batches"
            >
              <Square size={13} />
              <span>{isCancellingAll ? 'Stopping...' : 'Stop All Active Batches'}</span>
            </button>
          ) : (
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span style={{ fontSize: '0.75rem', color: 'var(--status-danger)', fontWeight: 600 }}>
                Stop all {batchCount} batches?
              </span>
              <button
                type="button"
                onClick={handleConfirmCancel}
                style={{
                  background: 'var(--status-danger, #ef4444)',
                  color: 'var(--text-on-brand, #ffffff)',
                  border: 'none',
                  borderRadius: 'var(--radius-sm, 6px)',
                  padding: '5px 10px',
                  fontSize: '0.75rem',
                  fontWeight: 700,
                  cursor: 'pointer'
                }}
              >
                Yes, Stop All
              </button>
              <button
                type="button"
                onClick={() => setShowConfirmCancel(false)}
                style={{
                  background: 'var(--bg-surface)',
                  color: 'var(--text-secondary)',
                  border: '1px solid var(--border-light)',
                  borderRadius: 'var(--radius-sm, 6px)',
                  padding: '5px 10px',
                  fontSize: '0.75rem',
                  cursor: 'pointer'
                }}
              >
                Cancel
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Metric Telemetry Cards Grid */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
          gap: '12px'
        }}
      >
        {/* Jobs progress */}
        <div
          style={{
            background: 'var(--bg-surface)',
            border: '1px solid var(--border-light)',
            borderRadius: 'var(--radius-sm, 8px)',
            padding: '10px 14px',
            display: 'flex',
            alignItems: 'center',
            gap: '10px'
          }}
        >
          <Cpu size={16} color="var(--brand-primary)" />
          <div>
            <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>Question Sets Progress</div>
            <div style={{ fontSize: '0.92rem', fontWeight: 800, color: 'var(--text-primary)' }}>
              {completedJobs} / {totalJobs} <span style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-secondary)' }}>Completed</span>
            </div>
          </div>
        </div>

        {/* Questions drafted */}
        <div
          style={{
            background: 'var(--bg-surface)',
            border: '1px solid var(--border-light)',
            borderRadius: 'var(--radius-sm, 8px)',
            padding: '10px 14px',
            display: 'flex',
            alignItems: 'center',
            gap: '10px'
          }}
        >
          <Layers size={16} color="var(--infynno-cyan, #1E7ADF)" />
          <div>
            <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>Questions Created</div>
            <div style={{ fontSize: '0.92rem', fontWeight: 800, color: 'var(--text-primary)' }}>
              {actualQuestions} / {targetQuestions} <span style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-secondary)' }}>({overallProgressPct}%)</span>
            </div>
          </div>
        </div>

        {/* Tokens consumed */}
        <div
          style={{
            background: 'var(--bg-surface)',
            border: '1px solid var(--border-light)',
            borderRadius: 'var(--radius-sm, 8px)',
            padding: '10px 14px',
            display: 'flex',
            alignItems: 'center',
            gap: '10px'
          }}
        >
          <Coins size={16} color="var(--status-success, #10b981)" />
          <div>
            <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>Usage &amp; Cost</div>
            <div style={{ fontSize: '0.92rem', fontWeight: 800, color: 'var(--text-primary)' }}>
              {formatTokenCount(totalTokens)} <span style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--status-success)' }}>({formatCostUsd(totalCost)})</span>
            </div>
          </div>
        </div>

        {/* Worker Pool Concurrency */}
        <div
          style={{
            background: 'var(--bg-surface)',
            border: '1px solid var(--border-light)',
            borderRadius: 'var(--radius-sm, 8px)',
            padding: '10px 14px',
            display: 'flex',
            alignItems: 'center',
            gap: '10px'
          }}
        >
          <Activity size={16} color="var(--brand-primary)" />
          <div>
            <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>Worker Pool Concurrency</div>
            <div style={{ fontSize: '0.92rem', fontWeight: 800, color: 'var(--text-primary)' }}>
              {activeWorkerSlots} / 4 <span style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-secondary)' }}>Slots Busy</span>
            </div>
            <div style={{ fontSize: '0.68rem', color: queuedJobs > 0 ? 'var(--status-warning)' : 'var(--status-success)', marginTop: '1px' }}>
              {queuedJobs > 0 ? `${queuedJobs} sets queued in pool` : 'All sets executing or done'}
            </div>
          </div>
        </div>
      </div>

      {/* Live Operational Stage Breakdown */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: '8px',
          flexWrap: 'wrap',
          padding: '8px 12px',
          background: 'var(--bg-surface-elevated)',
          border: '1px solid var(--border-light)',
          borderRadius: 'var(--radius-xs)',
          fontSize: '0.72rem'
        }}
      >
        <span style={{ fontWeight: 700, color: 'var(--text-primary)' }}>Active Execution Stages:</span>
        <span
          className="badge"
          style={{
            fontSize: '0.68rem',
            background: 'rgba(51, 90, 207, 0.1)',
            color: 'var(--brand-primary)',
            display: 'inline-flex',
            alignItems: 'center',
            gap: '4px'
          }}
        >
          <span
            style={{
              width: '5px',
              height: '5px',
              borderRadius: '50%',
              background: 'var(--brand-primary)',
              animation: 'pulse 1.4s infinite'
            }}
          />
          {activeWorkerSlots} Sets Generating in Parallel
        </span>
        {queuedJobs > 0 && (
          <span
            className="badge"
            style={{
              fontSize: '0.68rem',
              background: 'rgba(245, 158, 11, 0.1)',
              color: 'var(--status-warning)',
              display: 'inline-flex',
              alignItems: 'center',
              gap: '4px'
            }}
          >
            <Clock size={10} />
            {queuedJobs} Sets Queued for Slots
          </span>
        )}
        <span
          className="badge"
          style={{
            fontSize: '0.68rem',
            background: 'rgba(16, 185, 129, 0.1)',
            color: 'var(--status-success)',
            display: 'inline-flex',
            alignItems: 'center',
            gap: '4px'
          }}
        >
          <CheckCircle2 size={10} />
          {completedJobs} Sets Fully Formed
        </span>
      </div>

      {/* Combined Progress Bar */}
      <div>
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            fontSize: '0.75rem',
            marginBottom: '6px'
          }}
        >
          <span style={{ fontWeight: 600, color: 'var(--text-secondary)' }}>
            Overall Generation Progress
          </span>
          <span style={{ fontWeight: 800, color: 'var(--brand-primary)' }}>
            {overallProgressPct}%
          </span>
        </div>
        <div
          style={{
            height: '8px',
            width: '100%',
            borderRadius: '4px',
            background: 'var(--border-light)',
            overflow: 'hidden'
          }}
        >
          <div
            style={{
              height: '100%',
              width: `${overallProgressPct}%`,
              background: 'linear-gradient(90deg, var(--infynno-violet) 0%, var(--infynno-blue) 50%, var(--infynno-cyan) 100%)',
              borderRadius: '4px',
              transition: 'width 0.5s ease',
              boxShadow: '0 0 10px rgba(79, 48, 185, 0.4)'
            }}
          />
        </div>
      </div>

      {/* Active Batches Section Badges */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: '8px',
          flexWrap: 'wrap',
          paddingTop: '4px'
        }}
      >
        <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)', fontWeight: 600 }}>
          Active Batches:
        </span>
        {activeBatches.map((b) => {
          const secLabel = MCAT_SECTION_LABELS[b.section] || b.section;
          const prog = b.target_count > 0 ? Math.round(((b.actual_count || 0) / b.target_count) * 100) : 0;
          return (
            <span
              key={b.id}
              style={{
                fontSize: '0.7rem',
                fontWeight: 600,
                padding: '3px 8px',
                borderRadius: '6px',
                background: 'var(--bg-surface)',
                border: '1px solid var(--border-medium)',
                color: 'var(--text-primary)',
                display: 'inline-flex',
                alignItems: 'center',
                gap: '5px'
              }}
            >
              <span
                style={{
                  width: '6px',
                  height: '6px',
                  borderRadius: '50%',
                  background: 'var(--infynno-cyan)',
                  animation: 'pulse 1.2s infinite'
                }}
              />
              {secLabel}: {b.actual_count || 0}/{b.target_count || 50} ({prog}%)
            </span>
          );
        })}
      </div>
    </div>
  );
}
