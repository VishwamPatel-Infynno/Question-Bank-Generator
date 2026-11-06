/** Formatters & metric calculation utilities */
export {
  countWords,
  formatExamTime,
  formatCostUsd,
  formatDurationMs,
  formatTokenCount,
  formatDate,
  formatDateTime,
  formatTime
} from './formatters';

/** MCAT cognitive trap detectors & resolvers */
export {
  resolveTrapInfo,
  detectTrapFromText,
  getEffectiveTrapInfo
} from './trapHelpers';

/** Export serializers (CSV, JSON, print HTML document) */
export {
  generateExamCsv,
  generateExamJson,
  generateExamHtmlDoc
} from './export';

/** Cognitive rationale & distractor extraction */
export {
  extractDistractorLines
} from './explanationHelpers';

/** Anti-guessability option length and balance checks */
export {
  calculateOptionSymmetry
} from './optionHelpers';

/** Batch lifecycle stages and progress calculations */
export {
  BATCH_LIFECYCLE_STAGES,
  getBatchStageInfo
} from './batchHelpers';

/** Question set job helpers and status resolution */
export {
  resolveQuestionStatus,
  computeJobQuestionCounts,
  hasJobPassage,
  hasJobDiagram,
  sortJobQuestions
} from './batchJobHelpers';

/** Question field helpers shared across cards, tables and exports */
export {
  formatQuestionForCopy,
  pickExportQuestions,
  getCorrectAnswerIds,
  isCorrectOption,
  formatCorrectAnswers,
  hasQuestionImage,
  getQuestionVisual,
  getReviewPillars,
  getAuditCostBreakdown,
  filterQuestionsByText
} from './questionHelpers';
export { toggleId, toggleAll, allSelected } from './selection';
export { sortPassages, passageQuestionCounts } from './passageHelpers';
export { buildBatchPayload } from './batchPayload';

/** Browser file download helper */
export { downloadTextFile } from './download';
