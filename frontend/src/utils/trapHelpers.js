import { MCAT_TRAP_DEFINITIONS } from '../constants/mcatTraps';

/**
 * Resolves a normalized trap key to user-friendly label and advice.
 * @param {string} trapKeyOrName - Trap code or raw text label
 * @returns {object|null} Object with key, label, advice
 */
export function resolveTrapInfo(trapKeyOrName) {
  if (!trapKeyOrName) return null;
  const clean = String(trapKeyOrName).trim();
  if (clean === 'Automatic' || clean === 'None') return null;

  // Direct lookup
  if (MCAT_TRAP_DEFINITIONS[clean]) {
    return { key: clean, ...MCAT_TRAP_DEFINITIONS[clean] };
  }

  // Look up by matching label or normalized key
  const normClean = clean.toLowerCase().replace(/[_\s-]+/g, ' ');
  for (const [k, info] of Object.entries(MCAT_TRAP_DEFINITIONS)) {
    const normKey = k.toLowerCase().replace(/[_\s-]+/g, ' ');
    const normLabel = info.label.toLowerCase().replace(/[_\s-]+/g, ' ');
    if (normKey === normClean || normLabel === normClean || normClean.includes(normKey) || normClean.includes(normLabel)) {
      return { key: k, ...info };
    }
  }

  // Fallback to formatted string
  return {
    key: clean,
    label: clean.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase()),
    advice: 'Read question stems carefully and watch out for tempting choices that look true but do not answer what was asked.'
  };
}

/**
 * Detects the most prominent trap mentioned in explanation text.
 * @param {string} text - Explanation or review text
 * @returns {object|null} Matched trap info object
 */
export function detectTrapFromText(text) {
  if (!text) return null;
  for (const [k, info] of Object.entries(MCAT_TRAP_DEFINITIONS)) {
    const pattern = new RegExp(info.label.replace(/[.*+?^${}()|[\]\\]/g, '\\$&') + `|${k.replace(/_/g, '\\s*')}`, 'i');
    if (pattern.test(text)) {
      return { key: k, ...info };
    }
  }
  return null;
}

/**
 * Derives the effective primary trap info (key, label, advice) for a question.
 * @param {object} question - Question object
 * @returns {object|null} Resolved trap info
 */
export function getEffectiveTrapInfo(question) {
  if (!question) return null;
  const t = question.primary_trap;
  if (!t || t === 'Automatic' || t === 'None') {
    return detectTrapFromText(question.explanation || '');
  }
  return resolveTrapInfo(t);
}
