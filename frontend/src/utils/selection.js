/** Multi-select helpers shared by the bank, review queue and passage views. */

/** Adds `id` when absent, removes it when present. */
export function toggleId(selected, id) {
  return selected.includes(id) ? selected.filter((x) => x !== id) : [...selected, id];
}

/**
 * "Select all" over the ids currently on screen: deselects them when every one is selected,
 * otherwise adds the missing ones (ids selected elsewhere are kept either way).
 */
export function toggleAll(selected, visibleIds) {
  const allSelected = visibleIds.length > 0 && visibleIds.every((id) => selected.includes(id));
  if (allSelected) return selected.filter((id) => !visibleIds.includes(id));
  return Array.from(new Set([...selected, ...visibleIds]));
}

/** True when every visible id is selected (and there is at least one). */
export function allSelected(selected, visibleIds) {
  return visibleIds.length > 0 && visibleIds.every((id) => selected.includes(id));
}
