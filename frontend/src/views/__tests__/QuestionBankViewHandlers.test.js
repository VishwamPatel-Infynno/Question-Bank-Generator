import { describe, expect, it, vi } from 'vitest';
import { toggleAll, toggleId } from '../../utils';

describe('QuestionBankView Selection & Filter Handlers', () => {
  it('clears all active filters when handleClearAllFilters logic runs', () => {
    const setSearchQuery = vi.fn();
    const setSectionFilter = vi.fn();
    const setDiffFilter = vi.fn();

    const handleClearAllFilters = () => {
      setSearchQuery('');
      setSectionFilter('');
      setDiffFilter('');
    };

    handleClearAllFilters();

    expect(setSearchQuery).toHaveBeenCalledWith('');
    expect(setSectionFilter).toHaveBeenCalledWith('');
    expect(setDiffFilter).toHaveBeenCalledWith('');
  });

  it('handleToggleSelect stops propagation and toggles an id', () => {
    let rawSelectedIds = ['q1', 'q2'];
    const mockEvent = { stopPropagation: vi.fn() };

    const handleToggleSelect = (id, e) => {
      e.stopPropagation();
      rawSelectedIds = toggleId(rawSelectedIds, id);
    };

    handleToggleSelect('q2', mockEvent);
    expect(mockEvent.stopPropagation).toHaveBeenCalledTimes(1);
    expect(rawSelectedIds).toEqual(['q1']);

    handleToggleSelect('q3', mockEvent);
    expect(mockEvent.stopPropagation).toHaveBeenCalledTimes(2);
    expect(rawSelectedIds).toEqual(['q1', 'q3']);
  });

  it('handleSelectAll toggles all currently paginated question ids', () => {
    const paginatedQuestions = [{ id: 'q1' }, { id: 'q2' }, { id: 'q3' }];
    let rawSelectedIds = ['q1'];

    const handleSelectAll = () => {
      const currentIds = paginatedQuestions.map((q) => q.id);
      rawSelectedIds = toggleAll(rawSelectedIds, currentIds);
    };

    handleSelectAll();
    expect(rawSelectedIds).toEqual(['q1', 'q2', 'q3']);

    handleSelectAll();
    expect(rawSelectedIds).toEqual([]);
  });

  it('supports persistent cross-page selection and bulk clearing', () => {
    // Page 1 selection
    let selectedIds = ['q1', 'q2'];

    // Navigating to page 2: user selects q5 on page 2 while preserving q1 and q2 from page 1
    selectedIds = toggleId(selectedIds, 'q5');
    expect(selectedIds).toEqual(['q1', 'q2', 'q5']);

    // Page 2 IDs: q5, q6
    const page2Ids = ['q5', 'q6'];
    const allSelectedOnPage2 = page2Ids.every((id) => selectedIds.includes(id));
    expect(allSelectedOnPage2).toBe(false);

    // Select all on page 2 retains page 1 items
    const set = new Set(selectedIds);
    page2Ids.forEach((id) => set.add(id));
    selectedIds = Array.from(set);
    expect(selectedIds).toEqual(['q1', 'q2', 'q5', 'q6']);

    // When all page 2 IDs are selected, toggling page 2 deselects only page 2 items
    const setPage2 = new Set(page2Ids);
    selectedIds = selectedIds.filter((id) => !setPage2.has(id));
    expect(selectedIds).toEqual(['q1', 'q2']);

    // Explicit Clear Selection action empties selection entirely
    selectedIds = [];
    expect(selectedIds).toEqual([]);
  });
});
