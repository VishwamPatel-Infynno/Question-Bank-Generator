/**
 * Next option index in `direction` (+1 / -1) that is not disabled, wrapping around; returns
 * `current` unchanged when every option is disabled.
 */
export function nextEnabledIndex(options, current, direction) {
  const n = options.length;
  if (n === 0) return -1;
  let idx = current;
  for (let step = 0; step < n; step += 1) {
    idx = (idx + direction + n) % n;
    if (!options[idx]?.disabled) return idx;
  }
  return current;
}
