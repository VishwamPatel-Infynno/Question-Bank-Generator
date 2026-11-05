/**
 * Saves text as a file through a temporary link.
 * @param {string} content - File content.
 * @param {string} filename - Suggested file name.
 * @param {string} mime - MIME type, e.g. 'text/csv;charset=utf-8;'.
 * @param {{ bom?: boolean }} [options] - `bom: true` prepends a UTF-8 byte order mark so Excel
 *   reads the file as UTF-8 (otherwise symbols such as µ and Δ turn to garbage).
 */
export function downloadTextFile(content, filename, mime, { bom = false } = {}) {
  const blob = new Blob(bom ? ['﻿', content] : [content], { type: mime });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  a.click();
  // Revoking synchronously can cancel the download in some browsers
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
