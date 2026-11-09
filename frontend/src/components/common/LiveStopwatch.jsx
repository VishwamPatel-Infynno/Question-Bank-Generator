import { useState, useEffect, memo } from 'react';

/**
 * LiveStopwatch:
 * Decoupled, self-contained timer component that ticks without re-rendering parent components.
 */
function LiveStopwatch({ isRunning }) {
  const [elapsedTime, setElapsedTime] = useState('0.0');

  useEffect(() => {
    let interval = null;
    if (isRunning) {
      const startTime = Date.now();
      interval = setInterval(() => {
        setElapsedTime(((Date.now() - startTime) / 1000).toFixed(1));
      }, 200);
    }
    return () => {
      if (interval) clearInterval(interval);
    };
  }, [isRunning]);

  return (
    <span>{elapsedTime}s</span>
  );
}

export default memo(LiveStopwatch);
