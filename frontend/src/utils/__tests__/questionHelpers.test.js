import { describe, expect, it } from 'vitest';
import { formatQuestionForCopy, pickExportQuestions } from '../questionHelpers';
import { flattenTopics } from '../taxonomyHelpers';

describe('formatQuestionForCopy', () => {
  const q = {
    section_label: 'Chem',
    difficulty: 'hard',
    question_stem: 'What happens?',
    options: [
      { id: 'A', text: 'one' },
      { id: 'B', text: 'two' }
    ],
    correct_answer_id: 'A',
    explanation: 'Because.'
  };

  it('lays out header, stem, options, key and explanation', () => {
    expect(formatQuestionForCopy(q)).toBe(
      '[AAMC MCAT - Chem] (hard)\nQuestion: What happens?\n\nA: one\nB: two\n\nCorrect Answer: A\n\nExplanation: Because.'
    );
  });

  it('puts the passage first when there is one and falls back to the section id', () => {
    const text = formatQuestionForCopy({ ...q, section_label: '', section: 'cars', stimulus_text: 'Passage.' });
    expect(text.startsWith('[AAMC MCAT - cars] (hard)\nPassage.\n\nQuestion:')).toBe(true);
  });
});

describe('pickExportQuestions', () => {
  const bankPool = [{ id: 'a' }, { id: 'b' }, { id: 'c' }];
  const filteredQuestions = [{ id: 'b' }];
  const base = { bankPool, filteredQuestions, selectedIds: [], hasActiveFilters: false };

  it('exports the selection when it is non-empty', () => {
    expect(pickExportQuestions({ ...base, scope: 'selected', selectedIds: ['c', 'a'] })).toEqual([
      { id: 'a' },
      { id: 'c' }
    ]);
  });

  it('falls back to the whole bank for an empty selection or scope all', () => {
    expect(pickExportQuestions({ ...base, scope: 'selected' })).toBe(bankPool);
    expect(pickExportQuestions({ ...base, scope: 'all' })).toBe(bankPool);
  });

  it('uses the filtered list only while filters are active', () => {
    expect(pickExportQuestions({ ...base, scope: 'filtered', hasActiveFilters: true })).toBe(
      filteredQuestions
    );
    expect(pickExportQuestions({ ...base, scope: 'filtered' })).toBe(bankPool);
  });
});

describe('flattenTopics', () => {
  const topic = (id) => ({ id, name: id });
  const subjects = [
    {
      id: 's1',
      name: 'S1',
      units: [
        { id: 'u1', name: 'U1', topics: [topic('t1'), topic('t2'), topic('t3')] },
        { id: 'u2', name: 'U2', topics: [topic('t4')] },
        { id: 'u3', name: 'U3', topics: [topic('t5')] }
      ]
    },
    { id: 's2', name: 'S2', units: [{ id: 'u4', name: 'U4', topics: [topic('t6')] }] }
  ];

  it('returns every topic of the selected subject with unit and subject context', () => {
    const topics = flattenTopics(subjects, subjects[0]);
    expect(topics.map((t) => t.id)).toEqual(['t1', 't2', 't3', 't4', 't5']);
    expect(topics[3]).toMatchObject({ unitId: 'u2', unitName: 'U2', subjectId: 's1', subjectName: 'S1' });
  });

  it('limits the all-disciplines overview to two units and two topics each', () => {
    expect(flattenTopics(subjects, null).map((t) => t.id)).toEqual(['t1', 't2', 't4', 't6']);
  });

  it('copes with missing units and topics', () => {
    expect(flattenTopics([{ id: 'x', name: 'X' }], null)).toEqual([]);
    expect(flattenTopics(undefined, null)).toEqual([]);
  });
});
