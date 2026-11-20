// @vitest-environment jsdom
globalThis.IS_REACT_ACT_ENVIRONMENT = true;

import { act, useEffect } from 'react';
import { createRoot } from 'react-dom/client';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { usePagination } from '../usePagination';

describe('usePagination Hook', () => {
  let container;
  let root;

  beforeEach(() => {
    container = document.createElement('div');
    document.body.appendChild(container);
    root = createRoot(container);
  });

  afterEach(() => {
    act(() => {
      root.unmount();
    });
    container.remove();
  });

  it('handles client-side pagination with item slicing', () => {
    let hookResult;
    function TestComponent() {
      const res = usePagination({
        items: [1, 2, 3, 4, 5, 6, 7],
        initialPageSize: 3
      });
      useEffect(() => {
        hookResult = res;
      });
      return null;
    }

    act(() => {
      root.render(<TestComponent />);
    });

    expect(hookResult.totalPages).toBe(3);
    expect(hookResult.totalItems).toBe(7);
    expect(hookResult.safeCurrentPage).toBe(1);
    expect(hookResult.paginatedItems).toEqual([1, 2, 3]);

    act(() => {
      hookResult.setCurrentPage(2);
    });

    expect(hookResult.safeCurrentPage).toBe(2);
    expect(hookResult.paginatedItems).toEqual([4, 5, 6]);
  });

  it('handles server-driven mode without client-side item slicing', () => {
    let hookResult;
    const onPageChange = vi.fn();
    const serverPageSlice = [{ id: 'q10' }, { id: 'q11' }];

    function TestComponent() {
      const res = usePagination({
        items: serverPageSlice,
        initialPageSize: 20,
        totalCount: 105,
        onPageChange
      });
      useEffect(() => {
        hookResult = res;
      });
      return null;
    }

    act(() => {
      root.render(<TestComponent />);
    });

    expect(hookResult.isServerDriven).toBe(true);
    expect(hookResult.totalItems).toBe(105);
    expect(hookResult.totalPages).toBe(6); // ceil(105 / 20)
    expect(hookResult.paginatedItems).toBe(serverPageSlice);

    act(() => {
      hookResult.setCurrentPage(3);
    });

    expect(onPageChange).toHaveBeenCalledWith(3);
    expect(hookResult.safeCurrentPage).toBe(3);
  });
});
