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
  DISTRACTOR_HEADER_REGEX,
  extractDistractorLines,
  parseMentorExplanation
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
  sortJobQuestions,
  resolveJobActualCount,
  isJobShortfall
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
/** Duplicate warning state derived from a question's duplicate_info */
export {
  getDuplicateState,
  hasDuplicateAlert,
  canCompare
} from './duplicateHelpers';

export { toggleId, toggleAll, allSelected } from './selection';
export { sortPassages, passageQuestionCounts } from './passageHelpers';
export { buildBatchPayload } from './batchPayload';

/** Browser file download helper */
export { downloadTextFile } from './download';

/** Visual stimulus modality detection & presentation metadata */
export {
  detectVisualModality,
  getModalityMetadata
} from './visualHelpers';

/** RFC4122-style client-side UUID generation fallback */
export { makeId } from './ids';

/** Keyboard focus selection helpers */
export { nextEnabledIndex } from './selectHelpers';

/** Pure taxonomy topic extraction and hierarchy flatteners */
export {
  flattenTopics,
  OVERVIEW_UNITS_PER_SUBJECT,
  OVERVIEW_TOPICS_PER_UNIT
} from './taxonomyHelpers';

/** Pagination configuration and option normalizers */
export {
  PAGE_SIZE_OPTIONS,
  normalizePageSizeOptions
} from './pagination';

/** Generator form state manipulation & exam section rules */
export {
  SUBTOPIC_RESET_VALUES,
  toggleInList,
  defaultSubtopicLabel,
  toggleSubtopicState,
  applySectionRules
} from './generatorFormState';


