// @vitest-environment jsdom
globalThis.IS_REACT_ACT_ENVIRONMENT = true;

import { createElement, act, useEffect } from 'react';
import { createRoot } from 'react-dom/client';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { toggleId, toggleAll, allSelected } from '../../utils';
import { QUESTION_STATUS } from '../../constants';

vi.mock('../../services', () => ({
  fetchQuestions: vi.fn(),
  fetchQuestionCounts: vi.fn(),
  updateQuestionStatus: vi.fn(),
  batchUpdateQuestionStatus: vi.fn(),
  purgeQuestion: vi.fn(),
  purgeQuestionsBatch: vi.fn(),
  overrideQuestionDuplicate: vi.fn()
}));

import * as services from '../../services';
import { useAiValidated } from '../useAiValidated';

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

describe('useAiValidated active card and shortcuts', () => {
  const dup = (over = {}) => ({
    is_duplicate: true,
    similarity_score: 0.9,
    matched_question_stem: 'orig',
    is_overridden: false,
    ...over
  });
  let server;
  let api;
  let root;
  let onShowToast;

  function Harness(props) {
    const result = useAiValidated(props);
    useEffect(() => {
      api = result;
    });
    return null;
  }

  const press = (key) =>
    act(() => {
      window.dispatchEvent(new KeyboardEvent('keydown', { key, bubbles: true, cancelable: true }));
    });
  const flush = () => act(async () => {});
  const ids = () => api.filteredQuestions.map((q) => q.id);

  const mount = async () => {
    onShowToast = vi.fn();
    await act(async () => {
      root.render(createElement(Harness, { onShowToast }));
    });
    await flush();
  };

  beforeEach(() => {
    vi.clearAllMocks();
    vi.spyOn(console, 'error').mockImplementation(() => {});
    server = [
      { id: 'q1', question_stem: 'one', final_score: 90, status: 'ai_validated' },
      { id: 'q2', question_stem: 'two', final_score: 91, status: 'ai_validated' },
      { id: 'q3', question_stem: 'three', final_score: 92, status: 'ai_validated' }
    ];
    services.fetchQuestions.mockImplementation(async () => ({
      questions: server.map((q) => ({ ...q })),
      total_count: server.length
    }));
    services.fetchQuestionCounts.mockResolvedValue({ ai_validated: 3 });
    services.updateQuestionStatus.mockImplementation(async (id) => {
      server = server.filter((q) => q.id !== id);
      return { success: true };
    });
    services.purgeQuestion.mockImplementation(async (id) => {
      server = server.filter((q) => q.id !== id);
      return { success: true };
    });
    root = createRoot(document.createElement('div'));
  });

  afterEach(() => {
    act(() => root.unmount());
    vi.restoreAllMocks();
  });

  it('defaults the active card to the first visible one and follows handleActivate', async () => {
    await mount();
    expect(api.activeId).toBe('q1');
    act(() => api.handleActivate('q2'));
    expect(api.activeId).toBe('q2');
    act(() => api.handleActivate('gone'));
    expect(api.activeId).toBe('q1');
  });

  it('A saves the active card to the bank and moves the highlight to the next card', async () => {
    await mount();
    act(() => api.handleActivate('q2'));
    press('a');
    await flush();
    await flush();
    expect(services.updateQuestionStatus).toHaveBeenCalledWith('q2', QUESTION_STATUS.IN_BANK);
    expect(ids()).toEqual(['q1', 'q3']);
    expect(api.activeId).toBe('q3');
  });

  it('after removing the last card the highlight moves to the previous one', async () => {
    await mount();
    act(() => api.handleActivate('q3'));
    press('a');
    await flush();
    await flush();
    expect(api.activeId).toBe('q2');
  });

  it('A on a hard duplicate opens the comparison instead of approving', async () => {
    server[0].duplicate_info = dup();
    await mount();
    press('a');
    await flush();
    expect(services.updateQuestionStatus).not.toHaveBeenCalled();
    expect(api.compareQuestion?.id).toBe('q1');
  });

  it('A still approves an overridden duplicate and a merely similar question', async () => {
    server[0].duplicate_info = dup({ is_overridden: true });
    server[1].duplicate_info = dup({ is_duplicate: false, similarity_score: 0.65 });
    await mount();
    press('a');
    await flush();
    await flush();
    expect(services.updateQuestionStatus).toHaveBeenCalledWith('q1', QUESTION_STATUS.IN_BANK);
    press('a');
    await flush();
    await flush();
    expect(services.updateQuestionStatus).toHaveBeenCalledWith('q2', QUESTION_STATUS.IN_BANK);
    expect(api.compareQuestion).toBeNull();
  });

  it('D asks for confirmation first and only purges after the confirm action', async () => {
    await mount();
    press('d');
    await flush();
    expect(services.purgeQuestion).not.toHaveBeenCalled();
    expect(api.confirmModal.isOpen).toBe(true);
    expect(api.confirmModal.title).toBe('Discard Question');

    await act(async () => {
      await api.confirmModal.onConfirm();
    });
    await flush();
    expect(services.purgeQuestion).toHaveBeenCalledWith('q1');
    expect(ids()).toEqual(['q2', 'q3']);
    expect(api.activeId).toBe('q2');
  });

  it('overriding a duplicate removes it from the queue and toasts once', async () => {
    server[0].duplicate_info = dup();
    services.overrideQuestionDuplicate.mockImplementation(async (id) => {
      server = server.filter((q) => q.id !== id);
      return { success: true, question: { id, status: QUESTION_STATUS.IN_BANK, is_duplicate_override: true } };
    });
    await mount();
    await act(async () => {
      await api.handleOverride(api.filteredQuestions[0]);
    });
    await flush();
    expect(services.overrideQuestionDuplicate).toHaveBeenCalledWith('q1');
    expect(ids()).toEqual(['q2', 'q3']);
    expect(onShowToast).toHaveBeenCalledTimes(1);
    expect(onShowToast).toHaveBeenCalledWith(expect.objectContaining({ type: 'success' }));
  });
});
