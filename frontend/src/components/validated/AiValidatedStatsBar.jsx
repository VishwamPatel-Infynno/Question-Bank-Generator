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
          <span className="text-muted">Ready for Review:</span>
          <strong className="text-success font-bold">
            {counts.ai_validated || questionsCount}
          </strong>
        </div>
        <span className="validated-stats-divider">•</span>
        <div className="validated-stats-pill">
          <span className="text-muted">In Question Bank:</span>
          <strong className="text-brand font-bold">
            {counts.in_bank || 0}
          </strong>
        </div>
        <span className="validated-stats-divider">•</span>
        <div className="validated-stats-pill">
          <span className="text-muted">Good Quality:</span>
          <strong className="text-indigo font-bold">
            {counts.batch_only || 0}
          </strong>
        </div>
      </div>
    </div>
  );
}
