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
