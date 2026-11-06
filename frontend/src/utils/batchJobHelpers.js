import { QUESTION_STATUS, SCORE_CUTOFFS } from '../constants';
import { hasQuestionImage } from './questionHelpers';

/**
 * batchJobHelpers.js - Status resolution and filtering helpers for BatchJobCard and BatchQuestionItem.
 */

/**
 * Resolves the lifecycle status of a question within a batch job.
 */
export function resolveQuestionStatus(q) {
  if (!q) return QUESTION_STATUS.BELOW_THRESHOLD;
  if (q.status === QUESTION_STATUS.DISCARDED) return QUESTION_STATUS.DISCARDED;
  if (q.is_deleted) return QUESTION_STATUS.DELETED;
  if (q.status) return q.status;
  const score = q.final_score ?? 95;
  if (score > SCORE_CUTOFFS.aiValidatedAbove) return QUESTION_STATUS.AI_VALIDATED;
  if (score > SCORE_CUTOFFS.batchAbove) return QUESTION_STATUS.BATCH_ONLY;
  return QUESTION_STATUS.BELOW_THRESHOLD;
}

/**
 * Computes breakdown counts of questions in a job.
 */
export function computeJobQuestionCounts(jobQuestions = []) {
  const deletedCount = jobQuestions.filter((q) => Boolean(q.is_deleted) && q.status !== QUESTION_STATUS.DISCARDED).length;
  const validatedCount = jobQuestions.filter((q) => !q.is_deleted && resolveQuestionStatus(q) === QUESTION_STATUS.AI_VALIDATED).length;
  const batchOnlyCount = jobQuestions.filter((q) => !q.is_deleted && resolveQuestionStatus(q) === QUESTION_STATUS.BATCH_ONLY).length;
  const inBankCount = jobQuestions.filter((q) => !q.is_deleted && resolveQuestionStatus(q) === QUESTION_STATUS.IN_BANK).length;
  const discardedCount = jobQuestions.filter((q) => !q.is_deleted && resolveQuestionStatus(q) === QUESTION_STATUS.DISCARDED).length;
  const belowCount = jobQuestions.filter((q) => !q.is_deleted && resolveQuestionStatus(q) === QUESTION_STATUS.BELOW_THRESHOLD).length;

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
  return jobQuestions.some(hasQuestionImage);
}

/**
 * Sorts job questions: kept questions (>85) first, then below threshold (<=85).
 * Discarded questions are excluded.
 */
export function sortJobQuestions(jobQuestions = []) {
  const visible = jobQuestions.filter((q) => q.status !== QUESTION_STATUS.DISCARDED);
  return [...visible].sort((a, b) => {
    const isKeptA = resolveQuestionStatus(a) !== QUESTION_STATUS.BELOW_THRESHOLD;
    const isKeptB = resolveQuestionStatus(b) !== QUESTION_STATUS.BELOW_THRESHOLD;
    if (isKeptA && !isKeptB) return -1;
    if (!isKeptA && isKeptB) return 1;
    return 0;
  });
}

