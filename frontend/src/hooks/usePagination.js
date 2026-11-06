import { useState, useMemo, useCallback } from 'react';

/**
 * usePagination - Reusable pagination and item slicing hook.
 *
 * Encapsulates page index, page size, total pages calculation, boundary clamping,
 * item slicing, and automatic page resetting when filter or search dependencies change.
 *
 * @param {Object} options
 * @param {Array} [options.items=[]] - Full list of items to paginate.
 * @param {number} [options.initialPageSize=10] - Initial items per page (-1 for showing all).
 * @param {Array} [options.resetDeps=[]] - Array of filter/search values that trigger a reset to page 1.
 * @returns {Object} Pagination state, sliced items, and controls.
 */
export function usePagination({
  items = [],
  initialPageSize = 10,
  resetDeps = []
} = {}) {
  const [pageSize, setPageSize] = useState(initialPageSize);
  // The page is stored with the filters it belongs to, so a filter change is page 1 in the
  // same render (no extra render at a stale page)
  const [pageState, setPageState] = useState({ page: 1, deps: resetDeps });
  const depsChanged =
    resetDeps.length !== pageState.deps.length ||
    resetDeps.some((dep, i) => !Object.is(dep, pageState.deps[i]));
  const currentPage = depsChanged ? 1 : pageState.page;
  const setCurrentPage = useCallback(
    (page) => setPageState({ page: typeof page === 'function' ? page(currentPage) : page, deps: resetDeps }),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [currentPage, ...resetDeps]
  );

  const totalItems = items?.length || 0;
  const totalPages =
    pageSize === -1
      ? 1
      : Math.max(1, Math.ceil(totalItems / (pageSize || 1)));

  const safeCurrentPage = Math.min(Math.max(1, currentPage), totalPages);

  const paginatedItems = useMemo(() => {
    if (!Array.isArray(items)) return [];
    if (pageSize === -1) return items;
    const start = (safeCurrentPage - 1) * pageSize;
    return items.slice(start, start + pageSize);
  }, [items, safeCurrentPage, pageSize]);

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
    resetPage
  };
}

