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
import { useRequestGuard } from './useRequestGuard';
import { useDebouncedValue } from './useDebouncedValue';
import { QUESTION_STATUS, SCORE_CUTOFFS } from '../constants';
import { allSelected, filterQuestionsByText, toggleAll, toggleId } from '../utils';

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
  const [loadError, setLoadError] = useState(null);
  const [refreshing, setRefreshing] = useState(false);
  const [actionInProgress, setActionInProgress] = useState(false);

  // Standardized accessible confirmation modal state hook
  const { confirmModal, openConfirmModal, closeConfirmModal } = useConfirmModal('question');

  // Filters & search
  const [searchQuery, setSearchQuery] = useState('');
  const debouncedSearch = useDebouncedValue(searchQuery);
  const [sectionFilter, setSectionFilter] = useState('');
  const [expandedPassageIds, setExpandedPassageIds] = useState({});
  const searchInputRef = useRef(null);

  // Focus search on '/'
  useKeyboardShortcuts({
    onFocusSearch: () => searchInputRef.current?.focus()
  });

  // Multi-selection state
  const [selectedIds, setSelectedIds] = useState([]);

  // Load questions and counts asynchronously without synchronous pre-render state mutations
  const guard = useRequestGuard();

  const performFetchValidated = useCallback(
    async (isSilent = false) => {
      // Only the newest request may write state: a slow response for an old filter must not
      // overwrite the list for the current one.
      const request = guard.begin();
      try {
        const [qsRes, countsRes] = await Promise.all([
          fetchQuestions({
            status: QUESTION_STATUS.AI_VALIDATED,
            section: sectionFilter || undefined,
            slim: true
          }, request.signal),
          fetchQuestionCounts()
        ]);
        if (!request.isCurrent()) return;
        const loadedQs = qsRes.questions || [];
        setLoadError(null);
        setQuestions(loadedQs);
        setCounts(countsRes || {});
        // Hand over the counts we just loaded so the parent does not fetch them again
        if (onRefreshCounts) onRefreshCounts(countsRes);
      } catch (err) {
        if (!request.isCurrent()) return;
        console.error('Failed to load AI validated questions:', err);
        setLoadError(err.message || 'Request failed');
        if (!isSilent && onShowToast) {
          onShowToast({
            type: 'error',
            title: 'Load Failed',
            message: 'Could not fetch validated questions from database.'
          });
        }
      } finally {
        if (request.isCurrent()) {
          setLoading(false);
          if (!isSilent) setRefreshing(false);
        }
      }
    },
    [guard, sectionFilter, onRefreshCounts, onShowToast]
  );

  const loadData = useCallback(
    async (isSilent = false) => {
      if (!isSilent) setRefreshing(true);
      return performFetchValidated(isSilent);
    },
    [performFetchValidated]
  );

  // Initial load on mount and when the filter changes
  useEffect(() => {
    async function init() {
      await performFetchValidated(true);
    }
    init();
  }, [performFetchValidated]);

  // Filtered in-memory questions by search query (strictly preserving score > 90 benchmark)
  const filteredQuestions = useMemo(() => {
    const validQuestions = questions.filter(
      (item) => (item.final_score || 0) > SCORE_CUTOFFS.aiValidatedAbove
    );
    return filterQuestionsByText(validQuestions, debouncedSearch);
  }, [questions, debouncedSearch]);

  const handleToggleSelect = (id) => setSelectedIds((prev) => toggleId(prev, id));
  const handleSelectAll = () =>
    setSelectedIds((prev) => toggleAll(prev, filteredQuestions.map((q) => q.id)));

  const toast = (payload) => {
    if (onShowToast) onShowToast(payload);
  };
  const viewInBank = onNavigateToBank ? { label: 'View in Bank', onClick: onNavigateToBank } : undefined;

  /**
   * Runs one lifecycle action: calls the API, drops the affected questions from the list and the
   * selection, shows the toast, then reloads (the reload also refreshes the global counts).
   */
  const runMutation = async ({ call, removeIds, successToast, errorTitle, afterSuccess }) => {
    setActionInProgress(true);
    try {
      await call();
      const gone = new Set(removeIds);
      setQuestions((prev) => prev.filter((item) => !gone.has(item.id)));
      setSelectedIds((prev) => prev.filter((id) => !gone.has(id)));
      toast(successToast);
      if (afterSuccess) afterSuccess();
      loadData(true);
    } catch (err) {
      console.error(`${errorTitle}:`, err);
      toast({ type: 'error', title: errorTitle, message: err.message || 'Error updating questions.' });
    } finally {
      setActionInProgress(false);
    }
  };

  const handleMoveToBankSingle = (q) =>
    runMutation({
      call: () => updateQuestionStatus(q.id, QUESTION_STATUS.IN_BANK),
      removeIds: [q.id],
      successToast: {
        type: 'success',
        title: 'Success - Question Saved to Bank',
        message: 'Question is now available in your Question Bank.',
        action: viewInBank
      },
      errorTitle: 'Action Failed'
    });

  const handleDiscardSingle = (q) =>
    openConfirmModal({
      title: 'Discard Question',
      description:
        'Are you sure you want to discard this question? It will be permanently removed from the system.',
      confirmLabel: 'Discard Question',
      variant: 'danger',
      itemCount: 1,
      itemLabel: 'question',
      onConfirm: () =>
        runMutation({
          call: () => purgeQuestion(q.id),
          removeIds: [q.id],
          successToast: {
            type: 'info',
            title: 'Question Discarded',
            message: 'Question has been permanently removed.'
          },
          errorTitle: 'Action Failed',
          afterSuccess: closeConfirmModal
        })
    });

  const handleBulkMoveToBank = () => {
    if (selectedIds.length === 0) return;
    const ids = [...selectedIds];
    return runMutation({
      call: () => batchUpdateQuestionStatus(ids, QUESTION_STATUS.IN_BANK),
      removeIds: ids,
      successToast: {
        type: 'success',
        title: 'Success - Saved to Bank',
        message: `Successfully placed ${ids.length} question(s) into Question Bank.`,
        action: viewInBank
      },
      errorTitle: 'Bulk Move Failed'
    });
  };

  const handleBulkDiscard = () => {
    if (selectedIds.length === 0) return;
    const ids = [...selectedIds];
    const count = ids.length;
    openConfirmModal({
      title: 'Discard Selected Questions',
      description: `Are you sure you want to discard ${count} selected question${count !== 1 ? 's' : ''}? They will be permanently removed from the system.`,
      confirmLabel: `Discard ${count} Question${count !== 1 ? 's' : ''}`,
      variant: 'danger',
      itemCount: count,
      itemLabel: 'question',
      onConfirm: () =>
        runMutation({
          call: () => purgeQuestionsBatch(ids),
          removeIds: ids,
          successToast: {
            type: 'info',
            title: 'Questions Discarded',
            message: `Successfully purged ${count} question(s) from database.`
          },
          errorTitle: 'Bulk Discard Failed',
          afterSuccess: closeConfirmModal
        })
    });
  };

  const handleApproveAllValidated = () => {
    const allIds = filteredQuestions.map((q) => q.id);
    if (allIds.length === 0) return;
    const count = allIds.length;
    // One click can move every listed question into the bank, so ask first
    openConfirmModal({
      title: 'Save All to Question Bank',
      description: `Save ${count} validated question${count !== 1 ? 's' : ''} to the Question Bank${debouncedSearch || sectionFilter ? ' (only those matching your current filters)' : ''}?`,
      confirmLabel: `Save ${count} Question${count !== 1 ? 's' : ''}`,
      variant: 'info',
      itemCount: count,
      itemLabel: 'question',
      onConfirm: () =>
        runMutation({
          call: () => batchUpdateQuestionStatus(allIds, QUESTION_STATUS.IN_BANK),
          removeIds: allIds,
          successToast: {
            type: 'success',
            title: 'All Questions Saved to Bank',
            message: `${count} question(s) saved to Question Bank.`,
            action: viewInBank
          },
          errorTitle: 'Action Failed',
          afterSuccess: closeConfirmModal
        })
    });
  };

  const togglePassage = (id) => {
    setExpandedPassageIds((prev) => ({ ...prev, [id]: !prev[id] }));
  };

  const allFilteredSelected = allSelected(selectedIds, filteredQuestions.map((q) => q.id));

  return {
    // Data & state
    questions,
    filteredQuestions,
    counts,
    loading,
    loadError,
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

