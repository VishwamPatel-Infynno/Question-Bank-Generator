import { describe, expect, it } from 'vitest';
import {
  computeJobQuestionCounts,
  resolveQuestionStatus,
  resolveJobActualCount,
  isJobShortfall
} from '../batchJobHelpers';

describe('resolveQuestionStatus', () => {
  it('prefers discarded, then deleted, then the explicit status', () => {
    expect(resolveQuestionStatus({ status: 'discarded', is_deleted: true })).toBe('discarded');
    expect(resolveQuestionStatus({ status: 'in_bank', is_deleted: true })).toBe('deleted');
    expect(resolveQuestionStatus({ status: 'batch_only' })).toBe('batch_only');
  });

  it('derives a status from the score using the shared cut-offs', () => {
    expect(resolveQuestionStatus({ final_score: 91 })).toBe('ai_validated');
    expect(resolveQuestionStatus({ final_score: 81 })).toBe('ai_validated');
    expect(resolveQuestionStatus({ final_score: 80 })).toBe('batch_only');
    expect(resolveQuestionStatus({ final_score: 76 })).toBe('batch_only');
    expect(resolveQuestionStatus({ final_score: 75 })).toBe('batch_only');
    expect(resolveQuestionStatus({ final_score: 70 })).toBe('batch_only');
    expect(resolveQuestionStatus({ final_score: 69 })).toBe('below_threshold');
    expect(resolveQuestionStatus({ final_score: 65 })).toBe('below_threshold');
    expect(resolveQuestionStatus({ final_score: 64 })).toBe('below_threshold');
    expect(resolveQuestionStatus({ final_score: 50 })).toBe('below_threshold');
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

describe('resolveJobActualCount', () => {
  it('prefers visibleQuestions count when job.questions is present', () => {
    const job = { questions: [{ id: 'q1' }, { id: 'q2' }], actual_count: 5 };
    const visibleQuestions = [{ id: 'q1' }, { id: 'q2' }, { id: 'q3' }, { id: 'q4' }];
    expect(resolveJobActualCount(job, visibleQuestions)).toBe(4);
  });

  it('falls back to job.actual_count when job.questions is missing or empty', () => {
    expect(resolveJobActualCount({ actual_count: 3 }, [])).toBe(3);
    expect(resolveJobActualCount({ questions: [], actual_count: 4 }, [])).toBe(4);
    expect(resolveJobActualCount(null, [])).toBe(0);
  });
});

describe('isJobShortfall', () => {
  it('returns true when actual count is less than target count', () => {
    expect(isJobShortfall({ target_count: 5 }, 4)).toBe(true);
    expect(isJobShortfall({ target_count: 5, actual_count: 3 })).toBe(true);
  });

  it('returns false when actual count meets or exceeds target count', () => {
    expect(isJobShortfall({ target_count: 5 }, 5)).toBe(false);
    expect(isJobShortfall({ target_count: 5 }, 6)).toBe(false);
    expect(isJobShortfall({ target_count: 5, actual_count: 5 })).toBe(false);
  });
});
