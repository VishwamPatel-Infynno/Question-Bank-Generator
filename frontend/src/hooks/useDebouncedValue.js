import { useEffect, useState } from 'react';

/**
 * Tracks and delays updating a value until a specified debounce interval has elapsed.
 *
 * @template T
 * @param {T} value - The input value to debounce.
 * @param {number} [delayMs=250] - Debounce delay in milliseconds.
 * @returns {T} The debounced value.
 */
export function useDebouncedValue(value, delayMs = 250) {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const handler = setTimeout(() => setDebounced(value), delayMs);
    return () => clearTimeout(handler);
  }, [value, delayMs]);
  return debounced;
}

export default useDebouncedValue;
