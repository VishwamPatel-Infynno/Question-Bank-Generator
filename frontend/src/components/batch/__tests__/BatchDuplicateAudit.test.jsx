// @vitest-environment jsdom
globalThis.IS_REACT_ACT_ENVIRONMENT = true;

import { act } from 'react';
import { createRoot } from 'react-dom/client';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('../../../services', () => ({
  fetchBatchDuplicateClusters: vi.fn(),
  resolveBatchDuplicates: vi.fn()
}));

import { fetchBatchDuplicateClusters, resolveBatchDuplicates } from '../../../services';
import BatchDuplicateAudit from '../BatchDuplicateAudit';

const report = {
  batch_id: 'b1',
  total_active_questions: 10,
  total_duplicate_questions: 2,
  archived_duplicates_count: 0,
  clusters: [
    {
      cluster_id: 'c1',
      size: 3,
      highest_similarity: 0.91,
      leader_question: { id: 'q1', question_stem: 'Leader stem' },
      duplicates: []
    }
  ]
};

let root;
let container;
const flush = () => act(async () => {});
const buttonByText = (text) =>
  [...document.querySelectorAll('button')].find((b) => b.textContent.includes(text));
const click = (el) => act(() => el.dispatchEvent(new MouseEvent('click', { bubbles: true })));

beforeEach(() => {
  vi.clearAllMocks();
  container = document.createElement('div');
  document.body.appendChild(container);
  root = createRoot(container);
});
afterEach(() => {
  act(() => root.unmount());
  document.body.innerHTML = '';
});

describe('BatchDuplicateAudit', () => {
  it('does nothing until asked, then lists the groups', async () => {
    fetchBatchDuplicateClusters.mockResolvedValue(report);
    act(() => root.render(<BatchDuplicateAudit batchId="b1" />));
    await flush();
    expect(fetchBatchDuplicateClusters).not.toHaveBeenCalled();

    click(buttonByText('Check duplicates'));
    await flush();
    expect(fetchBatchDuplicateClusters).toHaveBeenCalledWith('b1', {}, expect.any(AbortSignal));
    expect(container.textContent).toContain('Group 1: 3 questions, up to 91% similar');
    expect(container.textContent).toContain('Leader stem');
  });

  it('says so when nothing is duplicated', async () => {
    fetchBatchDuplicateClusters.mockResolvedValue({ ...report, clusters: [], total_duplicate_questions: 0 });
    act(() => root.render(<BatchDuplicateAudit batchId="b1" />));
    click(buttonByText('Check duplicates'));
    await flush();
    expect(container.textContent).toContain('No duplicates found');
    expect(buttonByText('Resolve duplicates')).toBeUndefined();
  });

  it('resolves only after confirmation, shows the deficit and refreshes the batch', async () => {
    fetchBatchDuplicateClusters.mockResolvedValue(report);
    resolveBatchDuplicates.mockResolvedValue({
      success: true,
      archived_count: 2,
      remaining_active_questions: 8,
      target_count: 10,
      deficit: 2
    });
    const onResolved = vi.fn();
    const onShowToast = vi.fn();
    act(() => root.render(<BatchDuplicateAudit batchId="b1" onResolved={onResolved} onShowToast={onShowToast} />));
    click(buttonByText('Check duplicates'));
    await flush();

    click(buttonByText('Resolve duplicates'));
    expect(resolveBatchDuplicates).not.toHaveBeenCalled();
    expect(document.querySelector('[role="dialog"]').textContent).toContain('archive the rest');

    click(document.getElementById('btn-confirm-action'));
    await flush();
    expect(resolveBatchDuplicates).toHaveBeenCalledWith('b1', { action: 'archive' });
    expect(onResolved).toHaveBeenCalledWith('b1');
    expect(onShowToast).toHaveBeenCalledWith(expect.objectContaining({ type: 'success' }));
    expect(container.textContent).toContain('2 questions short of the target');
    expect(document.querySelector('[role="dialog"]')).toBeNull();
  });

  it('shows an error when the check fails', async () => {
    vi.spyOn(console, 'error').mockImplementation(() => {});
    fetchBatchDuplicateClusters.mockRejectedValue(new Error('nope'));
    act(() => root.render(<BatchDuplicateAudit batchId="b1" />));
    click(buttonByText('Check duplicates'));
    await flush();
    expect(container.textContent).toContain('nope');
  });
});
