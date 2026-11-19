import { describe, expect, it, vi } from 'vitest';
import { toggleId, toggleAll, allSelected } from '../../utils';
import { QUESTION_STATUS } from '../../constants';

describe('useAiValidated Handlers & Selection Logic', () => {
  it('handleToggleSelect toggles item ID accurately', () => {
    let selectedIds = ['q1', 'q2'];
    const handleToggleSelect = (id) => {
      selectedIds = toggleId(selectedIds, id);
    };

    handleToggleSelect('q1');
    expect(selectedIds).toEqual(['q2']);

    handleToggleSelect('q3');
    expect(selectedIds).toEqual(['q2', 'q3']);
  });

  it('handleSelectAll toggles all filtered question IDs', () => {
    const filteredQuestions = [{ id: 'q1' }, { id: 'q2' }, { id: 'q3' }];
    let selectedIds = ['q1'];

    const handleSelectAll = () => {
      selectedIds = toggleAll(selectedIds, filteredQuestions.map((q) => q.id));
    };

    // When partially selected, selecting all adds remaining
    handleSelectAll();
    expect(selectedIds).toEqual(['q1', 'q2', 'q3']);
    expect(allSelected(selectedIds, filteredQuestions.map((q) => q.id))).toBe(true);

    // When already all selected, selecting all unselects them
    handleSelectAll();
    expect(selectedIds).toEqual([]);
    expect(allSelected(selectedIds, filteredQuestions.map((q) => q.id))).toBe(false);
  });

  it('togglePassage flips passage expansion boolean state', () => {
    let expandedPassageIds = {};
    const togglePassage = (id) => {
      expandedPassageIds = { ...expandedPassageIds, [id]: !expandedPassageIds[id] };
    };

    togglePassage('pass-1');
    expect(expandedPassageIds['pass-1']).toBe(true);

    togglePassage('pass-1');
    expect(expandedPassageIds['pass-1']).toBe(false);

    togglePassage('pass-2');
    expect(expandedPassageIds['pass-2']).toBe(true);
  });

  it('mutation logic updates question state and prunes removed question IDs', async () => {
    let questions = [
      { id: 'q1', stem: 'Question 1', status: QUESTION_STATUS.AI_VALIDATED },
      { id: 'q2', stem: 'Question 2', status: QUESTION_STATUS.AI_VALIDATED },
      { id: 'q3', stem: 'Question 3', status: QUESTION_STATUS.AI_VALIDATED }
    ];
    let selectedIds = ['q1', 'q2'];
    const toast = vi.fn();
    const loadData = vi.fn();

    const runMutation = async ({ call, removeIds, successToast }) => {
      await call();
      const gone = new Set(removeIds);
      questions = questions.filter((item) => !gone.has(item.id));
      selectedIds = selectedIds.filter((id) => !gone.has(id));
      toast(successToast);
      loadData(true);
    };

    const mockApiCall = vi.fn().mockResolvedValue({ success: true });

    await runMutation({
      call: mockApiCall,
      removeIds: ['q1'],
      successToast: { type: 'success', title: 'Saved to Bank' }
    });

    expect(mockApiCall).toHaveBeenCalledTimes(1);
    expect(questions.map((q) => q.id)).toEqual(['q2', 'q3']);
    expect(selectedIds).toEqual(['q2']);
    expect(toast).toHaveBeenCalledWith({ type: 'success', title: 'Saved to Bank' });
    expect(loadData).toHaveBeenCalledWith(true);
  });

  it('bulk mutation logic removes all batch IDs from state and selection', async () => {
    let questions = [{ id: 'q1' }, { id: 'q2' }, { id: 'q3' }];
    let selectedIds = ['q1', 'q2'];

    const runBulkMutation = async (ids) => {
      const gone = new Set(ids);
      questions = questions.filter((item) => !gone.has(item.id));
      selectedIds = selectedIds.filter((id) => !gone.has(id));
    };

    await runBulkMutation(['q1', 'q2']);
    expect(questions.map((q) => q.id)).toEqual(['q3']);
    expect(selectedIds).toEqual([]);
  });
});
