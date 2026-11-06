import { useState, useEffect, useRef, useCallback } from 'react';
import { fetchBatches, fetchQuestionCounts } from '../services/api';

/**
 * The navbar's live numbers: running batches, questions waiting for review, and whether the
 * backend answers at all. Polls every 4s while batches run, every 30s otherwise, and catches
 * up when the tab becomes visible again.
 *
 * @returns {{ backendStatus: boolean|null, activeBatchCount: number, validatedCount: number,
 *            refreshGlobalCounts: (prefetchedCounts?: object) => void }}
 */
export function useGlobalCounts() {
  // null = still connecting, true = online, false = offline
  const [backendStatus, setBackendStatus] = useState(null);
  const [activeBatchCount, setActiveBatchCount] = useState(0);
  const [validatedCount, setValidatedCount] = useState(0);

  const activeBatchCountRef = useRef(activeBatchCount);
  useEffect(() => {
    activeBatchCountRef.current = activeBatchCount;
  }, [activeBatchCount]);
  const countsAbortRef = useRef(null);

  // Optionally takes counts the caller already fetched so they are not requested a second time.
  const refreshGlobalCounts = useCallback((prefetchedCounts) => {
    countsAbortRef.current?.abort();
    const controller = new AbortController();
    countsAbortRef.current = controller;
    const { signal } = controller;

    // limit: 1 keeps the payload tiny; active_running_batches is counted over the whole table
    fetchBatches({ limit: 1 }, signal)
      .then((data) => {
        setActiveBatchCount(data.active_running_batches || 0);
        setBackendStatus(true);
      })
      .catch((err) => {
        // This poll doubles as the health check, so the navbar recovers and goes offline live
        if (err?.name !== 'AbortError') setBackendStatus(false);
      });

    if (prefetchedCounts && typeof prefetchedCounts === 'object' && 'ai_validated' in prefetchedCounts) {
      Promise.resolve(prefetchedCounts).then((counts) => {
        setValidatedCount(counts.ai_validated || 0);
      });
      return;
    }
    fetchQuestionCounts(signal)
      .then((counts) => {
        setValidatedCount(counts.ai_validated || 0);
      })
      .catch(() => {});
  }, []);

  useEffect(() => {
    refreshGlobalCounts();

    let timer = null;
    let isCancelled = false;

    const scheduleNext = () => {
      if (isCancelled) return;
      // If there are running background batches, poll every 4s; otherwise idle poll at 30s
      const delay = activeBatchCountRef.current > 0 ? 4000 : 30000;
      timer = setTimeout(() => {
        // No point refreshing counts nobody can see; the visibility handler catches up on return
        if (document.visibilityState !== 'hidden') refreshGlobalCounts();
        scheduleNext();
      }, delay);
    };

    scheduleNext();

    const handleVisibilityChange = () => {
      if (document.visibilityState === 'visible') {
        refreshGlobalCounts();
      }
    };
    document.addEventListener('visibilitychange', handleVisibilityChange);

    return () => {
      isCancelled = true;
      if (timer) clearTimeout(timer);
      countsAbortRef.current?.abort();
      document.removeEventListener('visibilitychange', handleVisibilityChange);
    };
  }, [refreshGlobalCounts]);

  return { backendStatus, activeBatchCount, validatedCount, refreshGlobalCounts };
}
