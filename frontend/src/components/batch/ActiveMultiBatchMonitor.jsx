import { useState, memo } from 'react';
import {
  Layers,
  Square,
  Activity,
  Cpu,
  Coins,
  Clock,
  CheckCircle2
} from 'lucide-react';
import { EMPTY_ARRAY, MCAT_SECTION_LABELS } from '../../constants';
import { formatCostUsd, formatTokenCount } from '../../utils';
import { LiveStopwatch } from '../common';

function ActiveMultiBatchMonitor({
  activeBatches = EMPTY_ARRAY,
  onCancelAll,
  isCancellingAll = false
}) {
  const [showConfirmCancel, setShowConfirmCancel] = useState(false);

  if (!activeBatches || activeBatches.length === 0) {
    return null;
  }

  // Aggregate multi-batch metrics
  const batchCount = activeBatches.length;
  const totalJobs = activeBatches.reduce((acc, b) => acc + (b.total_jobs || 1), 0);
  const completedJobs = activeBatches.reduce((acc, b) => acc + (b.completed_jobs || 0), 0);
  const targetQuestions = activeBatches.reduce((acc, b) => acc + (b.target_count || 5), 0);
  const actualQuestions = activeBatches.reduce((acc, b) => acc + (b.actual_count || 0), 0);
  const totalTokens = activeBatches.reduce((acc, b) => acc + (b.total_tokens || 0), 0);
  const totalCost = activeBatches.reduce((acc, b) => acc + (b.cost_usd || 0), 0);

  // Accurate true progress percentage without artificial caps
  const overallProgressPct = Math.min(
    100,
    Math.round((actualQuestions / Math.max(1, targetQuestions)) * 100)
  );

  // Concurrency stats
  const activeWorkerSlots = Math.min(4, Math.max(1, totalJobs - completedJobs));
  const queuedJobs = Math.max(0, totalJobs - completedJobs - activeWorkerSlots);

  const handleConfirmCancel = async () => {
    try {
      await onCancelAll?.();
    } finally {
      setShowConfirmCancel(false);
    }
  };

  return (
    <div className="batch-monitor-card">
      {/* Top Row: Title, Pulse, Stopwatch, Emergency Stop */}
      <div className="batch-monitor-top-row">
        <div className="batch-monitor-header-left">
          <div className="batch-monitor-icon-box">
            <Activity size={18} />
          </div>
          <div>
            <div className="batch-monitor-title-group">
              <h3 className="batch-monitor-title">
                Active Generation Batches
              </h3>
              <span className="batch-monitor-active-badge">
                <span className="batch-monitor-pulse-dot" />
                <span>{batchCount} Running</span>
              </span>
              <span className="batch-monitor-stopwatch-chip">
                <Clock size={11} />
                <LiveStopwatch isRunning={true} />
              </span>
            </div>
            <p className="batch-monitor-subtitle">
              Generating question sets safely in parallel. You can leave this page anytime without losing progress.
            </p>
          </div>
        </div>

        {/* Action Controls */}
        <div className="batch-monitor-actions">
          {!showConfirmCancel ? (
            <button
              type="button"
              onClick={() => setShowConfirmCancel(true)}
              disabled={isCancellingAll}
              className="batch-monitor-stop-btn"
              title="Stop all currently running background batches"
            >
              <Square size={13} />
              <span>{isCancellingAll ? 'Stopping...' : 'Stop All Active Batches'}</span>
            </button>
          ) : (
            <div className="batch-monitor-confirm-box">
              <span className="batch-monitor-confirm-text">
                Stop all {batchCount} batches?
              </span>
              <button
                type="button"
                onClick={handleConfirmCancel}
                className="batch-monitor-btn-danger"
              >
                Yes, Stop All
              </button>
              <button
                type="button"
                onClick={() => setShowConfirmCancel(false)}
                className="batch-monitor-btn-cancel"
              >
                Cancel
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Metric Telemetry Cards Grid */}
      <div className="batch-monitor-telemetry-grid">
        {/* Jobs progress */}
        <div className="batch-monitor-telemetry-card">
          <Cpu size={16} color="var(--brand-primary)" />
          <div>
            <div className="batch-monitor-metric-title">Question Sets Progress</div>
            <div className="batch-monitor-metric-stat">
              {completedJobs} / {totalJobs} <span className="batch-monitor-metric-secondary">Completed</span>
            </div>
          </div>
        </div>

        {/* Questions drafted */}
        <div className="batch-monitor-telemetry-card">
          <Layers size={16} color="var(--infynno-cyan)" />
          <div>
            <div className="batch-monitor-metric-title">Questions Created</div>
            <div className="batch-monitor-metric-stat">
              {actualQuestions} / {targetQuestions} <span className="batch-monitor-metric-secondary">({overallProgressPct}%)</span>
            </div>
          </div>
        </div>

        {/* Tokens consumed */}
        <div className="batch-monitor-telemetry-card">
          <Coins size={16} color="var(--status-success)" />
          <div>
            <div className="batch-monitor-metric-title">Usage &amp; Cost</div>
            <div className="batch-monitor-metric-stat">
              {formatTokenCount(totalTokens)} <span className="batch-monitor-metric-cost">({formatCostUsd(totalCost)})</span>
            </div>
          </div>
        </div>

        {/* Worker Pool Concurrency */}
        <div className="batch-monitor-telemetry-card">
          <Activity size={16} color="var(--brand-primary)" />
          <div>
            <div className="batch-monitor-metric-title">Worker Pool Concurrency</div>
            <div className="batch-monitor-metric-stat">
              {activeWorkerSlots} / 4 <span className="batch-monitor-metric-secondary">Slots Busy</span>
            </div>
            <div className={`batch-monitor-metric-subtext ${queuedJobs > 0 ? 'warning' : 'success'}`}>
              {queuedJobs > 0 ? `${queuedJobs} sets queued in pool` : 'All sets executing or done'}
            </div>
          </div>
        </div>
      </div>

      {/* Live Operational Stage Breakdown */}
      <div className="batch-monitor-stages-bar">
        <span className="batch-monitor-stages-title">Active Execution Stages:</span>
        <span className="badge batch-monitor-stage-tag active">
          <span className="batch-monitor-stage-dot" />
          {activeWorkerSlots} Sets Generating in Parallel
        </span>
        {queuedJobs > 0 && (
          <span className="badge batch-monitor-stage-tag queued">
            <Clock size={10} />
            {queuedJobs} Sets Queued for Slots
          </span>
        )}
        <span className="badge batch-monitor-stage-tag done">
          <CheckCircle2 size={10} />
          {completedJobs} Sets Fully Formed
        </span>
      </div>

      {/* Combined Progress Bar */}
      <div className="batch-monitor-progress-wrapper">
        <div className="batch-monitor-progress-header">
          <span className="batch-monitor-progress-lbl">
            Overall Generation Progress
          </span>
          <span className="batch-monitor-progress-pct">
            {overallProgressPct}%
          </span>
        </div>
        <div className="batch-monitor-progress-track">
          <div
            className="batch-monitor-progress-fill"
            style={{ width: `${overallProgressPct}%` }}
          />
        </div>
      </div>

      {/* Active Batches Section Badges */}
      <div className="batch-monitor-batches-strip">
        <span className="batch-monitor-batches-label">
          Active Batches:
        </span>
        {activeBatches.map((b) => {
          const secLabel = MCAT_SECTION_LABELS[b.section] || b.section;
          const prog = b.target_count > 0 ? Math.round(((b.actual_count || 0) / b.target_count) * 100) : 0;
          return (
            <span key={b.id} className="batch-monitor-batch-pill">
              <span className="batch-monitor-cyan-dot" />
              {secLabel}: {b.actual_count || 0}/{b.target_count || 50} ({prog}%)
            </span>
          );
        })}
      </div>
    </div>
  );
}

export default memo(ActiveMultiBatchMonitor);
