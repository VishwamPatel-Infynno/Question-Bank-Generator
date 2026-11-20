import { useState, useCallback, useMemo } from 'react';
import {
  fetchBatchDetail,
  deleteBatch,
  stopBatch,
  retryBatchJobs,
  cancelAllBatches,
  updateQuestionStatus,
  restoreQuestion
} from '../services';
import { QUESTION_STATUS } from '../constants';
import { patchQuestionInDetails } from '../utils/batchHelpers';
import { useConfirmModal } from './useConfirmModal';
import { useDuplicateOverride } from './useDuplicateOverride';

/**
 * Lifecycle actions for batches (stop, retry, cancel all, delete) and for single questions
 * inside them (save to bank, restore), with their loading flags and toasts.
 *
 * @param {Object} deps
 * @param {(silent?: boolean) => Promise<void>} deps.loadBatches - Reloads the batch list
 * @param {Function} deps.setBatches
 * @param {Function} deps.setBatchDetails
 * @param {Function} deps.setExpandedBatchIds
 * @param {Function} [deps.onShowToast]
 * @param {() => void} [deps.onNavigateToBank]
 * @returns {{
 *   handleStopBatch: (batchId: string) => Promise<void>,
 *   handleRetryBatch: (batchId: string) => Promise<void>,
 *   handleCancelAllBatches: () => Promise<void>,
 *   handleDeleteBatch: (e: any, batchId: string) => void,
 *   handleSaveQuestionToBank: (question: any) => Promise<void>,
 *   handleRestoreQuestion: (question: any) => Promise<void>,
 *   handleRefreshBatch: (batchId: string) => Promise<void>,
 *   compareQuestion: object | null,
 *   isOverriding: boolean,
 *   openCompare: (question: object) => void,
 *   closeCompare: () => void,
 *   handleOverride: (question: object) => Promise<void>,
 *   stoppingBatchIds: Record<string, boolean>,
 *   retryingBatchIds: Record<string, boolean>,
 *   isCancellingAll: boolean,
 *   isDeletingBatch: boolean,
 *   confirmModal: object,
 *   closeConfirmModal: () => void
 * }} Batch and question mutation methods with loading states.
 */
