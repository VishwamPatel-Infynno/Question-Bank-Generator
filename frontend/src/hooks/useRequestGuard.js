import { useEffect, useState } from 'react';
import { createRequestGuard } from '../utils/requestGuard';

/** A request guard (see utils/requestGuard) that retires its requests when the component unmounts. */
export function useRequestGuard() {
  const [guard] = useState(createRequestGuard);
  useEffect(() => () => guard.cancel(), [guard]);
  return guard;
}

export default useRequestGuard;
