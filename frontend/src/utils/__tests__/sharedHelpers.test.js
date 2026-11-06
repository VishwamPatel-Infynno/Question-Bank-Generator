import { describe, expect, it } from 'vitest';
import {
  filterQuestionsByText,
  formatCorrectAnswers,
  getAuditCostBreakdown,
  getCorrectAnswerIds,
  getReviewPillars,
  hasQuestionImage,
  isCorrectOption
} from '../questionHelpers';
import { allSelected, toggleAll, toggleId } from '../selection';
import { passageQuestionCounts, sortPassages } from '../passageHelpers';
import { buildBatchPayload } from '../batchPayload';

describe('correct answer helpers', () => {
  it('prefers the id list, else splits the single id, always upper-cased and trimmed', () => {
    expect(getCorrectAnswerIds({ correct_answer_ids: [' a', 'C'] })).toEqual(['A', 'C']);
    expect(getCorrectAnswerIds({ correct_answer_ids: [], correct_answer_id: 'b, d' })).toEqual(['B', 'D']);
    expect(getCorrectAnswerIds({})).toEqual([]);
    expect(getCorrectAnswerIds(null)).toEqual([]);
  });
  it('matches options case-insensitively and formats with a fallback', () => {
    expect(isCorrectOption({ correct_answer_id: 'b' }, 'B')).toBe(true);
    expect(isCorrectOption({ correct_answer_ids: ['A'] }, 'c')).toBe(false);
    expect(formatCorrectAnswers({ correct_answer_ids: ['A', 'C'] })).toBe('A, C');
    expect(formatCorrectAnswers({}, 'A')).toBe('A');
    expect(formatCorrectAnswers({})).toBe('');
  });
});

describe('hasQuestionImage', () => {
  it('looks at the question, its visual stage and the passage visual stage', () => {
    expect(hasQuestionImage({ image_url: 'x' })).toBe(true);
    expect(hasQuestionImage({ stage_outcomes: { visual_stimulus: { image_svg: '<svg/>' } } })).toBe(true);
    expect(hasQuestionImage({ stage_outcomes: { passage_visual_stimulus: { image_url: 'u' } } })).toBe(true);
    expect(hasQuestionImage({ image_description: 'text only' })).toBe(false);
    expect(hasQuestionImage(undefined)).toBe(false);
  });
});

describe('getReviewPillars / getAuditCostBreakdown', () => {
  it('returns four 25-point pillars with null scores when the rubric is missing', () => {
    const pillars = getReviewPillars(undefined);
    expect(pillars).toHaveLength(4);
    expect(pillars.every((p) => p.max === 25 && p.score === null)).toBe(true);
    expect(getReviewPillars({ clarity_score: 20 })[1].score).toBe(20);
  });
  it('subtracts the recorded visual cost only when there is a visual', () => {
    const q = {
      cost_usd: 0.05,
      image_url: 'x',
      stage_outcomes: { visual_stimulus: { usage: { cost_usd: 0.02 } } },
      token_usage_details: [{ duration_ms: 100 }, { duration_ms: 0 }, null, { duration_ms: 50 }]
    };
    const b = getAuditCostBreakdown(q);
    expect(b).toMatchObject({ totalCost: 0.05, hasVisual: true, visualCost: 0.02, totalDurationMs: 150 });
    expect(b.cognitiveCost).toBeCloseTo(0.03);
    expect(b.stageTimings).toHaveLength(2);
    expect(getAuditCostBreakdown({ cost_usd: 0.01 })).toMatchObject({ hasVisual: false, cognitiveCost: 0.01, visualCost: 0 });
    expect(getAuditCostBreakdown({ cost_usd: 0.01, image_description: 'desc' }).hasVisual).toBe(true);
  });
});

describe('filterQuestionsByText', () => {
  const qs = [
    { id: 1, question_stem: 'Enzyme kinetics', subtopic: 'K' },
    { id: 2, explanation: 'Because of ENTROPY' },
    { id: 3, stimulus_text: 'a passage' }
  ];
  it('is case-insensitive across four fields and returns the input list for an empty query', () => {
    expect(filterQuestionsByText(qs, '  ')).toBe(qs);
    expect(filterQuestionsByText(qs, 'entropy').map((q) => q.id)).toEqual([2]);
    expect(filterQuestionsByText(qs, 'PASSAGE').map((q) => q.id)).toEqual([3]);
    expect(filterQuestionsByText(qs, 'nope')).toEqual([]);
  });
});

