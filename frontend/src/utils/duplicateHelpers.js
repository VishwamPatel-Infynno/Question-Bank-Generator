import { DUPLICATE_SOFT_THRESHOLD } from '../constants';

/**
 * @typedef {Object} DuplicateState
 * @property {'high'|'similar'|'overridden'|'none'} level
 * @property {number} percent - Similarity as a whole percent (0 when there is no info).
 * @property {boolean} isOverridden
 * @property {Object|null} info - The question's `duplicate_info`, if any.
 */

const NONE = Object.freeze({ level: 'none', percent: 0, isOverridden: false, info: null });

/**
 * Reads a question's duplicate info into one display state. "Similar" is derived on the client
 * (not flagged and similarity at or above the soft threshold) because the API only flags hard
 * duplicates.
 * @param {Object|null|undefined} q - Question record.
 * @returns {DuplicateState}
 */
export function getDuplicateState(q) {
  const info = q?.duplicate_info;
  if (!info) return NONE;
  const score = Number(info.similarity_score) || 0;
  const percent = Math.round(score * 100);
  const isOverridden = Boolean(info.is_overridden || q.is_duplicate_override);
  let level = 'none';
  if (isOverridden) level = 'overridden';
  else if (info.is_duplicate) level = 'high';
  else if (score >= DUPLICATE_SOFT_THRESHOLD) level = 'similar';
  if (level === 'none') return { ...NONE, info };
  return { level, percent, isOverridden, info };
}

/** True when the question is a hard duplicate or a similar one that has not been overridden. */
export function hasDuplicateAlert(q) {
  const { level } = getDuplicateState(q);
  return level === 'high' || level === 'similar';
}

/** True when there is a duplicate record worth comparing (flagged, similar or overridden). */
export function canCompare(q) {
  return getDuplicateState(q).level !== 'none';
}
