/**
 * Formatting and calculation utilities for MCAT Question Studio.
 */

export const PACING_SECONDS = {
  chem_phys: 96,
  cars: 101,
  bio_biochem: 96,
  psych_soc: 96,
  CP: 96,
  CARS: 101,
  BB: 96,
  PS: 96
};

/**
 * Calculates estimated test exam duration for a set of MCAT questions.
 * @param {Array} questions - Array of question objects with a .section property
 * @returns {string} Human-readable time duration e.g. "8 minutes"
 */
export function formatExamTime(questions) {
  if (!questions || questions.length === 0) return '0 minutes';
  const totalSeconds = questions.reduce((acc, q) => {
    const sec = PACING_SECONDS[q.section] || 96;
    return acc + sec;
  }, 0);
  const minutes = Math.ceil(totalSeconds / 60);
  return `${minutes} minute${minutes === 1 ? '' : 's'}`;
}

/**
 * Strips whitespace and counts words in text.
 * @param {string} text - The input string
 * @returns {number} Word count
 */
export function countWords(text) {
  if (!text) return 0;
  return String(text).trim().split(/\s+/).filter(Boolean).length;
}

/**
 * Formats a numeric USD cost to a fixed fractional display string.
 * @param {number} cost - Cost in USD
 * @returns {string} e.g. "$0.0014" or "$0.00"
 */
export function formatCostUsd(cost) {
  if (cost === undefined || cost === null || isNaN(cost)) return '$0.00';
  if (cost === 0) return '$0.00';
  if (cost < 0.0001) return '< $0.0001';
  return `$${cost.toFixed(4)}`;
}

/**
 * Formats token count with localized thousands separators.
 * @param {number} tokens - Token count
 * @returns {string} e.g. "1,420"
 */
export function formatTokenCount(tokens) {
  if (!tokens || isNaN(tokens)) return '0';
  return Number(tokens).toLocaleString();
}

/**
 * Formats an ISO date string into a readable short date.
 * @param {string} iso - ISO date string
 * @returns {string} Formatted date e.g. "Oct 28, 2026"
 */
export function formatDate(iso) {
  if (!iso) return '';
  try {
    const d = new Date(iso);
    if (isNaN(d.getTime())) return String(iso);
    return d.toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric'
    });
  } catch {
    return String(iso);
  }
}
