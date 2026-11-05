import { describe, expect, it } from 'vitest';
import { getBatchStageInfo, patchQuestionInDetails, reuseUnchangedBatches } from '../batchHelpers';

const batch = (over = {}) => ({
  id: 'b1',
  status: 'in_progress',
  target_count: 50,
  actual_count: 10,
  completed_jobs: 2,
  total_jobs: 10,
  ...over
});

describe('getBatchStageInfo', () => {
  it('reports completed batches as ready for review', () => {
    const info = getBatchStageInfo(batch({ status: 'completed' }));
    expect(info.activeStep).toBe(4);
    expect(info.stageBadge).toBe('Ready for Review');
  });

  it('treats stopped and cancelled the same', () => {
    for (const status of ['stopped', 'cancelled']) {
      expect(getBatchStageInfo(batch({ status })).stageBadge).toBe('Stopped by User');
    }
  });

  it('shows the error message of failed batches', () => {
    const info = getBatchStageInfo(batch({ status: 'failed', error_message: 'boom' }));
    expect(info.stageBadge).toBe('Failed');
    expect(info.stageDescription).toBe('boom');
  });

  it('is drafting while jobs are still running', () => {
    const info = getBatchStageInfo(batch());
    expect(info.activeStep).toBe(1);
    expect(info.stageDescription).toContain('2/10');
  });

  it('is auditing once every job finished and nothing refills', () => {
    const info = getBatchStageInfo(batch({ completed_jobs: 10 }), { jobs: [] });
    expect(info.isAuditing).toBe(true);
    expect(info.activeStep).toBe(2);
  });

  it('is refilling when a retried job is running', () => {
    const detail = { jobs: [{ trial_count: 2, status: 'running' }] };
    const info = getBatchStageInfo(batch({ completed_jobs: 10 }), detail);
    expect(info.isRefilling).toBe(true);
    expect(info.isAuditing).toBe(false);
    expect(info.activeStep).toBe(3);
    expect(info.hasEverRefilled).toBe(true);
  });
});

describe('reuseUnchangedBatches', () => {
  it('returns the previous array when nothing changed', () => {
    const prev = [batch(), batch({ id: 'b2' })];
    const next = prev.map((b) => ({ ...b }));
    expect(reuseUnchangedBatches(prev, next)).toBe(prev);
  });

  it('keeps unchanged objects and takes changed ones', () => {
    const prev = [batch(), batch({ id: 'b2' })];
    const next = [{ ...prev[0] }, { ...prev[1], actual_count: 11 }];
    const merged = reuseUnchangedBatches(prev, next);
    expect(merged).not.toBe(prev);
    expect(merged[0]).toBe(prev[0]);
    expect(merged[1]).toBe(next[1]);
  });

  it('adopts the new list when the previous one is empty or sizes differ', () => {
    const next = [batch()];
    expect(reuseUnchangedBatches([], next)).toBe(next);
    expect(reuseUnchangedBatches([batch(), batch({ id: 'b2' })], next)).not.toBe(next[1]);
  });
});

describe('patchQuestionInDetails', () => {
  const details = () => ({
    b1: {
      batch: { id: 'b1' },
      jobs: [
        { id: 'j1', questions: [{ id: 'q1', status: 'batch_only' }, { id: 'q2', status: 'batch_only' }] },
        { id: 'j2', questions: [{ id: 'q3', status: 'batch_only' }] }
      ],
      questions: [{ id: 'q1', status: 'batch_only' }, { id: 'q2' }, { id: 'q3' }]
    },
    b2: { batch: { id: 'b2' }, jobs: [{ id: 'j9', questions: [{ id: 'q9' }] }], questions: [] },
    b3: null
  });

  it('patches the question in its job and in the flat list only', () => {
    const before = details();
    const after = patchQuestionInDetails(before, 'q1', { status: 'in_bank' });
    expect(after.b1.jobs[0].questions[0]).toEqual({ id: 'q1', status: 'in_bank' });
    expect(after.b1.jobs[0].questions[1]).toBe(before.b1.jobs[0].questions[1]);
    expect(after.b1.questions[0].status).toBe('in_bank');
    expect(after.b1.jobs[1]).toBe(before.b1.jobs[1]);
  });

  it('keeps untouched batches (and null entries) as they were', () => {
    const before = details();
    const after = patchQuestionInDetails(before, 'q1', { status: 'in_bank' });
    expect(after.b2).toBe(before.b2);
    expect(after.b3).toBeNull();
    expect(before.b1.jobs[0].questions[0].status).toBe('batch_only'); // input not mutated
  });

  it('is a no-op for an unknown question', () => {
    const before = details();
    const after = patchQuestionInDetails(before, 'nope', { status: 'x' });
    expect(after.b1).toBe(before.b1);
  });
});
