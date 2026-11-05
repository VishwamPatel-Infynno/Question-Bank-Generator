import DOMPurify from 'dompurify';

/** Escapes text for safe interpolation into an HTML document string. */
export function escapeHtml(value) {
  return String(value ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

/**
 * Escapes text, then applies the same inline markdown the app UI shows
 * (**bold**, *italic*) so printed papers match what authors reviewed on screen.
 */
export function escapeInlineMarkdown(value) {
  return escapeHtml(value)
    .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
    .replace(/\*([^*]+)\*/g, '<em>$1</em>');
}

/** Sanitises untrusted SVG markup (scripts, event handlers and foreignObject are removed). */
export function sanitizeSvg(svg) {
  return DOMPurify.sanitize(svg || '', { USE_PROFILES: { svg: true, svgFilters: true } });
}

const SAFE_IMAGE_URL = /^(https?:\/\/|\/(?!\/)|data:image\/(png|jpe?g|webp|gif);base64,)/i;

/** Returns the URL escaped for an attribute, or '' when it is not a plain image location. */
export function safeImageUrl(url) {
  const value = String(url ?? '').trim();
  return SAFE_IMAGE_URL.test(value) ? escapeHtml(value) : '';
}
