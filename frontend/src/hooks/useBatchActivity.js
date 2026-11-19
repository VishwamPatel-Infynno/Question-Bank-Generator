import { useState, useEffect, useCallback, useRef } from 'react';
import { fetchBatches, fetchBatchDetail } from '../services';
import { BATCH_STATUS } from '../constants';
import { reuseUnchangedBatches } from '../utils/batchHelpers';
import { useBatchFilters } from './useBatchFilters';
import { useBatchMutations } from './useBatchMutations';

/**
 * Batch activity state for BatchActivityView: polling telemetry and accordion/detail caching
 * live here; filtering is `useBatchFilters` and lifecycle actions are `useBatchMutations`.
 *
 * @param {Object} options
 * @param {(toast: { type?: string, title: string, message?: string, action?: any }) => void} [options.onShowToast]
 * @param {() => void} [options.onNavigateToBank]
 * @param {Object} [options.newlyLaunchedBatch]
 * @param {() => void} [options.onClearNewlyLaunchedBatch]
 * @returns {Object} Batch activity state and actions
 */
export function useBatchActivity({
  onShowToast,
  onNavigateToBank,
  newlyLaunchedBatch,
  onClearNewlyLaunchedBatch
} = {}) {
  const [batches, setBatches] = useState(() => (newlyLaunchedBatch?.batch ? [newlyLaunchedBatch.batch] : []));
  const [loading, setLoading] = useState(() => !newlyLaunchedBatch?.batch);
  const [loadError, setLoadError] = useState(null);
  const [refreshing, setRefreshing] = useState(false);
  const [activeCount, setActiveCount] = useState(() => (newlyLaunchedBatch?.batch ? 1 : 0));

  // Multi-expand batch details cache: Set of expanded batch IDs
  const [expandedBatchIds, setExpandedBatchIds] = useState(
    () => (newlyLaunchedBatch?.batch ? new Set([newlyLaunchedBatch.batch.id]) : new Set())
  );
  const [batchDetails, setBatchDetails] = useState(() =>
    newlyLaunchedBatch?.batch
      ? { [newlyLaunchedBatch.batch.id]: { batch: newlyLaunchedBatch.batch, jobs: newlyLaunchedBatch.jobs || [] } }
      : {}
  );
  const [loadingDetails, setLoadingDetails] = useState({});

  // Expanded job within the expanded batches: { [jobId]: boolean }
  const [expandedJobIds, setExpandedJobIds] = useState(() => {
    const firstJobId = newlyLaunchedBatch?.jobs?.[0]?.id;
    return firstJobId ? { [firstJobId]: true } : {};
  });

  // Adjust state when newlyLaunchedBatch changes while mounted (React official pattern:
  // https://react.dev/learn/you-might-not-need-an-effect#adjusting-some-state-when-a-prop-changes)
  const [prevLaunchedBatch, setPrevLaunchedBatch] = useState(newlyLaunchedBatch);
  if (newlyLaunchedBatch && newlyLaunchedBatch !== prevLaunchedBatch) {
    setPrevLaunchedBatch(newlyLaunchedBatch);
    const { batch, jobs = [] } = newlyLaunchedBatch;
    setBatches((prev) => (prev.some((b) => b.id === batch.id) ? prev : [batch, ...prev]));
    setActiveCount((prev) => Math.max(1, prev + 1));
    setExpandedBatchIds((prev) => new Set([...prev, batch.id]));
    setBatchDetails((prev) => ({
      ...prev,
      [batch.id]: { batch, jobs }
    }));
    if (jobs.length > 0) {
      setExpandedJobIds((prev) => ({ ...prev, [jobs[0].id]: true }));
    }
    setLoading(false);
  }

  // Clear parent launch buffer when this view unmounts
  useEffect(() => {
    return () => {
      onClearNewlyLaunchedBatch?.();
    };
  }, [onClearNewlyLaunchedBatch]);

  // Auto-refresh control
  const [autoRefresh, setAutoRefresh] = useState(true);
  const pollTimerRef = useRef(null);
  const fetchInFlightRef = useRef(false);
  const abortRef = useRef(null);
  const lastStatusRef = useRef(new Map());
  const failureCountRef = useRef(0);
  const nextPollAllowedRef = useRef(0);
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
    // A slow response must never overlap with the next poll tick.
    if (fetchInFlightRef.current && isSilent) return;
    fetchInFlightRef.current = true;
    try {
      const controller = new AbortController();
      abortRef.current?.abort();
      abortRef.current = controller;
      const data = await fetchBatches({}, controller.signal);
      const fetchedBatches = data.batches || [];
      setBatches((prev) => reuseUnchangedBatches(prev, fetchedBatches));
      setActiveCount(data.active_running_batches || 0);

      // Auto-expand the running batch if none are expanded yet
      let currentExpanded = Array.from(expandedBatchIdsRef.current);
      if (currentExpanded.length === 0) {
        const runningBatch = fetchedBatches.find((b) => b.status === BATCH_STATUS.IN_PROGRESS);
        if (runningBatch) {
          currentExpanded = [runningBatch.id];
          setExpandedBatchIds(new Set(currentExpanded));
        }
      }

      // Re-fetch details for any expanded batches that are in progress atomically
      const previousStatus = lastStatusRef.current;
      const inProgressIds = currentExpanded.filter((bId) => {
        const matchingBatch = fetchedBatches.find((b) => b.id === bId);
        if (!matchingBatch) return false;
        return (
          matchingBatch.status === BATCH_STATUS.IN_PROGRESS || previousStatus.get(bId) === BATCH_STATUS.IN_PROGRESS
        );
      });
      lastStatusRef.current = new Map(fetchedBatches.map((b) => [b.id, b.status]));

      if (inProgressIds.length > 0) {
        const results = await Promise.allSettled(
          inProgressIds.map((bId) => fetchBatchDetail(bId, controller.signal))
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
      failureCountRef.current = 0;
      nextPollAllowedRef.current = 0;
      setLoadError(null);
    } catch (err) {
      // A newer request superseded this one (or the view unmounted): not a failure
      if (err?.name === 'AbortError') return;
      // Exponential backoff (2.5s doubling, capped at 30s) while the backend is unreachable.
      failureCountRef.current += 1;
      nextPollAllowedRef.current =
        Date.now() + Math.min(30000, 2500 * 2 ** failureCountRef.current);
      console.error('Failed to load batches:', err);
      setLoadError(err?.message || 'Request failed');
      if (!isSilent && onShowToastRef.current) {
        onShowToastRef.current({
          type: 'error',
          title: 'Failed to Refresh',
          message: 'Could not connect to database to fetch batch logs.'
        });
      }
    } finally {
      fetchInFlightRef.current = false;
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
        await performFetchBatches(false);
      }
    }
    init();
    return () => {
      ignore = true;
      abortRef.current?.abort();
      fetchInFlightRef.current = false;
    };
  }, [performFetchBatches]);

  const hasActiveBatches = activeCount > 0 || batches.some((b) => b.status === BATCH_STATUS.IN_PROGRESS);

  // Auto-polling effect (adaptive: 1.5s active / 10s idle, paused if window hidden, immediate on focus)
  useEffect(() => {
    if (!autoRefresh) return;

    const intervalMs = hasActiveBatches ? 1500 : 10000;

    pollTimerRef.current = setInterval(() => {
      if (typeof document !== 'undefined' && document.visibilityState === 'hidden') return;
      if (Date.now() < nextPollAllowedRef.current) return;
      loadBatches(true);
    }, intervalMs);

    const handleVisibilityOrFocus = () => {
      if (typeof document !== 'undefined' && document.visibilityState === 'visible') {
        loadBatches(true);
      }
    };

    document.addEventListener('visibilitychange', handleVisibilityOrFocus);
    window.addEventListener('focus', handleVisibilityOrFocus);

    return () => {
      if (pollTimerRef.current) clearInterval(pollTimerRef.current);
      document.removeEventListener('visibilitychange', handleVisibilityOrFocus);
      window.removeEventListener('focus', handleVisibilityOrFocus);
    };
  }, [autoRefresh, hasActiveBatches, loadBatches]);

  // Handle multi-batch expansion toggle
  const handleToggleExpandBatch = useCallback(
    async (batchId) => {
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
      if (!batchDetails[batchId] || batchDetails[batchId]?.batch?.status === BATCH_STATUS.IN_PROGRESS) {
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
    },
    [batchDetails]
  );

  // Toggle individual job accordion
  const handleToggleJob = useCallback((jobId) => {
    setExpandedJobIds((prev) => ({
      ...prev,
      [jobId]: !prev[jobId]
    }));
  }, []);

  const { filteredBatches, activeBatchesList, ...filters } = useBatchFilters(batches);

  const mutations = useBatchMutations({
    loadBatches,
    setBatches,
    setBatchDetails,
    setExpandedBatchIds,
    onShowToast,
    onNavigateToBank
  });

  return {
    // Data & status
    batches,
    filteredBatches,
    activeBatchesList,
    activeCount,
    hasActiveBatches,
    loading,
    loadError,
    refreshing,
    loadBatches,
    // Filters (scope/status/section/search + their setters, searchInputRef)
    ...filters,
    autoRefresh,
    setAutoRefresh,
    // Expansion & detail caching
    expandedBatchIds,
    batchDetails,
    loadingDetails,
    handleToggleExpandBatch,
    expandedJobIds,
    handleToggleJob,
    // Actions, loading flags and the confirm modal
    ...mutations
  };
}
