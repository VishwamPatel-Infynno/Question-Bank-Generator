import { describe, expect, it } from 'vitest';
import { DUPLICATE_SOFT_THRESHOLD } from '../../constants';
import { canCompare, getDuplicateState, hasDuplicateAlert } from '../duplicateHelpers';

const withInfo = (info, extra = {}) => ({
  id: 'q1',
  duplicate_info: {
    is_duplicate: false,
    similarity_score: 0,
    is_overridden: false,
    ...info
  },
  ...extra
});

describe('getDuplicateState', () => {
  it('returns none for missing info', () => {
    expect(getDuplicateState(null).level).toBe('none');
    expect(getDuplicateState({ id: 'q' }).level).toBe('none');
    expect(getDuplicateState({ duplicate_info: null }).percent).toBe(0);
  });

  it('flags a hard duplicate as high with a rounded percent', () => {
    const state = getDuplicateState(withInfo({ is_duplicate: true, similarity_score: 0.876 }));
    expect(state).toMatchObject({ level: 'high', percent: 88, isOverridden: false });
    expect(state.info.similarity_score).toBe(0.876);
  });

  it('derives similar from the soft threshold, not from a flag', () => {
    expect(DUPLICATE_SOFT_THRESHOLD).toBe(0.6);
    expect(getDuplicateState(withInfo({ similarity_score: 0.6 })).level).toBe('similar');
    expect(getDuplicateState(withInfo({ similarity_score: 0.65 })).percent).toBe(65);
    expect(getDuplicateState(withInfo({ similarity_score: 0.59 })).level).toBe('none');
  });

  it('reports overridden whether the flag is in the info or on the question', () => {
    const viaInfo = getDuplicateState(withInfo({ is_duplicate: true, similarity_score: 0.9, is_overridden: true }));
    expect(viaInfo).toMatchObject({ level: 'overridden', isOverridden: true, percent: 90 });
    const viaQuestion = getDuplicateState(withInfo({ is_duplicate: true, similarity_score: 0.9 }, { is_duplicate_override: true }));
    expect(viaQuestion.level).toBe('overridden');
  });
});

describe('hasDuplicateAlert / canCompare', () => {
  it('alerts for high and similar, not for overridden or none', () => {
    expect(hasDuplicateAlert(withInfo({ is_duplicate: true, similarity_score: 0.8 }))).toBe(true);
    expect(hasDuplicateAlert(withInfo({ similarity_score: 0.7 }))).toBe(true);
    expect(hasDuplicateAlert(withInfo({ is_duplicate: true, similarity_score: 0.8, is_overridden: true }))).toBe(false);
    expect(hasDuplicateAlert(withInfo({ similarity_score: 0.2 }))).toBe(false);
    expect(hasDuplicateAlert(null)).toBe(false);
  });

  it('can compare any flagged, similar or overridden question', () => {
    expect(canCompare(withInfo({ is_duplicate: true, similarity_score: 0.8 }))).toBe(true);
    expect(canCompare(withInfo({ similarity_score: 0.7 }))).toBe(true);
    expect(canCompare(withInfo({ similarity_score: 0.9, is_overridden: true }))).toBe(true);
    expect(canCompare(withInfo({ similarity_score: 0.1 }))).toBe(false);
    expect(canCompare(undefined)).toBe(false);
  });
});
