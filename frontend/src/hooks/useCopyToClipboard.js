import { useCallback, useEffect, useRef, useState } from 'react';

/**
 * Copies text to the clipboard and reports which item was copied for a short while.
 *
 * `copiedKey` is the key passed to `copy` (defaults to `true`) until the timer resets it to
 * `null`, so one hook instance can drive a whole list ("is this row the copied one?") or a single
 * button. The flag only turns on when the browser actually accepted the text: clipboard access
 * fails on non-secure origins or when permission is denied. The reset timer is cleared on unmount.
 *
 * @param {number} [resetMs=2000] - How long the "copied" state stays on.
 * @returns {{ copiedKey: any, copy: (text: string, key?: any) => Promise<boolean> }}
 */
export function useCopyToClipboard(resetMs = 2000) {
  const [copiedKey, setCopiedKey] = useState(null);
  const timerRef = useRef(null);

  useEffect(() => () => clearTimeout(timerRef.current), []);

  const copy = useCallback(
    async (text, key = true) => {
      try {
        await navigator.clipboard.writeText(text);
      } catch (err) {
        console.warn('Clipboard copy failed:', err);
        return false;
      }
      setCopiedKey(key);
      clearTimeout(timerRef.current);
      timerRef.current = setTimeout(() => setCopiedKey(null), resetMs);
      return true;
    },
    [resetMs]
  );

  return { copiedKey, copy };
}

export default useCopyToClipboard;
