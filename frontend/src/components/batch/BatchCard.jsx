import { memo } from 'react';
import { getSectionColor } from '../../constants/mcat';
import { getBatchStageInfo } from '../../utils';
import BatchCardSummary from './BatchCardSummary';
import BatchLifecycleStepper from './BatchLifecycleStepper';
import BatchOutcomeCard from './BatchOutcomeCard';
import BatchCardJobsGrid from './BatchCardJobsGrid';

const EMPTY_JOB_IDS = {};

function BatchCard({
  batch,
  isExpanded,
  onToggleExpand,
  onDeleteBatch,
  onStopBatch,
  onRetryBatch,
  isStopping = false,
  isRetrying = false,
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
  const secColor = getSectionColor(batch.section);
  const totalJobs = batch.total_jobs || 10;
  const completedJobs = batch.completed_jobs || 0;
  const totalTarget = batch.target_count || 50;
  const actualTotal = batch.actual_count || 0;
  const isMiniSet = totalJobs === 1 || totalTarget === 5;
  const isCompleted = batch.status === 'completed';
  const isInProgress = batch.status === 'in_progress';

  // Accurate true progress percentage without artificial 95% caps
  const rawPercent = Math.min(100, Math.round((actualTotal / Math.max(1, totalTarget)) * 100));
  const progressPercent = isCompleted ? 100 : rawPercent;

  const stageInfo = getBatchStageInfo(batch, detail);

  return (
    <div className={`batch-card-wrapper ${isExpanded ? 'expanded' : ''}`}>
      {/* Batch Summary & Status Area (clickable to expand/collapse) */}
      <div
        onClick={() => onToggleExpand(batch.id)}
        onKeyDown={(e) => {
          // Only when the header itself has focus: Enter/Space on inner buttons keep their meaning
          if (e.target === e.currentTarget && (e.key === 'Enter' || e.key === ' ')) {
            e.preventDefault();
            onToggleExpand(batch.id);
          }
        }}
        role="button"
        tabIndex={0}
        aria-expanded={isExpanded}
        className={`batch-card-clickable ${isExpanded ? 'expanded' : ''}`}
      >
        <BatchCardSummary
          batch={batch}
          secColor={secColor}
          isExpanded={isExpanded}
          isMiniSet={isMiniSet}
          isCompleted={isCompleted}
          isInProgress={isInProgress}
          completedJobs={completedJobs}
          totalJobs={totalJobs}
          actualTotal={actualTotal}
          totalTarget={totalTarget}
          progressPercent={progressPercent}
          stageInfo={stageInfo}
          isStopping={isStopping}
          isRetrying={isRetrying}
          onStopBatch={onStopBatch}
          onRetryBatch={onRetryBatch}
          onDeleteBatch={onDeleteBatch}
        />

        {/* Dual-Track Lifecycle Stepper */}
        <BatchLifecycleStepper
          batch={batch}
          stageInfo={stageInfo}
          actualTotal={actualTotal}
          isCompleted={isCompleted}
          isInProgress={isInProgress}
        />

        {/* Contextual Outcome Banners */}
        <BatchOutcomeCard
          batch={batch}
          actualTotal={actualTotal}
          totalTarget={totalTarget}
          isCompleted={isCompleted}
          isRetrying={isRetrying}
          onRetryBatch={onRetryBatch}
          onNavigateToBank={onNavigateToBank}
          onNavigateToValidated={onNavigateToValidated}
        />
      </div>

      {/* Expanded Batch Detail: Question Sets */}
      {isExpanded && (
        <BatchCardJobsGrid
          detail={detail}
          loadingDetail={loadingDetail}
          expandedJobIds={expandedJobIds}
          onToggleJob={onToggleJob}
          onNavigateToBank={onNavigateToBank}
          onNavigateToValidated={onNavigateToValidated}
          onOpenAudit={onOpenAudit}
          onSaveToBank={onSaveToBank}
          onRestoreQuestion={onRestoreQuestion}
        />
      )}
    </div>
  );
}

export default memo(BatchCard);
