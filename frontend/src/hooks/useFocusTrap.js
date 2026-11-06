import { useEffect, useRef } from 'react';

// Open traps, innermost last: Escape closes only the top dialog, never every stacked one.
const trapStack = [];

const FOCUSABLE_SELECTOR =
  'button:not([disabled]), [href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])';

/**
 * useFocusTrap:
 * WCAG-compliant keyboard focus trap for modal dialogs and drawers.
 *
 * - Traps Tab and Shift+Tab cycles strictly inside the referenced container.
 * - Auto-focuses the first focusable child upon mounting.
 * - Restores focus to the triggering element upon unmount.
 * - Listens for Escape key to close the dialog.
 */
export function useFocusTrap({ isActive = true, onClose = null }) {
  const containerRef = useRef(null);
  const previousActiveElementRef = useRef(null);
  // Callers pass inline closures; keeping the latest one in a ref stops the effect below from
  // re-running (and stealing focus back to the first control) on every parent re-render.
  const onCloseRef = useRef(onClose);
  useEffect(() => {
    onCloseRef.current = onClose;
  }, [onClose]);

  useEffect(() => {
    if (!isActive) return;

    const container = containerRef.current;
    if (!container) return;

    const trapToken = {};
    trapStack.push(trapToken);

    previousActiveElementRef.current = document.activeElement;

    // Find first focusable element and focus it
    const focusableElements = container.querySelectorAll(FOCUSABLE_SELECTOR);
    if (focusableElements.length > 0) {
      focusableElements[0].focus();
    } else {
      container.focus();
    }

    const handleKeyDown = (e) => {
      if (e.key === 'Escape') {
        // Only the topmost dialog reacts; a disabled close (null onClose, e.g. while saving) still
        // swallows the key so it cannot dismiss anything underneath.
        if (trapStack[trapStack.length - 1] !== trapToken) return;
        e.stopPropagation();
        if (onCloseRef.current) onCloseRef.current();
        return;
      }

      if (e.key !== 'Tab') return;

      const elements = Array.from(container.querySelectorAll(FOCUSABLE_SELECTOR));
      if (elements.length === 0) {
        e.preventDefault();
        return;
      }

      const firstElement = elements[0];
      const lastElement = elements[elements.length - 1];

      if (e.shiftKey) {
        // Shift + Tab: if on first element, wrap to last
        if (document.activeElement === firstElement || !container.contains(document.activeElement)) {
          e.preventDefault();
          lastElement.focus();
        }
      } else {
        // Tab: if on last element, wrap to first
        if (document.activeElement === lastElement || !container.contains(document.activeElement)) {
          e.preventDefault();
          firstElement.focus();
        }
      }
    };

    // Capture phase: runs before the app-level Escape handler, so stopPropagation really isolates it
    window.addEventListener('keydown', handleKeyDown, true);

    return () => {
      window.removeEventListener('keydown', handleKeyDown, true);
      const at = trapStack.indexOf(trapToken);
      if (at !== -1) trapStack.splice(at, 1);
      if (previousActiveElementRef.current && typeof previousActiveElementRef.current.focus === 'function') {
        previousActiveElementRef.current.focus();
      }
    };
  }, [isActive]);

  return containerRef;
}

