import { describe, expect, it } from 'vitest';
import { createRequestGuard } from '../requestGuard';

describe('createRequestGuard', () => {
  it('makes only the latest request current and aborts the earlier one', () => {
    const guard = createRequestGuard();
    const first = guard.begin();
    expect(first.isCurrent()).toBe(true);
    expect(first.signal.aborted).toBe(false);

    const second = guard.begin();
    expect(first.isCurrent()).toBe(false);
    expect(first.signal.aborted).toBe(true);
    expect(second.isCurrent()).toBe(true);
    expect(second.signal.aborted).toBe(false);
  });

  it('retires the current request on cancel', () => {
    const guard = createRequestGuard();
    const req = guard.begin();
    guard.cancel();
    expect(req.isCurrent()).toBe(false);
    expect(req.signal.aborted).toBe(true);
    expect(guard.begin().isCurrent()).toBe(true);
  });

  it('keeps guards independent of each other', () => {
    const a = createRequestGuard();
    const b = createRequestGuard();
    const ra = a.begin();
    b.begin();
    expect(ra.isCurrent()).toBe(true);
  });
});
