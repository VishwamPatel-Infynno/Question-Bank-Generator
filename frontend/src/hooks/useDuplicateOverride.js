import { useState, useCallback, useRef, useEffect } from 'react';
import { overrideQuestionDuplicate } from '../services';

/**
 * State for the duplicate compare dialog and the "Override and approve" action. The caller decides
 * what a successful override means for its own list through `onUpdated(question)`, which receives
 * the question the API returned (its `status` is trusted, since the backend keeps batch-only
 * questions out of the bank).
 *
 * @param {Object} [options]
 * @param {(toast: { type?: string, title: string, message?: string }) => void} [options.onShowToast]
 * @param {(question: Object) => void | Promise<void>} [options.onUpdated]
 * @returns {{
 *   compareQuestion: Object|null,
 *   isOverriding: boolean,
 *   openCompare: (question: Object) => void,
 *   closeCompare: () => void,
 *   handleOverride: (question: Object) => Promise<void>
 * }}
 */
export function useDuplicateOverride({ onShowToast, onUpdated } = {}) {
  const [compareQuestion, setCompareQuestion] = useState(null);
  const [isOverriding, setIsOverriding] = useState(false);
  const busyRef = useRef(false);

  // Latest callbacks without re-creating handleOverride (the rows that receive it are memoized)
  const callbacksRef = useRef({ onShowToast, onUpdated });
  useEffect(() => {
    callbacksRef.current = { onShowToast, onUpdated };
  }, [onShowToast, onUpdated]);

  const openCompare = useCallback((question) => setCompareQuestion(question), []);
  const closeCompare = useCallback(() => setCompareQuestion(null), []);

  const handleOverride = useCallback(async (question) => {
    if (!question || busyRef.current) return;
    busyRef.current = true;
    setIsOverriding(true);
    try {
      const res = await overrideQuestionDuplicate(question.id);
      const saved = res?.question || { ...question, is_duplicate_override: true };
      await callbacksRef.current.onUpdated?.(saved);
      setCompareQuestion(null);
      callbacksRef.current.onShowToast?.({
        type: 'success',
        title: 'Duplicate Warning Overridden',
        message: 'The question was approved even though it looks like another one.'
      });
    } catch (err) {
      console.error('Failed to override duplicate warning:', err);
      callbacksRef.current.onShowToast?.({
        type: 'error',
        title: 'Override Failed',
        message: err?.message || 'Could not override the duplicate warning.'
      });
    } finally {
      busyRef.current = false;
      setIsOverriding(false);
    }
  }, []);

  return { compareQuestion, isOverriding, openCompare, closeCompare, handleOverride };
}
