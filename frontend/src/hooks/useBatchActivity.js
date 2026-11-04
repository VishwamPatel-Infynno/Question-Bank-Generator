import { useState, useEffect, useCallback, useRef, useMemo } from 'react';
import {
  fetchBatches,
  fetchBatchDetail,
  deleteBatch,
  stopBatch,
  retryBatchJobs,
  cancelAllBatches,
  updateQuestionStatus,
  restoreQuestion
} from '../services/api';
import { SECTION_CODE_MAP } from '../constants/mcat';
import { useConfirmModal } from './useConfirmModal';
import { useKeyboardShortcuts } from './useKeyboardShortcuts';

/**
 * Custom hook encapsulating full batch management state, polling telemetry,
 * accordion caching, and lifecycle mutation actions for BatchActivityView.
 *
 * @param {Object} options
 * @param {(toast: { type?: string, title: string, message?: string, action?: any }) => void} [options.onShowToast]
 * @param {() => void} [options.onNavigateToBank]
 * @returns {Object} Batch activity state and actions
 */
export function useBatchActivity({ onShowToast, onNavigateToBank } = {}) {
  const [batches, setBatches] = useState([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [activeCount, setActiveCount] = useState(0);

  // Filter states
  const [scopeFilter, setScopeFilter] = useState('all'); // 'all' | 'mini' | 'full'
  const [statusFilter, setStatusFilter] = useState('all'); // 'all' | 'in_progress' | 'completed' | 'failed'
  const [sectionFilter, setSectionFilter] = useState('all');
  const [searchQuery, setSearchQuery] = useState('');
  const searchInputRef = useRef(null);

  // Focus search input on '/' shortcut
  useKeyboardShortcuts({
    onFocusSearch: () => searchInputRef.current?.focus()
  });

  // Multi-expand batch details cache: Set of expanded batch IDs
  const [expandedBatchIds, setExpandedBatchIds] = useState(new Set());
  const [batchDetails, setBatchDetails] = useState({});
  const [loadingDetails, setLoadingDetails] = useState({});

  // Individual action loading states
  const [stoppingBatchIds, setStoppingBatchIds] = useState({});
  const [retryingBatchIds, setRetryingBatchIds] = useState({});
  const [isDeletingBatch, setIsDeletingBatch] = useState(false);
  const [isCancellingAll, setIsCancellingAll] = useState(false);

  // Standardized accessible confirmation modal state hook
  const { confirmModal, openConfirmModal, closeConfirmModal } = useConfirmModal('batch');

  // Expanded job within the expanded batches: { [jobId]: boolean }
  const [expandedJobIds, setExpandedJobIds] = useState({});

  // Auto-refresh control
  const [autoRefresh, setAutoRefresh] = useState(true);
  const pollTimerRef = useRef(null);
  const expandedBatchIdsRef = useRef(expandedBatchIds);
  const onShowToastRef = useRef(onShowToast);

  useEffect(() => {
    expandedBatchIdsRef.current = expandedBatchIds;
  }, [expandedBatchIds]);

  useEffect(() => {
    onShowToastRef.current = onShowToast;
  }, [onShowToast]);

  // Fetch batch list asynchronously without synchronous pre-render state mutations
  const performFetchBatches = useCallback(async (isSilent = false) => {
    try {
      const data = await fetchBatches();
      setBatches(data.batches || []);
      setActiveCount(data.active_running_batches || 0);

      // Re-fetch details for any expanded batches that are in progress atomically
      const expandedIds = Array.from(expandedBatchIdsRef.current);
      const inProgressIds = expandedIds.filter((bId) => {
        const matchingBatch = data.batches?.find((b) => b.id === bId);
        return matchingBatch && matchingBatch.status === 'in_progress';
      });

      if (inProgressIds.length > 0) {
        const results = await Promise.allSettled(
          inProgressIds.map((bId) => fetchBatchDetail(bId))
        );
        const nextDetails = {};
        results.forEach((res, idx) => {
          if (res.status === 'fulfilled' && res.value) {
            nextDetails[inProgressIds[idx]] = res.value;
          }
        });
        if (Object.keys(nextDetails).length > 0) {
          setBatchDetails((prev) => ({ ...prev, ...nextDetails }));
        }
      }
    } catch (err) {
      console.error('Failed to load batches:', err);
      if (!isSilent && onShowToastRef.current) {
        onShowToastRef.current({
          type: 'error',
          title: 'Failed to Refresh',
          message: 'Could not connect to database to fetch batch logs.'
        });
      }
    } finally {
      setLoading(false);
      if (!isSilent) setRefreshing(false);
    }
  }, []);

  const loadBatches = useCallback(async (isSilent = false) => {
    if (!isSilent) setRefreshing(true);
    return performFetchBatches(isSilent);
  }, [performFetchBatches]);

  // Initial load on mount
  useEffect(() => {
    let ignore = false;
    async function init() {
      if (!ignore) {
        await performFetchBatches(true);
      }
    }
    init();
    return () => {
      ignore = true;
    };
  }, [performFetchBatches]);

  const hasActiveBatches = activeCount > 0 || batches.some((b) => b.status === 'in_progress');

  // Auto-polling effect (every 2.5s if active batches, else 8s, paused if window hidden)
  useEffect(() => {
    if (!autoRefresh) return;

    const intervalMs = hasActiveBatches ? 2500 : 8000;

    pollTimerRef.current = setInterval(() => {
      if (typeof document !== 'undefined' && document.visibilityState === 'hidden') return;
      loadBatches(true);
    }, intervalMs);

    const handleVisibilityChange = () => {
      if (document.visibilityState === 'visible') {
        loadBatches(true);
      }
    };
    document.addEventListener('visibilitychange', handleVisibilityChange);

    return () => {
      if (pollTimerRef.current) clearInterval(pollTimerRef.current);
      document.removeEventListener('visibilitychange', handleVisibilityChange);
    };
  }, [autoRefresh, hasActiveBatches, loadBatches]);

  // Handle multi-batch expansion toggle
  const handleToggleExpandBatch = async (batchId) => {
    setExpandedBatchIds((prev) => {
      const next = new Set(prev);
      if (next.has(batchId)) {
        next.delete(batchId);
      } else {
        next.add(batchId);
      }
      return next;
    });

    // Fetch batch detail if not yet cached or if in progress
    if (!batchDetails[batchId] || batchDetails[batchId]?.batch?.status === 'in_progress') {
      setLoadingDetails((prev) => ({ ...prev, [batchId]: true }));
      try {
        const detail = await fetchBatchDetail(batchId);
        setBatchDetails((prev) => ({ ...prev, [batchId]: detail }));
      } catch (err) {
        console.error('Failed to load batch detail:', err);
      } finally {
        setLoadingDetails((prev) => ({ ...prev, [batchId]: false }));
      }
    }
  };

  // Toggle individual job accordion
  const handleToggleJob = (jobId) => {
    setExpandedJobIds((prev) => ({
      ...prev,
      [jobId]: !prev[jobId]
    }));
  };

  // Stop a running batch
  const handleStopBatch = async (batchId) => {
    setStoppingBatchIds((prev) => ({ ...prev, [batchId]: true }));
    try {
      await stopBatch(batchId);
      if (onShowToast) {
        onShowToast({
          type: 'info',
          title: 'Batch Stopped',
          message: 'Active background tasks halted. Generated questions remain preserved in the bank.'
        });
      }
      await loadBatches(true);
      const detail = await fetchBatchDetail(batchId);
      setBatchDetails((prev) => ({ ...prev, [batchId]: detail }));
    } catch (err) {
      console.error('Failed to stop batch:', err);
      if (onShowToast) {
        onShowToast({
          type: 'error',
          title: 'Stop Failed',
          message: err.message
        });
      }
    } finally {
      setStoppingBatchIds((prev) => ({ ...prev, [batchId]: false }));
    }
  };

  // Retry incomplete or failed jobs in a batch
  const handleRetryBatch = async (batchId) => {
    setRetryingBatchIds((prev) => ({ ...prev, [batchId]: true }));
    try {
      await retryBatchJobs(batchId);
      if (onShowToast) {
        onShowToast({
          type: 'success',
          title: 'Incomplete Sets Resumed',
          message: 'Incomplete question sets have resumed generation.'
        });
      }
      await loadBatches(true);
      const detail = await fetchBatchDetail(batchId);
      setBatchDetails((prev) => ({ ...prev, [batchId]: detail }));
    } catch (err) {
      console.error('Failed to retry batch jobs:', err);
      if (onShowToast) {
        onShowToast({
          type: 'error',
          title: 'Retry Failed',
          message: err.message
        });
      }
    } finally {
      setRetryingBatchIds((prev) => ({ ...prev, [batchId]: false }));
    }
  };

  // Cancel all active background batches
  const handleCancelAllBatches = async () => {
    setIsCancellingAll(true);
    try {
      const res = await cancelAllBatches();
      if (onShowToast) {
        onShowToast({
          type: 'info',
          title: 'All Active Batches Stopped',
          message: res.message || 'All background batches have been stopped.'
        });
      }
      await loadBatches(false);
    } catch (err) {
      console.error('Failed to cancel all batches:', err);
      if (onShowToast) {
        onShowToast({
          type: 'error',
          title: 'Cancel All Failed',
          message: err.message
        });
      }
    } finally {
      setIsCancellingAll(false);
    }
  };

  // Delete a batch via Confirmation Modal
  const handleDeleteBatch = (e, batchId) => {
    e.stopPropagation();
    openConfirmModal({
      title: 'Delete Batch Record',
      description: 'Are you sure you want to delete this batch history? Any questions you already saved to your Question Bank will remain safe.',
      confirmLabel: 'Delete Batch',
      variant: 'danger',
      itemCount: 1,
      itemLabel: 'batch',
      onConfirm: async () => {
        setIsDeletingBatch(true);
        try {
          await deleteBatch(batchId);
          setBatches((prev) => prev.filter((b) => b.id !== batchId));
          setExpandedBatchIds((prev) => {
            const next = new Set(prev);
            next.delete(batchId);
            return next;
          });
          if (onShowToast) {
            onShowToast({
              type: 'info',
              title: 'Batch Deleted',
              message: 'The batch log has been deleted.'
            });
          }
          closeConfirmModal();
        } catch (err) {
          console.error('Failed to delete batch:', err);
          if (onShowToast) {
            onShowToast({
              type: 'error',
              title: 'Delete Failed',
              message: err.message
            });
          }
        } finally {
          setIsDeletingBatch(false);
        }
      }
    });
  };

  // Handle saving a question directly to Question Bank
  const handleSaveQuestionToBank = async (question) => {
    try {
      await updateQuestionStatus(question.id, 'in_bank');
      setBatchDetails((prev) => {
        const next = { ...prev };
        for (const [bId, detail] of Object.entries(next)) {
          if (!detail) continue;
          let changed = false;
          const updatedJobs = (detail.jobs || []).map((job) => {
            const hasQ = (job.questions || []).some((q) => q.id === question.id);
            if (!hasQ) return job;
            changed = true;
            return Object.assign({}, job, {
              questions: job.questions.map((q) =>
                q.id === question.id ? Object.assign({}, q, { status: 'in_bank' }) : q
              )
            });
          });
          const updatedQs = (detail.questions || []).map((q) =>
            q.id === question.id ? Object.assign({}, q, { status: 'in_bank' }) : q
          );
          if (changed) {
            next[bId] = {
              ...detail,
              jobs: updatedJobs,
              questions: updatedQs
            };
          }
        }
        return next;
      });

      if (onShowToast) {
        onShowToast({
          type: 'success',
          title: 'Saved to Question Bank',
          message: 'Question promoted directly into your official Question Bank.',
          action: onNavigateToBank ? { label: 'View in Bank', onClick: onNavigateToBank } : undefined
        });
      }
    } catch (err) {
      console.error('Failed to move question to bank:', err);
      if (onShowToast) {
        onShowToast({
          type: 'error',
          title: 'Action Failed',
          message: err.message || 'Could not move question to bank.'
        });
      }
    }
  };

  // Handle restoring a soft-deleted question back to Question Bank
  const handleRestoreQuestion = async (question) => {
    try {
      await restoreQuestion(question.id);
      setBatchDetails((prev) => {
        const next = { ...prev };
        for (const [bId, detail] of Object.entries(next)) {
          if (!detail) continue;
          let changed = false;
          const updatedJobs = (detail.jobs || []).map((job) => {
            const hasQ = (job.questions || []).some((q) => q.id === question.id);
            if (!hasQ) return job;
            changed = true;
            return Object.assign({}, job, {
              questions: job.questions.map((q) =>
                q.id === question.id
                  ? Object.assign({}, q, { is_deleted: false, deleted_at: null, status: 'in_bank' })
                  : q
              )
            });
          });
          const updatedQs = (detail.questions || []).map((q) =>
            q.id === question.id
              ? Object.assign({}, q, { is_deleted: false, deleted_at: null, status: 'in_bank' })
              : q
          );
          if (changed) {
            next[bId] = {
              ...detail,
              jobs: updatedJobs,
              questions: updatedQs
            };
          }
        }
        return next;
      });

      if (onShowToast) {
        onShowToast({
          type: 'success',
          title: 'Question Restored',
          message: 'Question and stimulus restored back to your Question Bank.',
          action: onNavigateToBank ? { label: 'View in Bank', onClick: onNavigateToBank } : undefined
        });
      }
    } catch (err) {
      console.error('Failed to restore question:', err);
      if (onShowToast) {
        onShowToast({
          type: 'error',
          title: 'Restore Failed',
          message: err.message || 'Could not restore question.'
        });
      }
    }
  };

  // Active batches list for multi-batch monitor
  const activeBatchesList = useMemo(
    () => batches.filter((b) => b.status === 'in_progress'),
    [batches]
  );

  // Filtered batches
  const filteredBatches = useMemo(() => {
    return batches.filter((b) => {
      if (scopeFilter === 'mini' && !(b.total_jobs === 1 || b.target_count === 5)) return false;
      if (scopeFilter === 'full' && !(b.total_jobs > 1 || b.target_count > 5)) return false;
      if (statusFilter !== 'all' && b.status !== statusFilter) return false;
      if (sectionFilter !== 'all') {
        const code = SECTION_CODE_MAP[b.section] || b.section;
        if (code !== sectionFilter && b.section !== sectionFilter) return false;
      }
      if (searchQuery.trim()) {
        const query = searchQuery.toLowerCase();
        const matchTopic = (b.subtopic || '').toLowerCase().includes(query);
        const matchSection = (b.section || '').toLowerCase().includes(query);
        const matchId = b.id.toLowerCase().includes(query);
        if (!matchTopic && !matchSection && !matchId) return false;
      }
      return true;
    });
  }, [batches, scopeFilter, statusFilter, sectionFilter, searchQuery]);

  return {
    // Data & status
    batches,
    filteredBatches,
    activeBatchesList,
    activeCount,
    hasActiveBatches,
    loading,
    refreshing,
    loadBatches,
    // Filters
    scopeFilter,
    setScopeFilter,
    statusFilter,
    setStatusFilter,
    sectionFilter,
    setSectionFilter,
    searchQuery,
    setSearchQuery,
    searchInputRef,
    autoRefresh,
    setAutoRefresh,
    // Expansion & detail caching
    expandedBatchIds,
    batchDetails,
    loadingDetails,
    handleToggleExpandBatch,
    expandedJobIds,
    handleToggleJob,
    // Actions & mutations
    handleStopBatch,
    handleRetryBatch,
    handleCancelAllBatches,
    handleDeleteBatch,
    handleSaveQuestionToBank,
    handleRestoreQuestion,
    stoppingBatchIds,
    retryingBatchIds,
    isCancellingAll,
    isDeletingBatch,
    // Modal
    confirmModal,
    closeConfirmModal
  };
}