export function useBatchMutations({
  loadBatches,
  setBatches,
  setBatchDetails,
  setExpandedBatchIds,
  onShowToast,
  onNavigateToBank
}) {
  const [stoppingBatchIds, setStoppingBatchIds] = useState({});
  const [retryingBatchIds, setRetryingBatchIds] = useState({});
  const [isDeletingBatch, setIsDeletingBatch] = useState(false);
  const [isCancellingAll, setIsCancellingAll] = useState(false);
  const { confirmModal, openConfirmModal, closeConfirmModal } = useConfirmModal('batch');

  /** Fires the parent's toast callback when it is wired (guards against unmounted callers). */
  const toast = useCallback(
    (payload) => {
      if (onShowToast) onShowToast(payload);
    },
    [onShowToast]
  );

  const viewInBank = useMemo(
    () => (onNavigateToBank ? { label: 'View in Bank', onClick: onNavigateToBank } : undefined),
    [onNavigateToBank]
  );

  // Runs a per-batch action, then refreshes the list and that batch's detail
  const runBatchAction = useCallback(
    async (batchId, setBusy, action, { success, failureTitle, logLabel }) => {
      setBusy((prev) => ({ ...prev, [batchId]: true }));
      try {
        await action(batchId);
        toast(success);
        await loadBatches(true);
        const detail = await fetchBatchDetail(batchId);
        setBatchDetails((prev) => ({ ...prev, [batchId]: detail }));
      } catch (err) {
        console.error(`Failed to ${logLabel}:`, err);
        toast({ type: 'error', title: failureTitle, message: err.message });
      } finally {
        setBusy((prev) => ({ ...prev, [batchId]: false }));
      }
    },
    [toast, loadBatches, setBatchDetails]
  );

  const handleStopBatch = useCallback(
    (batchId) =>
      runBatchAction(batchId, setStoppingBatchIds, stopBatch, {
        success: {
          type: 'info',
          title: 'Batch Stopped',
          message: 'Active background tasks halted. Generated questions remain preserved in the bank.'
        },
        failureTitle: 'Stop Failed',
        logLabel: 'stop batch'
      }),
    [runBatchAction]
  );

  const handleRetryBatch = useCallback(
    (batchId) =>
      runBatchAction(batchId, setRetryingBatchIds, retryBatchJobs, {
        success: {
          type: 'success',
          title: 'Incomplete Sets Resumed',
          message: 'Incomplete question sets have resumed generation.'
        },
        failureTitle: 'Retry Failed',
        logLabel: 'retry batch jobs'
      }),
    [runBatchAction]
  );

  const handleCancelAllBatches = useCallback(async () => {
    setIsCancellingAll(true);
    try {
      const res = await cancelAllBatches();
      toast({
        type: 'info',
        title: 'All Active Batches Stopped',
        message: res.message || 'All background batches have been stopped.'
      });
      await loadBatches(false);
    } catch (err) {
      console.error('Failed to cancel all batches:', err);
      toast({ type: 'error', title: 'Cancel All Failed', message: err.message });
    } finally {
      setIsCancellingAll(false);
    }
  }, [toast, loadBatches]);

  const handleDeleteBatch = useCallback(
    (e, batchId) => {
      e.stopPropagation();
      openConfirmModal({
        title: 'Delete Batch Record',
        description:
          'Are you sure you want to delete this batch history? Any questions you already saved to your Question Bank will remain safe.',
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
            toast({
              type: 'info',
              title: 'Batch Deleted',
              message: 'The batch log has been deleted.'
            });
            closeConfirmModal();
          } catch (err) {
            console.error('Failed to delete batch:', err);
            toast({ type: 'error', title: 'Delete Failed', message: err.message });
          } finally {
            setIsDeletingBatch(false);
          }
        }
      });
    },
    [openConfirmModal, toast, setBatches, setExpandedBatchIds, closeConfirmModal]
  );

  const handleSaveQuestionToBank = useCallback(
    async (question) => {
      try {
        await updateQuestionStatus(question.id, QUESTION_STATUS.IN_BANK);
        setBatchDetails((prev) =>
          patchQuestionInDetails(prev, question.id, { status: QUESTION_STATUS.IN_BANK })
        );
        toast({
          type: 'success',
          title: 'Saved to Question Bank',
          message: 'Question promoted directly into your official Question Bank.',
          action: viewInBank
        });
      } catch (err) {
        console.error('Failed to move question to bank:', err);
        toast({
          type: 'error',
          title: 'Action Failed',
          message: err.message || 'Could not move question to bank.'
        });
      }
    },
    [toast, viewInBank, setBatchDetails]
  );

  const handleRestoreQuestion = useCallback(
    async (question) => {
      try {
        await restoreQuestion(question.id);
        setBatchDetails((prev) =>
          patchQuestionInDetails(prev, question.id, {
            is_deleted: false,
            deleted_at: null,
            status: QUESTION_STATUS.IN_BANK
          })
        );
        toast({
          type: 'success',
          title: 'Question Restored',
          message: 'Question and stimulus restored back to your Question Bank.',
          action: viewInBank
        });
      } catch (err) {
        console.error('Failed to restore question:', err);
        toast({
          type: 'error',
          title: 'Restore Failed',
          message: err.message || 'Could not restore question.'
        });
      }
    },
    [toast, viewInBank, setBatchDetails]
  );

  /** Reloads the batch list and one batch's detail (used after a duplicate audit changes it). */
  const handleRefreshBatch = useCallback(
    async (batchId) => {
      await loadBatches(true);
      if (!batchId) return;
      try {
        const detail = await fetchBatchDetail(batchId);
        setBatchDetails((prev) => ({ ...prev, [batchId]: detail }));
      } catch (err) {
        console.error('Failed to refresh batch detail:', err);
      }
    },
    [loadBatches, setBatchDetails]
  );

  // Duplicate compare dialog and "Override and approve". Patch the cached question first so the
  // card updates at once, then refetch its batch: the API's ETag cache and the detail cache (only
  // re-fetched for running batches) would otherwise keep serving the old warning.
  const {
    compareQuestion,
    isOverriding,
    openCompare,
    closeCompare,
    handleOverride
  } = useDuplicateOverride({
    onShowToast,
    onUpdated: (saved) => {
      setBatchDetails((prev) =>
        patchQuestionInDetails(prev, saved.id, {
          status: saved.status,
          is_duplicate_override: saved.is_duplicate_override,
          duplicate_info: saved.duplicate_info
        })
      );
      handleRefreshBatch(saved.batch_id);
    }
  });

  return {
    handleStopBatch,
    handleRetryBatch,
    handleCancelAllBatches,
    handleDeleteBatch,
    handleSaveQuestionToBank,
    handleRestoreQuestion,
    handleRefreshBatch,
    compareQuestion,
    isOverriding,
    openCompare,
    closeCompare,
    handleOverride,
    stoppingBatchIds,
    retryingBatchIds,
    isCancellingAll,
    isDeletingBatch,
    confirmModal,
    closeConfirmModal
  };
}
