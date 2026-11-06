import { useState, useRef, useEffect, useMemo, useCallback } from 'react';
import {
  fetchPassages,
  fetchSinglePassage,
  savePassage,
  deletePassage,
  saveEditedQuestion
} from '../services/api';
import { useKeyboardShortcuts } from './useKeyboardShortcuts';
import { makeId } from '../utils/ids';
import { passageQuestionCounts, sortPassages } from '../utils';
import { useRequestGuard } from './useRequestGuard';
import { useDebouncedValue } from './useDebouncedValue';

/**
 * Custom hook encapsulating reading passages state, search debouncing,
 * master-detail selection, editorial desk operations, and cascade deletion.
 *
 * @param {Object} options
 * @param {(toast: { type?: string, title: string, message?: string }) => void} [options.onShowToast]
 * @param {any} [options.resetSignal] - Trigger to reset selection back to master catalog.
 * @param {() => void} [options.onRefreshCounts] - Trigger to update global navbar/dashboard counts.
 * @returns {Object} Passage bank state, computed values, and actions.
 */
export function usePassageBank({ onShowToast, resetSignal, onRefreshCounts } = {}) {
  const [passages, setPassages] = useState([]);
  const [loading, setLoading] = useState(true);
  const [passageToDelete, setPassageToDelete] = useState(null);
  const [isDeletingPassage, setIsDeletingPassage] = useState(false);

  // Filter & Search State
  const [searchQuery, setSearchQuery] = useState('');
  const debouncedSearch = useDebouncedValue(searchQuery);
  const [sectionFilter, setSectionFilter] = useState('');
  const [sortBy, setSortBy] = useState('newest');
  const searchInputRef = useRef(null);

  // Master-Detail Selected State
  const [selectedPassage, setSelectedPassage] = useState(null);
  const [selectedPassageQuestions, setSelectedPassageQuestions] = useState([]);
  const [isLoadingDetail, setIsLoadingDetail] = useState(false);

  // Return to master catalog whenever resetSignal changes (e.g. clicking Passages tab in Navbar)
  const isFirstMountRef = useRef(true);
  useEffect(() => {
    if (isFirstMountRef.current) {
      isFirstMountRef.current = false;
      return;
    }
    setSelectedPassage(null);
    setSelectedPassageQuestions([]);
  }, [resetSignal]);

  // Focus search on '/'
  useKeyboardShortcuts({
    onFocusSearch: () => searchInputRef.current?.focus()
  });

  const guard = useRequestGuard();

  // Fetch all passages and build question counts directly from server aggregation. Only the newest
  // request may write state or clear the loading flag (an aborted one must not).
  const performFetchPassages = useCallback(async (isSilent = false) => {
    const request = guard.begin();
    if (!isSilent) setLoading(true);
    try {
      const passageRes = await fetchPassages(
        {
          section: sectionFilter || undefined,
          search: debouncedSearch || undefined
        },
        request.signal
      );
      if (!request.isCurrent()) return;

      const fetchedPassages = passageRes?.passages || [];

      setPassages(fetchedPassages);
    } catch (err) {
      if (err.name === 'AbortError' || !request.isCurrent()) return;
      console.error('Failed to load passages:', err);
      if (onShowToast) {
        onShowToast({
          type: 'error',
          title: 'Load Failed',
          message: 'Could not retrieve reading passages from database.'
        });
      }
    } finally {
      if (request.isCurrent()) setLoading(false);
    }
  }, [guard, sectionFilter, debouncedSearch, onShowToast]);

  // Initial load and dependency-driven fetch on filter changes
  useEffect(() => {
    async function init() {
      await performFetchPassages(true);
    }
    init();
  }, [performFetchPassages]);

  // Sort passages locally
  // Question counts come with each passage from the server aggregate
  const questionCounts = useMemo(() => passageQuestionCounts(passages), [passages]);
  const sortedPassages = useMemo(() => sortPassages(passages, sortBy), [passages, sortBy]);

  // Total word count & metrics
  const totalWordCount = useMemo(() => {
    return passages.reduce((acc, p) => acc + (p.word_count || 0), 0);
  }, [passages]);

  const avgWordCount = passages.length > 0 ? Math.round(totalWordCount / passages.length) : 0;
  const hasActiveFilters = Boolean(searchQuery.trim() || sectionFilter);

  const handleClearAllFilters = () => {
    setSearchQuery('');
    setSectionFilter('');
  };

  // Open Passage Editorial Desk
  const handleSelectPassage = async (passage) => {
    setIsLoadingDetail(true);
    setSelectedPassage(passage);
    try {
      const res = await fetchSinglePassage(passage.id);
      if (res?.passage) {
        setSelectedPassage(res.passage);
        setSelectedPassageQuestions(res.questions || []);
      }
    } catch (err) {
      console.error('Failed to load passage detail:', err);
      // Fallback: keep existing passage and questions if available
      setSelectedPassageQuestions(passage.questions || []);
    } finally {
      setIsLoadingDetail(false);
    }
  };

  // Manual New Passage Creation
  const handleCreateNewPassage = () => {
    const newId = `passage-${makeId().slice(0, 8)}`;
    const blankPassage = {
      id: newId,
      title: 'New Reading Passage',
      section: sectionFilter || 'cars',
      subtopic: '',
      text: '',
      word_count: 0,
      image_url: null,
      image_svg: null,
      image_description: null,
      created_at: new Date().toISOString()
    };
    setSelectedPassage(blankPassage);
    setSelectedPassageQuestions([]);
  };

  // Save Passage Handler
  const handleSavePassage = async (updatedPassage) => {
    try {
      const res = await savePassage(updatedPassage);
      const saved = res.passage || updatedPassage;
      setSelectedPassage(saved);

      // Also update stimulus_text in local questions state
      setSelectedPassageQuestions((prev) =>
        prev.map((q) => ({ ...q, stimulus_text: saved.text }))
      );

      // Refresh passages list
      await performFetchPassages();

      if (onShowToast) {
        onShowToast({
          type: 'success',
          title: 'Passage Saved',
          message: 'Reading passage and linked question stimuli updated successfully.'
        });
      }
    } catch (err) {
      console.error('Failed to save passage:', err);
      if (onShowToast) {
        onShowToast({
          type: 'error',
          title: 'Save Failed',
          message: err.message || 'Could not save passage updates to database.'
        });
      }
      throw err;
    }
  };

  // Delete Passage Request (Opens Cascade Delete Modal)
  const handleRequestDeletePassage = (passage) => {
    if (!passage) return;
    const qCount =
      selectedPassage && selectedPassage.id === passage.id
        ? selectedPassageQuestions.length
        : questionCounts[passage.id] || 0;

    setPassageToDelete({
      ...passage,
      question_count: qCount
    });
  };

  // Confirm Cascade Delete
  const handleConfirmDeletePassage = async () => {
    if (!passageToDelete) return;
    setIsDeletingPassage(true);
    try {
      const res = await deletePassage(passageToDelete.id);
      const deletedQuestionsCount = res.deleted_questions_count || 0;

      // Clear selection if current passage was deleted
      if (selectedPassage && selectedPassage.id === passageToDelete.id) {
        setSelectedPassage(null);
        setSelectedPassageQuestions([]);
      }

      setPassageToDelete(null);

      // Refresh catalog list
      await performFetchPassages();

      // Trigger global navbar / app state counts refresh
      if (onRefreshCounts) {
        onRefreshCounts();
      }

      if (onShowToast) {
        onShowToast({
          type: 'info',
          title: 'Passage Deleted',
          message:
            deletedQuestionsCount > 0
              ? `Passage and ${deletedQuestionsCount} associated question(s) permanently removed.`
              : 'Passage removed from database.'
        });
      }
    } catch (err) {
      console.error('Failed to cascade delete passage:', err);
      if (onShowToast) {
        onShowToast({
          type: 'error',
          title: 'Delete Failed',
          message: err.message || 'Could not delete passage from database.'
        });
      }
    } finally {
      setIsDeletingPassage(false);
    }
  };

  // Update a single linked question from editorial desk
  const handleUpdateQuestion = async (updatedQuestion) => {
    try {
      await saveEditedQuestion(updatedQuestion);

      setSelectedPassageQuestions((prev) =>
        prev.map((q) => (q.id === updatedQuestion.id ? updatedQuestion : q))
      );

      if (onShowToast) {
        onShowToast({
          type: 'success',
          title: 'Question Updated',
          message: 'Changes saved to Question Bank.'
        });
      }
    } catch (err) {
      console.error('Failed to update question:', err);
      if (onShowToast) {
        onShowToast({
          type: 'error',
          title: 'Update Failed',
          message: 'Could not update question in database.'
        });
      }
      throw err; // lets the editor stay open with the user's changes
    }
  };

  return {
    // Data & state
    passages,
    sortedPassages,
    loading,
    questionCounts,
    totalWordCount,
    avgWordCount,
    // Filters & search
    searchQuery,
    setSearchQuery,
    debouncedSearch,
    sectionFilter,
    setSectionFilter,
    sortBy,
    setSortBy,
    searchInputRef,
    hasActiveFilters,
    handleClearAllFilters,
    // Master-detail state
    selectedPassage,
    setSelectedPassage,
    selectedPassageQuestions,
    isLoadingDetail,
    // Actions
    handleSelectPassage,
    handleCreateNewPassage,
    handleSavePassage,
    handleRequestDeletePassage,
    handleConfirmDeletePassage,
    handleUpdateQuestion,
    // Modal state
    passageToDelete,
    setPassageToDelete,
    isDeletingPassage
  };
}

