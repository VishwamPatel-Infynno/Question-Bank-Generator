import { useState, useMemo, useCallback } from 'react';

/**
 * usePagination - Reusable pagination and item slicing hook.
 *
 * Encapsulates page index, page size, total pages calculation, boundary clamping,
 * item slicing, and automatic page resetting when filter or search dependencies change.
 *
 * Supports both client-side slicing (default) and server-driven mode (when totalCount is provided).
 *
 * @param {Object} options
 * @param {Array} [options.items=[]] - Current items (full list for client mode, page slice for server mode).
 * @param {number} [options.initialPageSize=15] - Initial items per page (-1 for showing all).
 * @param {Array} [options.resetDeps=[]] - Array of filter/search values that trigger a reset to page 1.
 * @param {number|null} [options.totalCount=null] - When provided, enables server-driven pagination mode.
 * @param {(page: number) => void} [options.onPageChange] - Callback invoked when page changes in server mode.
 * @param {(size: number) => void} [options.onPageSizeChange] - Callback invoked when page size changes.
 * @returns {Object} Pagination state, sliced items, and controls.
 */
export function usePagination({
  items = [],
  initialPageSize = 15,
  resetDeps = [],
  totalCount = null,
  onPageChange = null,
  onPageSizeChange = null
} = {}) {
  const [pageSize, setPageSizeState] = useState(initialPageSize);
  // The page is stored with the filters it belongs to, so a filter change is page 1 in the
  // same render (no extra render at a stale page)
  const [pageState, setPageState] = useState({ page: 1, deps: resetDeps });
  const depsChanged =
    resetDeps.length !== pageState.deps.length ||
    resetDeps.some((dep, i) => !Object.is(dep, pageState.deps[i]));
  const currentPage = depsChanged ? 1 : pageState.page;

  const setPageSize = useCallback(
    (newSize) => {
      setPageSizeState(newSize);
      onPageSizeChange?.(newSize);
    },
    [onPageSizeChange]
  );

  const isServerDriven = totalCount !== null && totalCount !== undefined;
  const totalItems = isServerDriven ? totalCount : items?.length || 0;
  const totalPages =
    pageSize === -1
      ? 1
      : Math.max(1, Math.ceil(totalItems / (pageSize || 1)));

  const safeCurrentPage = Math.min(Math.max(1, currentPage), totalPages);

  const setCurrentPage = useCallback(
    (page) => {
      const nextRaw = typeof page === 'function' ? page(currentPage) : page;
      const nextSafe = Math.min(Math.max(1, nextRaw), totalPages);
      setPageState({ page: nextSafe, deps: resetDeps });
      onPageChange?.(nextSafe);
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [currentPage, totalPages, ...resetDeps, onPageChange]
  );

  const paginatedItems = useMemo(() => {
    if (!Array.isArray(items)) return [];
    if (isServerDriven) return items;
    if (pageSize === -1) return items;
    const start = (safeCurrentPage - 1) * pageSize;
    return items.slice(start, start + pageSize);
  }, [items, isServerDriven, safeCurrentPage, pageSize]);

  const resetPage = useCallback(() => setCurrentPage(1), [setCurrentPage]);

  return {
    currentPage,
    setCurrentPage,
    pageSize,
    setPageSize,
    totalPages,
    safeCurrentPage,
    paginatedItems,
    totalItems,
    resetPage,
    isServerDriven
  };
}