describe('selection helpers', () => {
  it('toggleId adds and removes', () => {
    expect(toggleId(['a'], 'b')).toEqual(['a', 'b']);
    expect(toggleId(['a', 'b'], 'a')).toEqual(['b']);
  });
  it('toggleAll selects the visible page or clears it, keeping other selections', () => {
    expect(toggleAll(['z'], ['a', 'b'])).toEqual(['z', 'a', 'b']);
    expect(toggleAll(['z', 'a', 'b'], ['a', 'b'])).toEqual(['z']);
    expect(toggleAll(['a'], ['a', 'b'])).toEqual(['a', 'b']);
    expect(toggleAll(['a'], [])).toEqual(['a']);
    expect(allSelected(['a', 'b'], ['a'])).toBe(true);
    expect(allSelected([], [])).toBe(false);
  });
});

describe('passage helpers', () => {
  const ps = [
    { id: 'p1', title: 'Beta', word_count: 50, created_at: '2026-01-02' },
    { id: 'p2', title: 'alpha', word_count: 500, created_at: '2026-01-01' }
  ];
  it('sorts by every key without mutating the input', () => {
    expect(sortPassages(ps, 'newest').map((p) => p.id)).toEqual(['p1', 'p2']);
    expect(sortPassages(ps, 'oldest').map((p) => p.id)).toEqual(['p2', 'p1']);
    expect(sortPassages(ps, 'words_desc').map((p) => p.id)).toEqual(['p2', 'p1']);
    expect(sortPassages(ps, 'words_asc').map((p) => p.id)).toEqual(['p1', 'p2']);
    expect(sortPassages(ps, 'title_asc').map((p) => p.id)).toEqual(['p2', 'p1']);
    expect(sortPassages(ps, 'unknown').map((p) => p.id)).toEqual(['p1', 'p2']);
    expect(ps[0].id).toBe('p1');
  });
  it('builds the question-count map', () => {
    expect(passageQuestionCounts([{ id: 'a', question_count: 3 }, { id: 'b' }])).toEqual({ a: 3, b: 0 });
  });
});

describe('buildBatchPayload', () => {
  const base = {
    selectedSection: 'chem_phys',
    selectedSubject: '',
    selectedTopic: 'Kinetics',
    selectedSubtopic: 'Kinetics (All Concepts)',
    selectedSubtopics: [],
    selectedSkill: '',
    selectedSubskill: '',
    selectedSubskills: [],
    questionType: '',
    difficulty: 'medium',
    totalQuestions: 50,
    passageMode: 'single_passage',
    passageRequired: 'Yes',
    primaryTrap: 'Automatic',
    primaryTraps: [],
    likelyMistakePattern: 'Automatic',
    likelyMistakePatterns: [],
    allowAiImages: true,
    requireImage: false,
    additionalInstructions: '  '
  };
  it('maps a 50-question passage set', () => {
    const p = buildBatchPayload(base);
    expect(p).toMatchObject({
      section: 'chem_phys',
      subject: undefined,
      topic: 'Kinetics',
      subtopic: 'Kinetics (All Concepts)',
      question_type: 'PASSAGE_BASED_MCQ',
      passage_count: 10,
      passage_question_count: 50,
      primary_trap: 'Automatic',
      likely_mistake_pattern: 'Automatic',
      additional_instructions: undefined,
      allow_ai_images: true,
      require_image: false,
      require_passage_image: true,
      visual_type: 'AI_FLUX_Image'
    });
  });
  it('maps an independent single question with images off and joined lists', () => {
    const p = buildBatchPayload({
      ...base,
      totalQuestions: 1,
      passageMode: 'independent',
      allowAiImages: false,
      selectedSubtopics: ['Rate laws', 'Catalysis'],
      primaryTraps: ['Extreme_Language'],
      likelyMistakePatterns: ['Unit confusion', 'Sign error']
    });
    expect(p).toMatchObject({
      subtopic: 'Rate laws, Catalysis',
      question_type: 'DISCRETE_MCQ',
      passage_count: 0,
      passage_question_count: undefined,
      primary_trap: 'Extreme_Language',
      likely_mistake_pattern: 'Unit confusion, Sign error',
      allow_ai_images: false,
      require_image: false,
      require_passage_image: false,
      visual_type: 'None'
    });
    expect(buildBatchPayload({ ...base, totalQuestions: 1, passageMode: 'independent' }).require_image).toBe(true);
    expect(buildBatchPayload({ ...base, totalQuestions: 5 }).passage_count).toBe(1);
  });
});
