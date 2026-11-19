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

  it('prunes stale selectedIds when questions array changes (filter change / reload)', () => {
    const rawSelectedIds = ['q1', 'q2', 'q3', 'stale_id'];
    const currentQuestions = [{ id: 'q1' }, { id: 'q2' }, { id: 'q4' }];

    const loaded = new Set(currentQuestions.map((q) => q.id));
    const selectedIds = rawSelectedIds.filter((id) => loaded.has(id));

    expect(selectedIds).toEqual(['q1', 'q2']);
    expect(selectedIds).not.toContain('stale_id');
    expect(selectedIds).not.toContain('q3');
  });
});
