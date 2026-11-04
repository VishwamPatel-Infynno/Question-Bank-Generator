/**
 * optionHelpers.js - Utilities for analyzing question option symmetry and word counts.
 */

/**
 * Calculates mathematical option symmetry metrics across candidate choices.
 * Enforces AAMC anti-guessability standards (length disparity <= 1.25x).
 *
 * @param {Array<{id?: string, text: string}>} options - Array of 4 option objects.
 * @returns {Object|null} Symmetry breakdown including word counts, disparity ratio, and balance status.
 */
export function calculateOptionSymmetry(options) {
  if (!Array.isArray(options) || options.length === 0) return null;

  const counts = options.map((o) =>
    (o?.text || '').trim().split(/\s+/u).filter(Boolean).length
  );
  const minW = Math.min(...counts);
  const maxW = Math.max(...counts);
  const ratio = minW > 0 ? Number((maxW / minW).toFixed(2)) : 1.0;
  const isBalanced = ratio <= 1.25;

  return {
    disparity_ratio: ratio,
    min_word_count: minW,
    max_word_count: maxW,
    is_balanced: isBalanced,
    status: isBalanced
      ? 'Balanced'
      : ratio <= 1.4
        ? 'Moderate Disparity'
        : 'High Disparity',
    word_counts: Object.fromEntries(
      options.map((o, i) => [o?.id || String.fromCharCode(65 + i), counts[i]])
    ),
  };
}

