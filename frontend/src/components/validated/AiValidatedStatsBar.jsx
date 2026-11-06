import { ShieldCheck, RefreshCw, Database } from 'lucide-react';

const EMPTY_COUNTS = {};

export default function AiValidatedStatsBar({
  counts = EMPTY_COUNTS,
  questionsCount = 0,
  refreshing = false,
  onRefresh,
  onNavigateToBank
}) {
  return (
    <div className="validated-stats-banner">
      <div className="validated-stats-top-row">
        <div>
          <div className="validated-stats-title-group">
            <div className="validated-stats-icon-box">
              <ShieldCheck size={15} />
            </div>
            <h2 className="validated-stats-title">
              Review Queue
            </h2>
          </div>
        </div>

        <div className="validated-stats-actions">
          <button
            type="button"
            onClick={onRefresh}
            disabled={refreshing}
            className="btn-secondary validated-stats-btn-primary"
            title="Refresh questions list"
          >
            <RefreshCw size={12} className={refreshing ? 'animate-spin' : ''} />
            <span>Refresh</span>
          </button>
          {onNavigateToBank && (
            <button
              type="button"
              onClick={onNavigateToBank}
              className="btn-secondary validated-stats-btn-primary"
            >
              <Database size={12} />
              <span>Question Bank</span>
            </button>
          )}
        </div>
      </div>

      {/* Quick Metrics Bar */}
      <div className="validated-stats-strip">
        <div className="validated-stats-pill">
          <span className="validated-stats-label">Ready for Review:</span>
          <strong className="validated-stats-value is-success">
            {counts.ai_validated || questionsCount}
          </strong>
        </div>
        <span className="validated-stats-divider">•</span>
        <div className="validated-stats-pill">
          <span className="validated-stats-label">In Question Bank:</span>
          <strong className="validated-stats-value is-brand">
            {counts.in_bank || 0}
          </strong>
        </div>
        <span className="validated-stats-divider">•</span>
        <div className="validated-stats-pill">
          <span className="validated-stats-label">Good Quality:</span>
          <strong className="validated-stats-value is-indigo">
            {counts.batch_only || 0}
          </strong>
        </div>
      </div>
    </div>
  );
}
