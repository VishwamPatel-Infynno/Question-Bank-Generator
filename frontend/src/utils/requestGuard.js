/**
 * Keeps only the newest of overlapping requests relevant.
 *
 * `begin()` aborts the previous request and returns `{ signal, isCurrent }` for the new one:
 * pass `signal` to fetch, and check `isCurrent()` before writing state, so a slow response to an
 * old filter can never overwrite the result of the current one. `cancel()` retires everything
 * (call it when the owner unmounts).
 */
export function createRequestGuard() {
  let sequence = 0;
  let controller = null;

  return {
    begin() {
      controller?.abort();
      const current = new AbortController();
      controller = current;
      const mine = ++sequence;
      return { signal: current.signal, isCurrent: () => mine === sequence };
    },
    cancel() {
      controller?.abort();
      controller = null;
      sequence += 1;
    }
  };
}
