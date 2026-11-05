import { useMemo } from 'react';
import DOMPurify from 'dompurify';

/**
 * Renders untrusted SVG markup safely. Scripts, event handlers and foreign objects
 * are stripped by DOMPurify's SVG profile before the markup reaches the DOM.
 * @param {Object} props
 * @param {string} props.svg - Raw SVG markup.
 * @param {string} [props.className] - Class for the wrapper element.
 */
export default function SafeSvg({ svg, className }) {
  const clean = useMemo(
    () => DOMPurify.sanitize(svg || '', { USE_PROFILES: { svg: true, svgFilters: true } }),
    [svg]
  );
  return <div className={className} dangerouslySetInnerHTML={{ __html: clean }} />;
}
