import { useState, useCallback } from 'react';

const draftFrom = (question) => ({
  stem: question?.question_stem || '',
  stimulus: question?.stimulus_text || '',
  options: question?.options || [],
  explanation: question?.explanation || '',
  imageDescription: question?.image_description || '',
  showStimulusField: Boolean(question?.stimulus_text && question.stimulus_text.trim().length > 0)
});

/**
 * The editable copy of a question's text fields: one state object, one setter per field, and a
 * reset that returns to the saved question (used by Cancel).
 */
export function useQuestionDraft(question) {
  const [draft, setDraft] = useState(() => draftFrom(question));
  const setDraftField = useCallback((key, value) => {
    setDraft((prev) => ({ ...prev, [key]: value }));
  }, []);
  const resetDraft = useCallback(() => setDraft(draftFrom(question)), [question]);
  const toQuestion = useCallback(
    () => ({
      ...question,
      question_stem: draft.stem,
      stimulus_text: draft.stimulus,
      options: draft.options,
      explanation: draft.explanation,
      image_description: draft.imageDescription
    }),
    [question, draft]
  );
  return { draft, setDraftField, resetDraft, toQuestion };
}
