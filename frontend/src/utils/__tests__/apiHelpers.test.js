import { describe, it, expect, vi, afterEach } from 'vitest';
import { SECTION_FILTER_OPTIONS, SECTION_IDS, getSectionShortLabel } from '../../constants';
import {
  fetchQuestions,
  updateQuestionStatus,
  deleteBatch,
  fetchEnhancedInstructions,
  fetchRefinedQuestion,
  fetchPassageAudit,
  fetchStudyGuide
} from '../../services';

describe('section short labels', () => {
  it('come from one table', () => {
    expect(getSectionShortLabel('chem_phys')).toBe('Chem / Phys');
    expect(getSectionShortLabel('CARS')).toBe('CARS');
    expect(getSectionShortLabel('bio_biochem')).toBe('Bio / Biochem');
    expect(getSectionShortLabel('')).toBe('General');
    expect(getSectionShortLabel('mystery')).toBe('mystery');
  });

  it('filter pills list every section after "All Sections"', () => {
    expect(SECTION_FILTER_OPTIONS[0]).toEqual({ id: '', label: 'All Sections' });
    expect(SECTION_FILTER_OPTIONS.slice(1).map((o) => o.id)).toEqual(Object.values(SECTION_IDS));
  });
});

describe('api request helper', () => {
  afterEach(() => vi.unstubAllGlobals());

  const okJson = (payload) =>
    vi.fn().mockResolvedValue({ ok: true, status: 200, json: async () => payload, clone() { return this; } });

  it('GET with query and signal', async () => {
    const fetchMock = okJson({ questions: [] });
    vi.stubGlobal('fetch', fetchMock);
    const ctrl = new AbortController();
    await fetchQuestions({ section: 'cars', search: '', slim: true }, ctrl.signal);
    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toBe('/api/questions?section=cars&slim=true');
    expect(init.method).toBe('GET');
    expect(init.signal).toBe(ctrl.signal);
    expect(init.body).toBeUndefined();
  });

  it('JSON body and method for mutations', async () => {
    const fetchMock = okJson({ success: true });
    vi.stubGlobal('fetch', fetchMock);
    await updateQuestionStatus('q1', 'in_bank');
    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toBe('/api/questions/q1/status');
    expect(init.method).toBe('PATCH');
    expect(init.headers['Content-Type']).toBe('application/json');
    expect(JSON.parse(init.body)).toEqual({ status: 'in_bank' });
  });

  it('throws a descriptive error on non-2xx with the server detail', async () => {
    const res = { ok: false, status: 404, json: async () => ({ detail: 'Batch not found' }) };
    res.clone = () => res;
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(res));
    await expect(deleteBatch('b9')).rejects.toThrow('Delete batch b9 failed (HTTP 404): Batch not found');
  });

  it('fetchEnhancedInstructions sends payload to /api/ai/enhance-instructions', async () => {
    const fetchMock = okJson({ enhanced_instructions: 'AAMC Mandate' });
    vi.stubGlobal('fetch', fetchMock);
    const result = await fetchEnhancedInstructions({
      instructions: 'make it hard',
      section: 'chem_phys',
      topic: 'Kinetics'
    });
    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toBe('/api/ai/enhance-instructions');
    expect(init.method).toBe('POST');
    expect(JSON.parse(init.body).instructions).toBe('make it hard');
    expect(result.enhanced_instructions).toBe('AAMC Mandate');
  });

  it('fetchRefinedQuestion sends question and action to /api/ai/refine-question', async () => {
    const fetchMock = okJson({ refined_question: { question_stem: 'Refined stem' } });
    vi.stubGlobal('fetch', fetchMock);
    const result = await fetchRefinedQuestion({
      action: 'polish_distractor',
      question: { question_stem: 'Original stem' }
    });
    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toBe('/api/ai/refine-question');
    expect(init.method).toBe('POST');
    expect(JSON.parse(init.body).action).toBe('polish_distractor');
    expect(result.refined_question.question_stem).toBe('Refined stem');
  });

  it('fetchPassageAudit sends passage text to /api/ai/audit-passage', async () => {
    const fetchMock = okJson({ flesch_kincaid_grade: 12.5, aamc_alignment_score: 95 });
    vi.stubGlobal('fetch', fetchMock);
    const result = await fetchPassageAudit('Sample passage text here.');
    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toBe('/api/ai/audit-passage');
    expect(init.method).toBe('POST');
    expect(JSON.parse(init.body)).toEqual({ passage_text: 'Sample passage text here.' });
    expect(result.aamc_alignment_score).toBe(95);
  });

  it('fetchStudyGuide sends questions to /api/ai/study-guide', async () => {
    const fetchMock = okJson({ title: 'Study Guide', flashcards: [] });
    vi.stubGlobal('fetch', fetchMock);
    const result = await fetchStudyGuide([{ question_stem: 'Sample stem' }]);
    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toBe('/api/ai/study-guide');
    expect(init.method).toBe('POST');
    expect(result.title).toBe('Study Guide');
  });
});
