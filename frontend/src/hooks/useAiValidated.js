import { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import {
  fetchQuestions,
  fetchQuestionCounts,
  updateQuestionStatus,
  batchUpdateQuestionStatus,
  purgeQuestion,
  purgeQuestionsBatch
} from '../services/api';
import { useConfirmModal } from './useConfirmModal';
import { useKeyboardShortcuts } from './useKeyboardShortcuts';

/**
 * Custom hook encapsulating AI Validated questions state, search debouncing,
 * multi-selection, lifecycle promotion to Question Bank, and cascade purge actions.
 *
 * @param {Object} options
 * @param {(toast: { type?: string, title: string, message?: string, action?: any }) => void} [options.onShowToast]
 * @param {() => void} [options.onNavigateToBank]
 * @param {() => void} [options.onRefreshCounts]
 * @returns {Object} AI Validated questions state, computed values, and action handlers.
 */
export function useAiValidated({ onShowToast, onNavigateToBank, onRefreshCounts } = {}) {
  const [questions, setQuestions] = useState([]);
  const [counts, setCounts] = useState({
    ai_validated: 0,
    in_bank: 0,
    discarded: 0,
    below_threshold: 0
  });
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [actionInProgress, setActionInProgress] = useState(false);

  // Standardized accessible confirmation modal state hook
  const { confirmModal, openConfirmModal, closeConfirmModal } = useConfirmModal('question');

  // Filters & search
  const [searchQuery, setSearchQuery] = useState('');
  const [debouncedSearch, setDebouncedSearch] = useState('');
  const [sectionFilter, setSectionFilter] = useState('');
  const [expandedPassageIds, setExpandedPassageIds] = useState({});
  const searchInputRef = useRef(null);

  // Debounce search query by 250ms to ensure responsive filtering
  useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedSearch(searchQuery);
    }, 250);
    return () => clearTimeout(handler);
  }, [searchQuery]);

  // Focus search on '/'
  useKeyboardShortcuts({
    onFocusSearch: () => searchInputRef.current?.focus()
  });

  // Multi-selection state
  const [selectedIds, setSelectedIds] = useState([]);

  // Load questions and counts asynchronously without synchronous pre-render state mutations
  const performFetchValidated = useCallback(
    async (isSilent = false) => {
      try {
        const [qsRes, countsRes] = await Promise.all([
          fetchQuestions({
            status: 'ai_validated',
            section: sectionFilter || undefined,
            slim: true
          }),
          fetchQuestionCounts()
        ]);
        const loadedQs = qsRes.questions || [];
        setQuestions(loadedQs);
        setCounts(countsRes || {});
        // Hand over the counts we just loaded so the parent does not fetch them again
        if (onRefreshCounts) onRefreshCounts(countsRes);
      } catch (err) {
        console.error('Failed to load AI validated questions:', err);
        if (!isSilent && onShowToast) {
          onShowToast({
            type: 'error',
            title: 'Load Failed',
            message: 'Could not fetch validated questions from database.'
          });
        }
      } finally {
        setLoading(false);
        if (!isSilent) setRefreshing(false);
      }
    },
    [sectionFilter, onRefreshCounts, onShowToast]
  );

  const loadData = useCallback(
    async (isSilent = false) => {
      if (!isSilent) setRefreshing(true);
      return performFetchValidated(isSilent);
    },
    [performFetchValidated]
  );

  // Initial load on mount and when filter changes
  useEffect(() => {
    let ignore = false;
    async function init() {
      if (!ignore) {
        await performFetchValidated(true);
      }
    }
    init();
    return () => {
      ignore = true;
    };
  }, [performFetchValidated]);

  // Filtered in-memory questions by search query (strictly preserving score > 90 benchmark)
  const filteredQuestions = useMemo(() => {
    const validQuestions = questions.filter((item) => (item.final_score || 0) > 90);
    if (!debouncedSearch.trim()) return validQuestions;
    const q = debouncedSearch.toLowerCase().trim();
    return validQuestions.filter(
      (item) =>
        (item.question_stem && item.question_stem.toLowerCase().includes(q)) ||
        (item.subtopic && item.subtopic.toLowerCase().includes(q)) ||
        (item.explanation && item.explanation.toLowerCase().includes(q)) ||
        (item.stimulus_text && item.stimulus_text.toLowerCase().includes(q))
    );
  }, [questions, debouncedSearch]);

  // Toggle single selection
  const handleToggleSelect = (id) => {
    setSelectedIds((prev) =>
      prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]
    );
  };

  // Toggle select all
  const handleSelectAll = () => {
    const currentIds = filteredQuestions.map((q) => q.id);
    const allSelected =
      currentIds.length > 0 && currentIds.every((id) => selectedIds.includes(id));
    if (allSelected) {
      setSelectedIds((prev) => prev.filter((id) => !currentIds.includes(id)));
    } else {
      setSelectedIds((prev) => Array.from(new Set([...prev, ...currentIds])));
    }
  };

  // Single question actions
  const handleMoveToBankSingle = async (q) => {
    setActionInProgress(true);
    try {
      await updateQuestionStatus(q.id, 'in_bank');
      setQuestions((prev) => prev.filter((item) => item.id !== q.id));
      setSelectedIds((prev) => prev.filter((id) => id !== q.id));
      if (onShowToast) {
        onShowToast({
          type: 'success',
          title: 'Success - Question Saved to Bank',
          message: 'Question is now available in your Question Bank.',
          action: onNavigateToBank
            ? { label: 'View in Bank', onClick: onNavigateToBank }
            : undefined
        });
      }
      if (onRefreshCounts) onRefreshCounts();
      loadData(true);
    } catch (err) {
      console.error('Error promoting question:', err);
      if (onShowToast) {
        onShowToast({
          type: 'error',
          title: 'Action Failed',
          message: err.message || 'Could not move question.'
        });
      }
    } finally {
      setActionInProgress(false);
    }
  };

  const handleDiscardSingle = async (q) => {
    setActionInProgress(true);
    try {
      await purgeQuestion(q.id);
      setQuestions((prev) => prev.filter((item) => item.id !== q.id));
      setSelectedIds((prev) => prev.filter((id) => id !== q.id));
      if (onShowToast) {
        onShowToast({
          type: 'info',
          title: 'Question Discarded',
          message: 'Question has been permanently removed.'
        });
      }
      if (onRefreshCounts) onRefreshCounts();
      loadData(true);
    } catch (err) {
      console.error('Error discarding question:', err);
      if (onShowToast) {
        onShowToast({
          type: 'error',
          title: 'Action Failed',
          message: err.message || 'Could not discard question.'
        });
      }
    } finally {
      setActionInProgress(false);
    }
  };

  // Bulk actions
  const handleBulkMoveToBank = async () => {
    if (selectedIds.length === 0) return;
    const count = selectedIds.length;
    setActionInProgress(true);
    try {
      await batchUpdateQuestionStatus(selectedIds, 'in_bank');
      setQuestions((prev) => prev.filter((item) => !selectedIds.includes(item.id)));
      if (onShowToast) {
        onShowToast({
          type: 'success',
          title: 'Success - Saved to Bank',
          message: `Successfully placed ${count} question(s) into Question Bank.`,
          action: onNavigateToBank
            ? { label: 'View in Bank', onClick: onNavigateToBank }
            : undefined
        });
      }
      setSelectedIds([]);
      if (onRefreshCounts) onRefreshCounts();
      loadData(true);
    } catch (err) {
      console.error('Bulk move failed:', err);
      if (onShowToast) {
        onShowToast({
          type: 'error',
          title: 'Bulk Move Failed',
          message: err.message || 'Error updating questions.'
        });
      }
    } finally {
      setActionInProgress(false);
    }
  };

  const handleBulkDiscard = () => {
    if (selectedIds.length === 0) return;
    const count = selectedIds.length;
    openConfirmModal({
      title: 'Discard Selected Questions',
      description: `Are you sure you want to discard ${count} selected question${count !== 1 ? 's' : ''}? They will be permanently removed from the system.`,
      confirmLabel: `Discard ${count} Question${count !== 1 ? 's' : ''}`,
      variant: 'danger',
      itemCount: count,
      itemLabel: 'question',
      onConfirm: async () => {
        setActionInProgress(true);
        try {
          await purgeQuestionsBatch(selectedIds);
          setQuestions((prev) => prev.filter((item) => !selectedIds.includes(item.id)));
          if (onShowToast) {
            onShowToast({
              type: 'info',
              title: 'Questions Discarded',
              message: `Successfully purged ${count} question(s) from database.`
            });
          }
          setSelectedIds([]);
          closeConfirmModal();
          if (onRefreshCounts) onRefreshCounts();
          loadData(true);
        } catch (err) {
          console.error('Bulk discard failed:', err);
          if (onShowToast) {
            onShowToast({
              type: 'error',
              title: 'Bulk Discard Failed',
              message: err.message || 'Error purging questions.'
            });
          }
        } finally {
          setActionInProgress(false);
        }
      }
    });
  };

  const handleApproveAllValidated = async () => {
    const allIds = filteredQuestions.map((q) => q.id);
    if (allIds.length === 0) return;
    const count = allIds.length;
    setActionInProgress(true);
    try {
      await batchUpdateQuestionStatus(allIds, 'in_bank');
      setQuestions((prev) => prev.filter((item) => !allIds.includes(item.id)));
      setSelectedIds([]);
      if (onShowToast) {
        onShowToast({
          type: 'success',
          title: 'All Questions Saved to Bank',
          message: `${count} question(s) saved to Question Bank.`,
          action: onNavigateToBank
            ? { label: 'View in Bank', onClick: onNavigateToBank }
            : undefined
        });
      }
      if (onRefreshCounts) onRefreshCounts();
      loadData(true);
    } catch (err) {
      console.error('Save all questions failed:', err);
      if (onShowToast) {
        onShowToast({
          type: 'error',
          title: 'Action Failed',
          message: err.message || 'Error updating questions.'
        });
      }
    } finally {
      setActionInProgress(false);
    }
  };

  const togglePassage = (id) => {
    setExpandedPassageIds((prev) => ({ ...prev, [id]: !prev[id] }));
  };

  const allFilteredSelected =
    filteredQuestions.length > 0 &&
    filteredQuestions.every((q) => selectedIds.includes(q.id));

  return {
    // Data & state
    questions,
    filteredQuestions,
    counts,
    loading,
    refreshing,
    actionInProgress,
    loadData,
    // Filters & search
    searchQuery,
    setSearchQuery,
    debouncedSearch,
    sectionFilter,
    setSectionFilter,
    searchInputRef,
    // Selection
    selectedIds,
    setSelectedIds,
    allFilteredSelected,
    handleToggleSelect,
    handleSelectAll,
    // Accordion
    expandedPassageIds,
    togglePassage,
    // Actions
    handleMoveToBankSingle,
    handleDiscardSingle,
    handleBulkMoveToBank,
    handleBulkDiscard,
    handleApproveAllValidated,
    // Modal
    confirmModal,
    closeConfirmModal
  };
}

