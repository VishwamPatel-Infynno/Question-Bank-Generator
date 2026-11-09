import { useMemo, useRef, useState } from 'react';
import { BATCH_FILTER, BATCH_STATUS, SECTION_CODE_MAP } from '../constants';
import { useKeyboardShortcuts } from './useKeyboardShortcuts';

/**
 * Filter state and derived lists for the batch activity view.
 *
 * @param {Array<object>} batches - All loaded batches
 * @returns {{
 *   scopeFilter: 'all' | 'mini' | 'full',
 *   setScopeFilter: (scope: 'all' | 'mini' | 'full') => void,
 *   statusFilter: string,
 *   setStatusFilter: (status: string) => void,
 *   sectionFilter: string,
 *   setSectionFilter: (section: string) => void,
 *   searchQuery: string,
 *   setSearchQuery: (query: string) => void,
 *   searchInputRef: any,
 *   activeBatchesList: Array<object>,
 *   filteredBatches: Array<object>
 * }} Filter states and derived filtered/active lists.
 */
export function useBatchFilters(batches) {
  const [scopeFilter, setScopeFilter] = useState('all'); // 'all' | 'mini' | 'full'
  const [statusFilter, setStatusFilter] = useState(BATCH_FILTER.ALL);
  const [sectionFilter, setSectionFilter] = useState('all');
  const [searchQuery, setSearchQuery] = useState('');
  const searchInputRef = useRef(null);

  // Focus search input on '/' shortcut
  useKeyboardShortcuts({
    onFocusSearch: () => searchInputRef.current?.focus()
  });

  // Active batches list for the multi-batch monitor
  const activeBatchesList = useMemo(
    () => batches.filter((b) => b.status === BATCH_STATUS.IN_PROGRESS),
    [batches]
  );

  const filteredBatches = useMemo(() => {
    return batches.filter((b) => {
      if (scopeFilter === 'mini' && !(b.total_jobs === 1 || b.target_count === 5)) return false;
      if (scopeFilter === 'full' && !(b.total_jobs > 1 || b.target_count > 5)) return false;
      if (statusFilter !== BATCH_FILTER.ALL && b.status !== statusFilter) return false;
      if (sectionFilter !== 'all') {
        const code = SECTION_CODE_MAP[b.section] || b.section;
        if (code !== sectionFilter && b.section !== sectionFilter) return false;
      }
      if (searchQuery.trim()) {
        const query = searchQuery.toLowerCase();
        const matchTopic = (b.subtopic || '').toLowerCase().includes(query);
        const matchSection = (b.section || '').toLowerCase().includes(query);
        const matchId = b.id.toLowerCase().includes(query);
        if (!matchTopic && !matchSection && !matchId) return false;
      }
      return true;
    });
  }, [batches, scopeFilter, statusFilter, sectionFilter, searchQuery]);

  return {
    scopeFilter,
    setScopeFilter,
    statusFilter,
    setStatusFilter,
    sectionFilter,
    setSectionFilter,
    searchQuery,
    setSearchQuery,
    searchInputRef,
    activeBatchesList,
    filteredBatches
  };
}
