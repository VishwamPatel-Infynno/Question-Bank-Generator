/**
 * Pure state updates for the generator form (used by useGeneratorForm). Each function takes the
 * previous form state and returns the next one, so the logic is unit-testable without React.
 */

/** Values the wizard sends to mean "clear the explicit subtopic selection". */
export const SUBTOPIC_RESET_VALUES = Object.freeze([
  'All',
  'Automatic',
  'All Core Topics',
  'All Concepts in Topic',
  'All Core Topics (Balanced Mix)',
  'All High-Yield Topics (Balanced Mix)'
]);

/** Adds `item` to `list` when absent, removes it when present. */
export function toggleInList(list, item) {
  const current = list || [];
  return current.includes(item) ? current.filter((x) => x !== item) : [...current, item];
}

/** The subtopic label shown when nothing is explicitly selected. */
export function defaultSubtopicLabel(selectedTopic) {
  return selectedTopic ? `${selectedTopic} (All Concepts)` : 'All High-Yield Topics (Balanced Mix)';
}

/**
 * Toggles one subtopic (or clears the selection for a reset value) and keeps the summary
 * `selectedSubtopic` label in step with the list.
 */
export function toggleSubtopicState(prev, subtopic) {
  if (SUBTOPIC_RESET_VALUES.includes(subtopic)) {
    return {
      ...prev,
      selectedSubtopics: [],
      selectedSubtopic: defaultSubtopicLabel(prev.selectedTopic)
    };
  }
  const next = toggleInList(prev.selectedSubtopics, subtopic);
  return {
    ...prev,
    selectedSubtopics: next,
    selectedSubtopic: next.length === 0 ? defaultSubtopicLabel(prev.selectedTopic) : next.join(', ')
  };
}
