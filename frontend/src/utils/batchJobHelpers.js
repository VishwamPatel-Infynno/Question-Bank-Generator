/**
 * batchJobHelpers.js - Status resolution and filtering helpers for BatchJobCard and BatchQuestionItem.
 */

/**
 * Resolves the lifecycle status of a question within a batch job.
 */
export function resolveQuestionStatus(q) {
  if (!q) return 'below_threshold';
  if (q.status === 'discarded') return 'discarded';
  if (q.is_deleted) return 'deleted';
  if (q.status) return q.status;
  const score = q.final_score ?? 95;
  if (score > 90) return 'ai_validated';
  if (score > 85) return 'batch_only';
  return 'below_threshold';
}

/**
 * Computes breakdown counts of questions in a job.
 */
export function computeJobQuestionCounts(jobQuestions = []) {
  const deletedCount = jobQuestions.filter((q) => Boolean(q.is_deleted) && q.status !== 'discarded').length;
  const validatedCount = jobQuestions.filter((q) => !q.is_deleted && resolveQuestionStatus(q) === 'ai_validated').length;
  const batchOnlyCount = jobQuestions.filter((q) => !q.is_deleted && resolveQuestionStatus(q) === 'batch_only').length;
  const inBankCount = jobQuestions.filter((q) => !q.is_deleted && resolveQuestionStatus(q) === 'in_bank').length;
  const discardedCount = jobQuestions.filter((q) => !q.is_deleted && resolveQuestionStatus(q) === 'discarded').length;
  const belowCount = jobQuestions.filter((q) => !q.is_deleted && resolveQuestionStatus(q) === 'below_threshold').length;

  return {
    deletedCount,
    validatedCount,
    batchOnlyCount,
    inBankCount,
    discardedCount,
    belowCount
  };
}

/**
 * Checks if any question in the job contains reading passage stimulus text.
 */
export function hasJobPassage(jobQuestions = []) {
  return jobQuestions.some(
    (q) => Boolean(q.stimulus_text && q.stimulus_text.trim().length > 0)
  );
}

/**
 * Checks if any question in the job contains an image or diagram.
 */
export function hasJobDiagram(jobQuestions = []) {
  return jobQuestions.some(
    (q) =>
      Boolean(
        q.image_url ||
          q.image_svg ||
          q.stage_outcomes?.visual_stimulus?.image_url ||
          q.stage_outcomes?.visual_stimulus?.image_svg ||
          q.stage_outcomes?.passage_visual_stimulus?.image_url ||
          q.stage_outcomes?.passage_visual_stimulus?.image_svg
      )
  );
}

/**
 * Sorts job questions: kept questions (>85) first, then below threshold (<=85).
 * Discarded questions are excluded.
 */
export function sortJobQuestions(jobQuestions = []) {
  const visible = jobQuestions.filter((q) => q.status !== 'discarded');
  return [...visible].sort((a, b) => {
    const isKeptA = resolveQuestionStatus(a) !== 'below_threshold';
    const isKeptB = resolveQuestionStatus(b) !== 'below_threshold';
    if (isKeptA && !isKeptB) return -1;
    if (!isKeptA && isKeptB) return 1;
    return 0;
  });
}

