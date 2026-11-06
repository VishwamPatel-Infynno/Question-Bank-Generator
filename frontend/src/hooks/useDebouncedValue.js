import { useEffect, useState } from 'react';

/** `value` as it was `delayMs` ago (unchanged input returns the same value immediately). */
export function useDebouncedValue(value, delayMs = 250) {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const handler = setTimeout(() => setDebounced(value), delayMs);
    return () => clearTimeout(handler);
  }, [value, delayMs]);
  return debounced;
}

export default useDebouncedValue;
