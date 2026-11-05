import {
  Layers,
  ShieldCheck,
  RotateCcw,
  CheckCircle2
} from 'lucide-react';

export const BATCH_LIFECYCLE_STAGES = [
  { id: 1, key: 'draft', label: '1. Drafting Sets', desc: 'Generating item drafts', icon: Layers },
  { id: 2, key: 'audit', label: '2. Duplicate Audit', desc: 'Clustering & quality checks', icon: ShieldCheck },
  { id: 3, key: 'refill', label: '3. In-Set Refill', desc: 'Autonomous replenishment', icon: RotateCcw },
  { id: 4, key: 'ready', label: '4. Ready for Review', desc: 'Promoted to Review Queue', icon: CheckCircle2 }
];

/**
 * Calculates current execution stage, badges, descriptions, and refill status for a batch.
 *
 * @param {Object} batch - GenerationBatch object.
 * @param {Object|null} [detail] - Detailed batch records including jobs and questions.
 * @returns {Object} Stage information object.
 */
export function getBatchStageInfo(batch, detail) {
  const isCompleted = batch.status === 'completed';
  const isPartial = batch.status === 'partially_completed';
  const isStopped = batch.status === 'stopped' || batch.status === 'cancelled';
  const isFailed = batch.status === 'failed';
  const isInProgress = batch.status === 'in_progress';

  const totalTarget = batch.target_count || 50;
  const actualTotal = batch.actual_count || 0;
  const completedJobs = batch.completed_jobs || 0;
  const totalJobs = batch.total_jobs || 10;

  const isRefilling = detail?.jobs?.some((j) => j.trial_count > 1 && j.status === 'running') || false;
  const hasEverRefilled = detail?.jobs?.some((j) => j.trial_count > 1) || false;

  const isAuditing = isInProgress && (completedJobs >= totalJobs || actualTotal >= totalTarget) && !isRefilling;

  let activeStep = 1;
  let stageBadge = 'Generating';
  let stageDescription = 'Generating questions across parallel sets';

  if (isCompleted) {
    activeStep = 4;
    stageBadge = 'Ready for Review';
    stageDescription = 'All sets generated & promoted to Review Queue';
  } else if (isPartial) {
    activeStep = 4;
    stageBadge = 'Trials Exhausted';
    stageDescription = 'Concluded with shortfalls after 3 replenishment trials';
  } else if (isStopped) {
    activeStep = 1;
    stageBadge = 'Stopped by User';
    stageDescription = 'Batch generation paused by user';
  } else if (isFailed) {
    activeStep = 1;
    stageBadge = 'Failed';
    stageDescription = batch.error_message || 'Batch encountered an unrecoverable error';
  } else if (isRefilling) {
    activeStep = 3;
    stageBadge = 'Autonomous Refill Active';
    stageDescription = 'Replenishing missing or duplicate slots in-set (Trial 2-3)';
  } else if (isAuditing) {
    activeStep = 2;
    stageBadge = 'Auditing Duplicates';
    stageDescription = 'Analyzing pairwise similarity (>75%) & quality thresholds';
  } else {
    activeStep = 1;
    stageBadge = 'Drafting Sets';
    stageDescription = `Drafting sets in parallel (${completedJobs}/${totalJobs} sets completed)`;
  }

  return {
    activeStep,
    stageBadge,
    stageDescription,
    isAuditing,
    isRefilling,
    hasEverRefilled
  };
}

const BATCH_SIGNATURE_FIELDS = [
  'status',
  'updated_at',
  'actual_count',
  'completed_jobs',
  'failed_jobs',
  'total_tokens',
  'cost_usd',
  'error_message'
];

function sameBatch(a, b) {
  return a.id === b.id && BATCH_SIGNATURE_FIELDS.every((field) => a[field] === b[field]);
}

/**
 * Structural sharing for poll results: keeps the previous object for every batch that did not
 * change, and returns the previous array itself when nothing changed at all. Memoized cards then
 * see identical props and skip rendering instead of re-rendering on every poll tick.
 * @param {Array<object>} prev - Batches currently in state
 * @param {Array<object>} next - Batches just fetched
 * @returns {Array<object>}
 */
export function reuseUnchangedBatches(prev, next) {
  if (!Array.isArray(prev) || prev.length === 0) return next;
  const previousById = new Map(prev.map((b) => [b.id, b]));
  let allSame = prev.length === next.length;
  const merged = next.map((batch, idx) => {
    const old = previousById.get(batch.id);
    if (old && sameBatch(old, batch)) {
      if (prev[idx] !== old) allSame = false;
      return old;
    }
    allSame = false;
    return batch;
  });
  return allSame ? prev : merged;
}
