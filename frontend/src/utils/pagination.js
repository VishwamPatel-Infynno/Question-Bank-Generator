/** The page sizes the views offer; -1 means "all". */
export const PAGE_SIZE_OPTIONS = Object.freeze([15, 30, 50, -1]);

/**
 * Accepts page sizes as numbers (`[10, 25]`) or `{value, label}` objects and returns the object
 * form CustomSelect needs. Numbers get their own text as label and -1 becomes 'All'.
 */
export function normalizePageSizeOptions(options) {
  return (options || []).map((opt) => {
    if (opt !== null && typeof opt === 'object') return opt;
    const value = Number(opt);
    return { value, label: value === -1 ? 'All' : String(value) };
  });
}
