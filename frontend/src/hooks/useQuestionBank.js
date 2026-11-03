import { useState, useEffect, useCallback, useMemo } from 'react';
import { fetchQuestions, deleteQuestion } from '../services/api';

export function useQuestionBank() {
  const [rawQuestions, setRawQuestions] = useState([]);
  const [repoStats, setRepoStats] = useState({ total_tokens: 0, total_cost_usd: 0 });
  const [loading, setLoading] = useState(true);
  const [sectionFilter, setSectionFilter] = useState('');
  const [diffFilter, setDiffFilter] = useState('');
  const [statusFilter, setStatusFilter] = useState('in_bank');
  const [searchQuery, setSearchQuery] = useState('');
  const [debouncedSearch, setDebouncedSearch] = useState('');
  const [sortBy, setSortBy] = useState('newest'); // 'newest' | 'score_desc' | 'score_asc' | 'difficulty'
  const [copiedId, setCopiedId] = useState(null);
  // Debounce search query by 250ms
  useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedSearch(searchQuery);
    }, 250);
    return () => clearTimeout(handler);
  }, [searchQuery]);

  const [refreshCount, setRefreshCount] = useState(0);

  // Fetch questions with inflight cancellation via AbortController
  useEffect(() => {
    let isCancelled = false;
    const controller = new AbortController();

    // Trigger reload when dependencies or refreshCount change
    fetchQuestions(
      {
        section: sectionFilter || undefined,
        difficulty: diffFilter || undefined,
        search: debouncedSearch || undefined,
        status: statusFilter || 'in_bank',
        sort_by: sortBy || 'newest',
        slim: true
      },
      controller.signal
    )
      .then((data) => {
        if (!isCancelled) {
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
        if (!isCancelled) setLoading(false);
      });

    return () => {
      isCancelled = true;
      controller.abort();
    };
  }, [sectionFilter, diffFilter, statusFilter, debouncedSearch, sortBy, refreshCount]);

  const loadQuestions = useCallback(() => {
    setLoading(true);
    setRefreshCount(c => c + 1);
  }, []);

  const handleDelete = useCallback(
    async (id, e) => {
      if (e) e.stopPropagation();
      await deleteQuestion(id);
      await loadQuestions();
    },
    [loadQuestions]
  );

  const handleCopy = useCallback((q, e) => {
    if (e) e.stopPropagation();
    const formatted =
      `[AAMC MCAT - ${q.section_label || q.section}] (${q.difficulty})\n` +
      `${q.stimulus_text ? q.stimulus_text + '\n\n' : ''}` +
      `Question: ${q.question_stem}\n\n` +
      (q.options || []).map((o) => `${o.id}: ${o.text}`).join('\n') +
      `\n\nCorrect Answer: ${q.correct_answer_id}\n\nExplanation: ${q.explanation}`;
    navigator.clipboard.writeText(formatted);
    setCopiedId(q.id);
    setTimeout(() => setCopiedId(null), 2000);
  }, []);

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
      const order = { low: 1, easy: 1, medium: 2, high: 3, hard: 3 };
      return list.sort(
        (a, b) => (order[(a.difficulty || '').toLowerCase()] || 0) - (order[(b.difficulty || '').toLowerCase()] || 0)
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
    rawQuestionsCount: rawQuestions.length,
    repoStats,
    loading,
    sectionFilter,
    setSectionFilter,
    diffFilter,
    setDiffFilter,
    statusFilter,
    setStatusFilter,
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
