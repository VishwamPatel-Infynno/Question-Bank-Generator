const joinOr = (list, fallback) => (list && list.length > 0 ? list.join(', ') : fallback);

/**
 * The POST /batches/start payload for the wizard's form state. Pure: what the form holds in,
 * what the API receives out, so the mapping is unit-testable.
 */
export function buildBatchPayload(form) {
  const {
    selectedSection,
    selectedSubject,
    selectedUnit,
    selectedTopic,
    selectedSubtopic,
    selectedSkill,
    selectedSubskill,
    questionType,
    difficulty,
    totalQuestions,
    passageMode,
    passageRequired,
    primaryTrap,
    primaryTraps,
    likelyMistakePattern,
    likelyMistakePatterns,
    selectedSubskills,
    selectedSubtopics,
    allowAiImages,
    requireImage,
    additionalInstructions
  } = form;

  const isPassageMode = passageMode === 'single_passage';
  const isVisualsPermitted = Boolean(allowAiImages || requireImage);

  return {
    section: selectedSection,
    subject: selectedSubject || undefined,
    unit: selectedUnit || undefined,
    topic: selectedTopic || undefined,
    subtopic: joinOr(selectedSubtopics, selectedSubtopic),
    aamc_skill: selectedSkill || undefined,
    subskill: joinOr(selectedSubskills, selectedSubskill || undefined),
    question_type: questionType || (isPassageMode ? 'PASSAGE_BASED_MCQ' : 'DISCRETE_MCQ'),
    difficulty,
    questions_to_generate: totalQuestions,
    passage_count: isPassageMode ? (totalQuestions === 50 ? 10 : 1) : 0,
    passage_mode: passageMode,
    passage_question_count: isPassageMode ? totalQuestions : undefined,
    interaction_type: 'single_choice',
    passage_required: passageRequired,
    primary_trap: joinOr(primaryTraps, primaryTrap || 'Automatic'),
    likely_mistake_pattern: joinOr(likelyMistakePatterns, likelyMistakePattern || 'Automatic'),
    additional_instructions: additionalInstructions?.trim() || undefined,
    allow_ai_images: isVisualsPermitted,
    require_image: isVisualsPermitted && !isPassageMode && totalQuestions === 1,
    visual_type: isVisualsPermitted ? 'AI_FLUX_Image' : 'None',
    require_passage_image: isVisualsPermitted && isPassageMode
  };
}
