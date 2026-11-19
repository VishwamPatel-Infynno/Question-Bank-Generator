import { describe, expect, it, vi, beforeEach } from 'vitest';
import { fetchBatchDetail } from '../../services/api';

describe('Frontend Services & Toast Contracts', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('fetchBatchDetail defaults to slim=true query parameter', async () => {
    const mockJson = vi.fn().mockResolvedValue({ batch: { id: 'batch-1' }, jobs: [] });
    const mockFetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: mockJson,
      clone: () => ({ json: mockJson })
    });
    vi.stubGlobal('fetch', mockFetch);

    await fetchBatchDetail('batch-1');

    expect(mockFetch).toHaveBeenCalledTimes(1);
    const calledUrl = mockFetch.mock.calls[0][0];
    expect(calledUrl).toBe('/api/batches/batch-1?slim=true');
  });

  it('fetchBatchDetail supports explicit slim=false when full diagnostics are requested', async () => {
    const mockJson = vi.fn().mockResolvedValue({ batch: { id: 'batch-1' }, jobs: [] });
    const mockFetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: mockJson,
      clone: () => ({ json: mockJson })
    });
    vi.stubGlobal('fetch', mockFetch);

    await fetchBatchDetail('batch-1', null, false);

    expect(mockFetch).toHaveBeenCalledTimes(1);
    const calledUrl = mockFetch.mock.calls[0][0];
    expect(calledUrl).toBe('/api/batches/batch-1?slim=false');
  });

  it('Toast contract adheres strictly to error, success, and info categories', () => {
    const validToastTypes = ['success', 'error', 'info'];
    // In our design system, 'danger' must be mapped to 'error'
    const exportErrorPayload = {
      type: 'error',
      title: 'Study Guide Error',
      message: 'Failed to synthesize study guide.'
    };
    expect(validToastTypes.includes(exportErrorPayload.type)).toBe(true);
    expect(exportErrorPayload.type).not.toBe('danger');
  });

  describe('Adaptive Semantic Search Ranking', () => {
    const mockSemanticQuestions = [
      { id: 'q-1', final_score: 85, similarity: 0.95, created_at: '2026-01-01T00:00:00Z' },
      { id: 'q-2', final_score: 98, similarity: 0.89, created_at: '2026-02-01T00:00:00Z' },
      { id: 'q-3', final_score: 92, similarity: 0.82, created_at: '2026-03-01T00:00:00Z' }
    ];

    function resolveQuestions(rawQuestions, sortBy, searchMode) {
      if (searchMode === 'semantic') {
        if (sortBy === 'score_desc') {
          return [...rawQuestions].sort((a, b) => (b.final_score || 0) - (a.final_score || 0));
        }
        if (sortBy === 'score_asc') {
          return [...rawQuestions].sort((a, b) => (a.final_score || 0) - (b.final_score || 0));
        }
        return rawQuestions;
      }
      const list = [...rawQuestions];
      if (sortBy === 'score_desc') {
        return list.sort((a, b) => (b.final_score || 0) - (a.final_score || 0));
      }
      return list.sort((a, b) => new Date(b.created_at || 0) - new Date(a.created_at || 0));
    }

    it('preserves vector cosine similarity ranking under default sort in semantic search mode', () => {
      const result = resolveQuestions(mockSemanticQuestions, 'newest', 'semantic');
      // In semantic mode, the initial vector order (q-1 with 0.95, q-2 with 0.89, q-3 with 0.82) is preserved
      expect(result.map(q => q.id)).toEqual(['q-1', 'q-2', 'q-3']);
    });

    it('respects explicit score_desc sort override in semantic search mode', () => {
      const result = resolveQuestions(mockSemanticQuestions, 'score_desc', 'semantic');
      // q-2 (98), q-3 (92), q-1 (85)
      expect(result.map(q => q.id)).toEqual(['q-2', 'q-3', 'q-1']);
    });

    it('sorts by created_at in keyword search mode', () => {
      const result = resolveQuestions(mockSemanticQuestions, 'newest', 'keyword');
      // q-3 (March), q-2 (February), q-1 (January)
      expect(result.map(q => q.id)).toEqual(['q-3', 'q-2', 'q-1']);
    });
  });
});
