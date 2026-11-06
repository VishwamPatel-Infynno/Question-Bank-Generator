import { describe, expect, it } from 'vitest';
import {
  countWords,
  formatCostUsd,
  formatDate,
  formatDurationMs,
  formatExamTime,
  formatTokenCount
} from '../formatters';
import { formatDateTime, formatTime } from '../formatters';

describe('formatters', () => {
  it('formats durations in ms or seconds and hides empty values', () => {
    expect(formatDurationMs(450)).toBe('450 ms');
    expect(formatDurationMs(1500)).toBe('1.5 s');
    expect(formatDurationMs(0)).toBe('');
    expect(formatDurationMs(undefined)).toBe('');
  });

  it('formats cost with a floor and zero handling', () => {
    expect(formatCostUsd(0)).toBe('$0.00');
    expect(formatCostUsd(undefined)).toBe('$0.00');
    expect(formatCostUsd(0.000001)).toBe('< $0.00001');
    expect(formatCostUsd(0.0123)).toBe('$0.01230');
    expect(formatCostUsd(1.5, 2)).toBe('$1.50');
  });

  it('formats token counts', () => {
    expect(formatTokenCount(0)).toBe('0');
    expect(formatTokenCount(null)).toBe('0');
    expect(formatTokenCount(1234)).toBe((1234).toLocaleString());
  });

  it('formats dates and survives bad input', () => {
    expect(formatDate('')).toBe('');
    expect(formatDate('not a date')).toBe('not a date');
    expect(formatDate('2025-03-04T12:00:00Z')).toMatch(/2025/);
  });

  it('counts words', () => {
    expect(countWords('one two  three')).toBe(3);
    expect(countWords('')).toBe(0);
  });

  it('formats exam time with plural handling', () => {
    expect(formatExamTime([])).toBe('0 minutes');
    expect(formatExamTime([{ section: 'chem_phys' }])).toMatch(/^\d+ minutes?$/);
  });
});

describe('date and time formatting', () => {
  it('returns an empty string for missing or invalid timestamps', () => {
    for (const bad of [undefined, null, '', 'nope']) {
      expect(formatDateTime(bad)).toBe('');
      expect(formatTime(bad)).toBe('');
    }
  });

  it('formats valid timestamps', () => {
    expect(formatDateTime('2025-03-04T12:30:00Z')).toMatch(/2025|25/);
    expect(formatTime('2025-03-04T12:30:00Z')).toMatch(/\d{1,2}:\d{2}/);
  });
});
