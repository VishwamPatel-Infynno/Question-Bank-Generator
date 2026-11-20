import { useState, useCallback, useRef } from 'react';
import { fetchBatchDuplicateClusters, resolveBatchDuplicates } from '../services';
import { useRequestGuard } from './useRequestGuard';

/**
 * On-demand duplicate audit for one batch: "Check" lists groups of near-identical questions and
 * "Resolve" keeps the best of each group and archives the rest. Nothing runs on its own (never on
 * a poll), and overlapping checks are guarded so only the newest answer is shown.
 *
 * @param {Object} options
 * @param {string} options.batchId
 * @param {(toast: { type?: string, title: string, message?: string }) => void} [options.onShowToast]
 * @param {(batchId: string) => void | Promise<void>} [options.onResolved] - Called after a successful resolve (refresh the batch).
 * @returns {{
 *   report: Object|null,
 *   resolution: Object|null,
 *   error: string|null,
 *   isChecking: boolean,
 *   isResolving: boolean,
 *   check: () => Promise<void>,
 *   resolve: () => Promise<boolean>
 * }}
 */
export function useBatchDuplicateAudit({ batchId, onShowToast, onResolved }) {
  const [report, setReport] = useState(null);
  const [resolution, setResolution] = useState(null);
  const [error, setError] = useState(null);
  const [isChecking, setIsChecking] = useState(false);
  const [isResolving, setIsResolving] = useState(false);
  const guard = useRequestGuard();
  const resolvingRef = useRef(false);

  const check = useCallback(async () => {
    const req = guard.begin();
    setIsChecking(true);
    setError(null);
    setResolution(null);
    try {
      const res = await fetchBatchDuplicateClusters(batchId, {}, req.signal);
      if (!req.isCurrent()) return;
      setReport(res);
    } catch (err) {
      if (err?.name === 'AbortError' || !req.isCurrent()) return;
      console.error('Failed to check batch duplicates:', err);
      setError(err?.message || 'Could not check this batch for duplicates.');
    } finally {
      if (req.isCurrent()) setIsChecking(false);
    }
  }, [guard, batchId]);

  const resolve = useCallback(async () => {
    if (resolvingRef.current) return false;
    resolvingRef.current = true;
    setIsResolving(true);
    try {
      const res = await resolveBatchDuplicates(batchId, { action: 'archive' });
      setResolution(res);
      setReport(null);
      const archived = res?.archived_count ?? 0;
      const deficit = res?.deficit ?? 0;
      onShowToast?.({
        type: 'success',
        title: 'Duplicates Archived',
        message:
          `${archived} duplicate question${archived === 1 ? '' : 's'} archived.` +
          (deficit > 0 ? ` This batch is now ${deficit} question${deficit === 1 ? '' : 's'} short of its target.` : '')
      });
      await onResolved?.(batchId);
      return true;
    } catch (err) {
      console.error('Failed to resolve batch duplicates:', err);
      onShowToast?.({
        type: 'error',
        title: 'Could Not Resolve Duplicates',
        message: err?.message || 'Duplicates could not be archived.'
      });
      return false;
    } finally {
      resolvingRef.current = false;
      setIsResolving(false);
    }
  }, [batchId, onShowToast, onResolved]);

  return { report, resolution, error, isChecking, isResolving, check, resolve };
}
