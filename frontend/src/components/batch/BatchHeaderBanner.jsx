import { Layers, RefreshCw, Sparkles } from 'lucide-react';

/**
 * BatchHeaderBanner
 *
 * Top banner bar for the Batch Activity view with page title,
 * refresh trigger, and navigation to the creation wizard.
 */
export default function BatchHeaderBanner({
  refreshing = false,
  onRefresh,
  onNavigateToWizard
}) {
  return (
    <div className="batch-activity-banner">
      <div className="batch-activity-banner-left">
        <div className="batch-activity-banner-icon">
          <Layers size={20} />
        </div>
        <div>
          <h1 className="batch-activity-banner-title">
            Batch Progress &amp; History
          </h1>
        </div>
      </div>

      {/* Global Action Tools */}
      <div className="batch-header-actions">
        <button
          type="button"
          className="btn-secondary batch-btn-refresh"
          onClick={onRefresh}
          disabled={refreshing}
          title="Refresh history from database"
        >
          <RefreshCw size={13} className={refreshing ? 'spin-icon' : ''} />
          <span>{refreshing ? 'Updating...' : 'Refresh'}</span>
        </button>

        {onNavigateToWizard && (
          <button
            type="button"
            className="btn-primary batch-btn-create"
            onClick={onNavigateToWizard}
          >
            <Sparkles size={14} />
            <span>+ Create New Questions</span>
          </button>
        )}
      </div>
    </div>
  );
}
