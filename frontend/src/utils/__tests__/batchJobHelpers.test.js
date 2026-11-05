import { describe, expect, it } from 'vitest';
import { computeJobQuestionCounts, resolveQuestionStatus } from '../batchJobHelpers';

describe('resolveQuestionStatus', () => {
  it('prefers discarded, then deleted, then the explicit status', () => {
    expect(resolveQuestionStatus({ status: 'discarded', is_deleted: true })).toBe('discarded');
    expect(resolveQuestionStatus({ status: 'in_bank', is_deleted: true })).toBe('deleted');
    expect(resolveQuestionStatus({ status: 'batch_only' })).toBe('batch_only');
  });

  it('derives a status from the score using the shared cut-offs', () => {
    expect(resolveQuestionStatus({ final_score: 91 })).toBe('ai_validated');
    expect(resolveQuestionStatus({ final_score: 90 })).toBe('batch_only');
    expect(resolveQuestionStatus({ final_score: 86 })).toBe('batch_only');
    expect(resolveQuestionStatus({ final_score: 85 })).toBe('below_threshold');
  });

  it('treats a missing question as below threshold', () => {
    expect(resolveQuestionStatus(null)).toBe('below_threshold');
  });
});

describe('computeJobQuestionCounts', () => {
  it('buckets questions by resolved status and counts deletions separately', () => {
    const counts = computeJobQuestionCounts([
      { status: 'ai_validated' },
      { status: 'ai_validated' },
      { status: 'batch_only' },
      { status: 'in_bank' },
      { status: 'discarded' },
      { status: 'below_threshold' },
      { status: 'in_bank', is_deleted: true },
      { status: 'discarded', is_deleted: true }
    ]);
    expect(counts).toEqual({
      deletedCount: 1,
      validatedCount: 2,
      batchOnlyCount: 1,
      inBankCount: 1,
      // a discarded question that is also deleted is counted in neither bucket
      discardedCount: 1,
      belowCount: 1
    });
  });
});
