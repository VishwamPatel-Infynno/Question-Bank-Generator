import { useState, useEffect, useCallback, useMemo } from 'react';
import { useCopyToClipboard } from './useCopyToClipboard';
import { useRequestGuard } from './useRequestGuard';
import { useDebouncedValue } from './useDebouncedValue';
import { formatQuestionForCopy } from '../utils/questionHelpers';
import { fetchQuestions, deleteQuestion } from '../services/api';
import { DIFFICULTY, QUESTION_STATUS, normalizeDifficulty } from '../constants';

export function useQuestionBank() {
  const [rawQuestions, setRawQuestions] = useState([]);
  const [repoStats, setRepoStats] = useState({ total_tokens: 0, total_cost_usd: 0 });
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState(null);
  const [sectionFilter, setSectionFilter] = useState('');
  const [diffFilter, setDiffFilter] = useState('');
  const [searchQuery, setSearchQuery] = useState('');
  const debouncedSearch = useDebouncedValue(searchQuery);
  const [sortBy, setSortBy] = useState('newest'); // 'newest' | 'score_desc' | 'score_asc' | 'difficulty'
  const { copiedKey: copiedId, copy } = useCopyToClipboard();
  const [refreshCount, setRefreshCount] = useState(0);
  const guard = useRequestGuard();

  // Fetch questions with inflight cancellation via AbortController
  useEffect(() => {
    const request = guard.begin();

    // Trigger reload when dependencies or refreshCount change
    fetchQuestions(
      {
        section: sectionFilter || undefined,
        difficulty: diffFilter || undefined,
        search: debouncedSearch || undefined,
        status: QUESTION_STATUS.IN_BANK,
        sort_by: sortBy || 'newest',
        slim: true
      },
      request.signal
    )
      .then((data) => {
        if (request.isCurrent()) {
          setLoadError(null);
          setRawQuestions(data.questions || []);
          setRepoStats({
            total_tokens: data.total_tokens || 0,
            total_cost_usd: data.total_cost_usd || 0,
            total_count: data.total_count || 0,
            bank_total_count: data.bank_total_count || 0
          });
          setLoading(false);
        }
      })
      .catch((err) => {
        if (err.name === 'AbortError') return;
        console.error('Failed to load question bank:', err);
        if (request.isCurrent()) {
          setLoadError(err.message || 'Request failed');
          setLoading(false);
        }
      });
  }, [guard, sectionFilter, diffFilter, debouncedSearch, sortBy, refreshCount]);

  const loadQuestions = useCallback(() => {
    setLoadError(null);
    setLoading(true);
    setRefreshCount(c => c + 1);
  }, []);

  const handleDelete = useCallback(
    async (id) => {
      await deleteQuestion(id);
      loadQuestions();
    },
    [loadQuestions]
  );

  const handleCopy = useCallback((q, e) => {
    if (e) e.stopPropagation();
    copy(formatQuestionForCopy(q), q.id);
  }, [copy]);

  const handleUpdate = useCallback((updatedQuestion) => {
    setRawQuestions((prev) =>
      prev.map((q) => (q.id === updatedQuestion.id ? { ...q, ...updatedQuestion } : q))
    );
  }, []);

  // Multi-criteria sorting executed in-memory with useMemo
  const questions = useMemo(() => {
    const list = [...rawQuestions];
    if (sortBy === 'score_desc') {
      return list.sort((a, b) => (b.final_score || 0) - (a.final_score || 0));
    }
    if (sortBy === 'score_asc') {
      return list.sort((a, b) => (a.final_score || 0) - (b.final_score || 0));
    }
    if (sortBy === 'difficulty') {
      const order = { [DIFFICULTY.LOW]: 1, [DIFFICULTY.MEDIUM]: 2, [DIFFICULTY.HIGH]: 3 };
      return list.sort(
        (a, b) => (order[normalizeDifficulty(a.difficulty)] || 0) - (order[normalizeDifficulty(b.difficulty)] || 0)
      );
    }
    // Default 'newest'
    return list.sort((a, b) => new Date(b.created_at || 0) - new Date(a.created_at || 0));
  }, [rawQuestions, sortBy]);

  const avgScore = useMemo(() => {
    if (questions.length === 0) return 0;
    return Math.round(questions.reduce((acc, q) => acc + (q.final_score || 0), 0) / questions.length);
  }, [questions]);

  return {
    questions,
    rawQuestions,
    repoStats,
    loading,
    loadError,
    sectionFilter,
    setSectionFilter,
    diffFilter,
    setDiffFilter,
    searchQuery,
    setSearchQuery,
    sortBy,
    setSortBy,
    copiedId,
    loadQuestions,
    handleDelete,
    handleCopy,
    handleUpdate,
    avgScore
  };
}
