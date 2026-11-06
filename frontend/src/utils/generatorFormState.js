import { SECTION_IDS, getSkillsForSection } from '../constants/mcat';

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

/** The subtopic label shown when nothing is explicitly selected (uses the topic's display name). */
export function defaultSubtopicLabel(form) {
  const topicName = typeof form === 'string' ? form : form?.selectedTopicName || form?.selectedTopic;
  return topicName ? `${topicName} (All Concepts)` : 'All High-Yield Topics (Balanced Mix)';
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
      selectedSubtopic: defaultSubtopicLabel(prev)
    };
  }
  const next = toggleInList(prev.selectedSubtopics, subtopic);
  return {
    ...prev,
    selectedSubtopics: next,
    selectedSubtopic: next.length === 0 ? defaultSubtopicLabel(prev) : next.join(', ')
  };
}

/**
 * The field updates that switching the exam section implies. CARS is passage-only with no
 * figures and its own skill list; the science sections re-enable AI figures. Used by the wizard's
 * section picker and by the hero presets so both paths apply the same rules.
 */
export function applySectionRules(form, sectionId) {
  const firstSkill = getSkillsForSection(sectionId)[0];
  const common = {
    selectedSection: sectionId,
    selectedSubject: '',
    selectedUnit: '',
    selectedTopic: '',
    selectedTopicName: '',
    selectedSubtopic: 'All Core Topics (Balanced Mix)',
    selectedSubtopics: [],
    selectedSubskill: firstSkill?.subskills?.[0] || '',
    selectedSubskills: []
  };
  if (sectionId === SECTION_IDS.CARS) {
    return {
      ...common,
      selectedSkill: firstSkill?.id || 'CARS1',
      passageMode: 'single_passage',
      passageRequired: 'Yes',
      questionType: 'PASSAGE_BASED_MCQ',
      requireImage: false,
      allowAiImages: false,
      requirePassageImage: false,
      visual_type: 'None'
    };
  }
  return {
    ...common,
    selectedSkill: firstSkill?.id || 'S1',
    allowAiImages: true,
    requireImage: true,
    requirePassageImage: true,
    visual_type: 'AI_FLUX_Image'
  };
}
