// @vitest-environment jsdom
globalThis.IS_REACT_ACT_ENVIRONMENT = true;

import { act, useEffect } from 'react';
import { createRoot } from 'react-dom/client';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('../../services', () => ({ overrideQuestionDuplicate: vi.fn() }));

import { overrideQuestionDuplicate } from '../../services';
import { useDuplicateOverride } from '../useDuplicateOverride';

let api;
function Harness(props) {
  const result = useDuplicateOverride(props);
  useEffect(() => {
    api = result;
  });
  return null;
}

let root;
beforeEach(() => {
  vi.clearAllMocks();
  vi.spyOn(console, 'error').mockImplementation(() => {});
  root = createRoot(document.createElement('div'));
});
afterEach(() => {
  act(() => root.unmount());
  vi.restoreAllMocks();
});

const mount = (props) => act(() => root.render(<Harness {...props} />));

describe('useDuplicateOverride', () => {
  it('opens and closes the compare dialog', () => {
    mount({});
    expect(api.compareQuestion).toBeNull();
    const q = { id: 'q1' };
    act(() => api.openCompare(q));
    expect(api.compareQuestion).toBe(q);
    act(() => api.closeCompare());
    expect(api.compareQuestion).toBeNull();
  });

  it('overrides, hands the returned question to onUpdated, toasts and closes the dialog', async () => {
    const saved = { id: 'q1', status: 'in_bank', is_duplicate_override: true };
    overrideQuestionDuplicate.mockResolvedValue({ success: true, question: saved });
    const onUpdated = vi.fn();
    const onShowToast = vi.fn();
    mount({ onUpdated, onShowToast });
    act(() => api.openCompare({ id: 'q1' }));

    await act(async () => {
      await api.handleOverride({ id: 'q1' });
    });

    expect(overrideQuestionDuplicate).toHaveBeenCalledWith('q1');
    expect(onUpdated).toHaveBeenCalledWith(saved);
    expect(onShowToast).toHaveBeenCalledWith(expect.objectContaining({ type: 'success' }));
    expect(api.compareQuestion).toBeNull();
    expect(api.isOverriding).toBe(false);
  });

  it('on error toasts, does not update, and keeps the dialog open', async () => {
    overrideQuestionDuplicate.mockRejectedValue(new Error('boom'));
    const onUpdated = vi.fn();
    const onShowToast = vi.fn();
    mount({ onUpdated, onShowToast });
    act(() => api.openCompare({ id: 'q1' }));

    await act(async () => {
      await api.handleOverride({ id: 'q1' });
    });

    expect(onUpdated).not.toHaveBeenCalled();
    expect(onShowToast).toHaveBeenCalledWith(
      expect.objectContaining({ type: 'error', message: 'boom' })
    );
    expect(api.compareQuestion).toEqual({ id: 'q1' });
    expect(api.isOverriding).toBe(false);
  });

  it('ignores a second click while an override is running', async () => {
    let resolve;
    overrideQuestionDuplicate.mockReturnValue(new Promise((r) => (resolve = r)));
    mount({});
    let first;
    act(() => {
      first = api.handleOverride({ id: 'q1' });
    });
    expect(api.isOverriding).toBe(true);
    await act(async () => {
      await api.handleOverride({ id: 'q1' });
    });
    expect(overrideQuestionDuplicate).toHaveBeenCalledTimes(1);
    await act(async () => {
      resolve({ question: { id: 'q1' } });
      await first;
    });
    expect(api.isOverriding).toBe(false);
  });

  it('keeps handleOverride stable across renders while using the latest callbacks', async () => {
    overrideQuestionDuplicate.mockResolvedValue({ question: { id: 'q1' } });
    const first = vi.fn();
    const second = vi.fn();
    mount({ onUpdated: first });
    const handler = api.handleOverride;
    mount({ onUpdated: second });
    expect(api.handleOverride).toBe(handler);
    await act(async () => {
      await api.handleOverride({ id: 'q1' });
    });
    expect(first).not.toHaveBeenCalled();
    expect(second).toHaveBeenCalled();
  });
});
