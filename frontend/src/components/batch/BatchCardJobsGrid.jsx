import { memo } from 'react';
import { Layers } from 'lucide-react';
import BatchJobCard from './BatchJobCard';

const EMPTY_JOB_IDS = {};

function BatchCardJobsGrid({
  detail,
  loadingDetail,
  expandedJobIds = EMPTY_JOB_IDS,
  onToggleJob,
  onNavigateToBank,
  onNavigateToValidated,
  onOpenAudit,
  onSaveToBank,
  onRestoreQuestion
}) {
  return (
    <div className="batch-jobs-wrapper">
      {loadingDetail && !detail ? (
        <div className="batch-jobs-loading">
          <div className="batch-jobs-loading-spinner" />
          <span className="batch-jobs-header-subtitle">Loading question sets...</span>
        </div>
      ) : (
        <div className="batch-jobs-body">
          <div className="batch-jobs-header">
            <div className="batch-jobs-header-title">
              <Layers size={15} />
              <span>
                Question Sets ({detail?.jobs?.length || 0} sets &bull; 5 questions each):
              </span>
            </div>
            <div className="batch-jobs-header-subtitle">
              Generating sets in parallel
            </div>
          </div>

          {/* Jobs Grid */}
          {!detail?.jobs || detail.jobs.length === 0 ? (
            <div className="batch-jobs-empty">
              No question sets recorded for this practice batch.
            </div>
          ) : (
            <div className="batch-jobs-grid">
              {detail.jobs.map((job) => (
                <BatchJobCard
                  key={job.id}
                  job={job}
                  isExpanded={Boolean(expandedJobIds[job.id])}
                  onToggleExpand={onToggleJob}
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
      )}
    </div>
  );
}

export default memo(BatchCardJobsGrid);
