/**
 * RFC4122-style random id. crypto.randomUUID only exists in secure contexts (HTTPS/localhost),
 * so it is missing when the app is opened over plain HTTP on a LAN address.
 */
export function makeId() {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID();
  }
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
    const r = Math.floor(Math.random() * 16);
    return (c === 'x' ? r : (r & 0x3) | 0x8).toString(16);
  });
}
