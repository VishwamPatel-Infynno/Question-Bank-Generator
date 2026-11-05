import { useState } from 'react';
import {
  fetchBatchDetail,
  deleteBatch,
  stopBatch,
  retryBatchJobs,
  cancelAllBatches,
  updateQuestionStatus,
  restoreQuestion
} from '../services/api';
import { QUESTION_STATUS } from '../constants';
import { patchQuestionInDetails } from '../utils/batchHelpers';
import { useConfirmModal } from './useConfirmModal';

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

  const toast = (payload) => {
    if (onShowToast) onShowToast(payload);
  };
  const viewInBank = onNavigateToBank
    ? { label: 'View in Bank', onClick: onNavigateToBank }
    : undefined;

  // Runs a per-batch action, then refreshes the list and that batch's detail
  const runBatchAction = async (batchId, setBusy, action, { success, failureTitle, logLabel }) => {
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
  };

  const handleStopBatch = (batchId) =>
    runBatchAction(batchId, setStoppingBatchIds, stopBatch, {
      success: {
        type: 'info',
        title: 'Batch Stopped',
        message: 'Active background tasks halted. Generated questions remain preserved in the bank.'
      },
      failureTitle: 'Stop Failed',
      logLabel: 'stop batch'
    });

  const handleRetryBatch = (batchId) =>
    runBatchAction(batchId, setRetryingBatchIds, retryBatchJobs, {
      success: {
        type: 'success',
        title: 'Incomplete Sets Resumed',
        message: 'Incomplete question sets have resumed generation.'
      },
      failureTitle: 'Retry Failed',
      logLabel: 'retry batch jobs'
    });

  const handleCancelAllBatches = async () => {
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
  };

  const handleDeleteBatch = (e, batchId) => {
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
  };

  const handleSaveQuestionToBank = async (question) => {
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
  };

  const handleRestoreQuestion = async (question) => {
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
  };

  return {
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
    confirmModal,
    closeConfirmModal
  };
}
