import { describe, expect, it } from 'vitest';
import { normalizePageSizeOptions, PAGE_SIZE_OPTIONS } from '../pagination';
import { SUBTOPIC_RESET_VALUES, toggleInList, toggleSubtopicState } from '../generatorFormState';
import { nextEnabledIndex } from '../selectHelpers';

describe('normalizePageSizeOptions', () => {
  it('turns numbers into {value,label} and names -1 "All"', () => {
    expect(normalizePageSizeOptions([10, 25, -1])).toEqual([
      { value: 10, label: '10' },
      { value: 25, label: '25' },
      { value: -1, label: 'All' }
    ]);
  });
  it('passes option objects through and handles empty input', () => {
    const objs = [{ value: 5, label: 'five' }];
    expect(normalizePageSizeOptions(objs)[0]).toBe(objs[0]);
    expect(normalizePageSizeOptions(undefined)).toEqual([]);
    expect(normalizePageSizeOptions(PAGE_SIZE_OPTIONS).map((o) => o.label)).toEqual(['15', '30', '50', 'All']);
  });
});

describe('toggleSubtopicState', () => {
  const base = { selectedTopic: 'Kinetics', selectedSubtopics: ['Rate laws'], selectedSubtopic: 'Rate laws' };

  it('adds and removes subtopics and keeps the summary label in step', () => {
    const added = toggleSubtopicState(base, 'Catalysis');
    expect(added.selectedSubtopics).toEqual(['Rate laws', 'Catalysis']);
    expect(added.selectedSubtopic).toBe('Rate laws, Catalysis');
    const removed = toggleSubtopicState(added, 'Rate laws');
    expect(removed.selectedSubtopics).toEqual(['Catalysis']);
    const empty = toggleSubtopicState(removed, 'Catalysis');
    expect(empty.selectedSubtopics).toEqual([]);
    expect(empty.selectedSubtopic).toBe('Kinetics (All Concepts)');
  });

  it('clears the selection for every reset value, including the wizard\'s "All Core Topics"', () => {
    for (const value of SUBTOPIC_RESET_VALUES) {
      const next = toggleSubtopicState(base, value);
      expect(next.selectedSubtopics).toEqual([]);
      expect(next.selectedSubtopic).toBe('Kinetics (All Concepts)');
    }
    expect(toggleSubtopicState({ ...base, selectedTopic: '' }, 'All').selectedSubtopic).toBe(
      'All High-Yield Topics (Balanced Mix)'
    );
  });

  it('toggleInList copes with a missing list', () => {
    expect(toggleInList(undefined, 'a')).toEqual(['a']);
    expect(toggleInList(['a'], 'a')).toEqual([]);
  });
});

describe('nextEnabledIndex', () => {
  const opts = [{ value: 1 }, { value: 2, disabled: true }, { value: 3 }];
  it('skips disabled options and wraps', () => {
    expect(nextEnabledIndex(opts, 0, 1)).toBe(2);
    expect(nextEnabledIndex(opts, 2, 1)).toBe(0);
    expect(nextEnabledIndex(opts, 0, -1)).toBe(2);
    expect(nextEnabledIndex(opts, 2, -1)).toBe(0);
  });
  it('stays put when nothing is enabled and returns -1 for no options', () => {
    expect(nextEnabledIndex([{ disabled: true }], 0, 1)).toBe(0);
    expect(nextEnabledIndex([], 0, 1)).toBe(-1);
  });
});
