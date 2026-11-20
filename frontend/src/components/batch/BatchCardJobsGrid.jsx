import { memo } from 'react';
import { Layers } from 'lucide-react';
import BatchJobCard from './BatchJobCard';
import BatchDuplicateAudit from './BatchDuplicateAudit';

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
  onRestoreQuestion,
  onCompareDuplicate,
  onOverrideDuplicate,
  onShowToast,
  onRefreshBatch
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

          {detail?.batch?.id && (
            <BatchDuplicateAudit
              batchId={detail.batch.id}
              onShowToast={onShowToast}
              onResolved={onRefreshBatch}
            />
          )}

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
                  onCompareDuplicate={onCompareDuplicate}
                  onOverrideDuplicate={onOverrideDuplicate}
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
