import { useEffect, useState } from 'react';
import { createRequestGuard } from '../utils/requestGuard';

/**
 * Instantiates a request guard that automatically aborts all active requests when the component unmounts.
 *
 * @returns {ReturnType<typeof createRequestGuard>} Request guard instance with begin(), isCurrent(), cancel().
 */
export function useRequestGuard() {
  const [guard] = useState(createRequestGuard);
  useEffect(() => () => guard.cancel(), [guard]);
  return guard;
}

export default useRequestGuard;
