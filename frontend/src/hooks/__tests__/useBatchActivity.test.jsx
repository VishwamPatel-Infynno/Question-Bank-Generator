// @vitest-environment jsdom
globalThis.IS_REACT_ACT_ENVIRONMENT = true;

import { act, useEffect } from 'react';
import { createRoot } from 'react-dom/client';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('../../services', () => ({
  fetchBatches: vi.fn(),
  fetchBatchDetail: vi.fn(),
}));
vi.mock('../useBatchMutations', () => ({ useBatchMutations: () => ({}) }));

import { fetchBatches, fetchBatchDetail } from '../../services';
import { useBatchActivity } from '../useBatchActivity';

const flush = () => act(async () => { await new Promise((r) => setTimeout(r, 0)); });

describe('useBatchActivity detail retry', () => {
  let container;
  let root;
  let latest;

  // Stable identity: a new object per render would re-trigger the launched-batch adjustment
  const launched = { batch: { id: 'b1', status: 'in_progress' }, jobs: [] };

  function Probe() {
    const value = useBatchActivity({ newlyLaunchedBatch: launched });
    useEffect(() => {
      latest = value;
    });
    return null;
  }

  beforeEach(() => {
    container = document.createElement('div');
    document.body.appendChild(container);
    root = createRoot(container);
    vi.mocked(fetchBatches).mockReset();
    vi.mocked(fetchBatchDetail).mockReset();
  });

  afterEach(() => {
    act(() => root.unmount());
    container.remove();
  });

  it('retries the detail fetch of a just-completed batch after a failure', async () => {
    const inProgress = { id: 'b1', status: 'in_progress', completed_jobs: 1, updated_at: 't1' };
    const completed = { id: 'b1', status: 'completed', completed_jobs: 2, updated_at: 't2' };
    fetchBatches
      .mockResolvedValueOnce({ batches: [inProgress], active_running_batches: 1 })
      .mockResolvedValue({ batches: [completed], active_running_batches: 0 });
    fetchBatchDetail
      .mockResolvedValueOnce({ batch: inProgress, jobs: [] })
      .mockRejectedValueOnce(new Error('boom'))
      .mockResolvedValue({ batch: completed, jobs: [] });

    await act(async () => { root.render(<Probe />); });
    await flush();
    expect(fetchBatchDetail).toHaveBeenCalledTimes(1);

    await act(async () => { await latest.loadBatches(true); }); // detail fetch fails
    expect(fetchBatchDetail).toHaveBeenCalledTimes(2);
    expect(latest.batchDetails.b1.batch.status).toBe('in_progress');

    await act(async () => { await latest.loadBatches(true); }); // must retry
    expect(fetchBatchDetail).toHaveBeenCalledTimes(3);
    expect(latest.batchDetails.b1.batch.status).toBe('completed');
  });
});
