/** Pure helpers for presenting and exporting questions. */

/** Plain-text version of a question for the clipboard. */
export function formatQuestionForCopy(q) {
  return (
    `[AAMC MCAT - ${q.section_label || q.section}] (${q.difficulty})\n` +
    `${q.stimulus_text ? q.stimulus_text + '\n\n' : ''}` +
    `Question: ${q.question_stem}\n\n` +
    (q.options || []).map((o) => `${o.id}: ${o.text}`).join('\n') +
    `\n\nCorrect Answer: ${q.correct_answer_id}\n\nExplanation: ${q.explanation}`
  );
}

/**
 * Chooses which questions an export covers.
 * - 'selected' with a non-empty selection: those bank questions
 * - 'filtered' while filters are active: the filtered list
 * - anything else (including an empty selection): the whole bank pool
 * @param {{scope: string, selectedIds: string[], bankPool: object[], filteredQuestions: object[], hasActiveFilters: boolean}} args
 */
export function pickExportQuestions({
  scope,
  selectedIds,
  bankPool,
  filteredQuestions,
  hasActiveFilters
}) {
  if (scope === 'selected' && selectedIds.length > 0) {
    const wanted = new Set(selectedIds);
    return bankPool.filter((q) => wanted.has(q.id));
  }
  if (scope === 'filtered' && hasActiveFilters) return filteredQuestions;
  return bankPool;
}

/**
 * The correct option ids of a question, upper-cased and trimmed. Uses `correct_answer_ids` when
 * it is a non-empty list, else splits the comma-separated `correct_answer_id`.
 */
export function getCorrectAnswerIds(q) {
  const ids =
    Array.isArray(q?.correct_answer_ids) && q.correct_answer_ids.length > 0
      ? q.correct_answer_ids
      : String(q?.correct_answer_id ?? '').split(',');
  return ids.map((k) => String(k).trim().toUpperCase()).filter(Boolean);
}

/** True when `optionId` is one of the question's correct ids (case-insensitive). */
export function isCorrectOption(q, optionId) {
  return getCorrectAnswerIds(q).includes(String(optionId ?? '').trim().toUpperCase());
}

/** The correct ids joined for display ('A, C'), or `fallback` when none is recorded. */
export function formatCorrectAnswers(q, fallback = '') {
  const ids = getCorrectAnswerIds(q);
  return ids.length ? ids.join(', ') : fallback;
}

/** True when the question (or its shared passage) carries an image or vector diagram. */
export function hasQuestionImage(q) {
  const { svg, url } = getQuestionVisual(q);
  return Boolean(svg || url);
}

/**
 * The visual attached to a question: its own figure first, then the figure recorded in the
 * image stage, then the shared passage's figure. Every field is `''` when absent.
 */
export function getQuestionVisual(q) {
  const own = q || {};
  const stage = own.stage_outcomes?.visual_stimulus || {};
  const passage = own.stage_outcomes?.passage_visual_stimulus || {};
  const pick = (key) => own[key] || stage[key] || passage[key] || '';
  return {
    svg: pick('image_svg'),
    url: pick('image_url'),
    description: pick('image_description')
  };
}

/** The four 25-point reviewer pillars (score null when the rubric is missing). */
export function getReviewPillars(review) {
  return [
    { label: 'Scientific Style', score: review?.authenticity_score ?? null, max: 25, color: 'var(--brand-primary)' },
    { label: 'Clarity & Logic', score: review?.clarity_score ?? null, max: 25, color: 'var(--brand-indigo)' },
    { label: 'Wrong Answers', score: review?.distractor_score ?? null, max: 25, color: 'var(--status-warning)' },
    { label: 'Explanation Accuracy', score: review?.explanation_score ?? null, max: 25, color: 'var(--status-success)' }
  ];
}

/**
 * Splits a question's recorded cost into the visual part (only what the engine recorded for the
 * image stage) and the cognitive remainder, plus the per-stage timings that carry a duration.
 */
export function getAuditCostBreakdown(q) {
  const totalCost = Number(q?.cost_usd || 0);
  const stageTimings = (Array.isArray(q?.token_usage_details) ? q.token_usage_details : []).filter(
    (entry) => entry && Number(entry.duration_ms) > 0
  );
  const totalDurationMs = stageTimings.reduce((sum, entry) => sum + Number(entry.duration_ms), 0);
  const hasVisual = hasQuestionImage(q) || Boolean(q?.image_description);
  const visualCost = Number(q?.stage_outcomes?.visual_stimulus?.usage?.cost_usd || 0);
  return {
    totalCost,
    hasVisual,
    visualCost,
    cognitiveCost: Math.max(0, totalCost - (hasVisual ? visualCost : 0)),
    stageTimings,
    totalDurationMs
  };
}

/** Case-insensitive search over stem, subtopic, explanation and passage text. */
export function filterQuestionsByText(questions, query) {
  const q = String(query ?? '').trim().toLowerCase();
  if (!q) return questions;
  const hit = (v) => typeof v === 'string' && v.toLowerCase().includes(q);
  return questions.filter(
    (item) => hit(item.question_stem) || hit(item.subtopic) || hit(item.explanation) || hit(item.stimulus_text)
  );
}
