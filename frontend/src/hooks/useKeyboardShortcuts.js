import { useEffect } from 'react';

/**
 * Global keyboard shortcuts listener.
 *
 * Supported shortcuts:
 * - Escape: Trigger modal or view dismiss action
 * - Cmd+Enter / Ctrl+Enter: Trigger generation action
 * - 't' / 'T': Toggle UI light/dark theme (disabled in form inputs)
 * - '/': Focus active search bar (disabled in form inputs)
 *
 * @param {Object} [options]
 * @param {() => void} [options.onGenerate] - Callback invoked when Cmd/Ctrl+Enter is pressed.
 * @param {() => void} [options.onToggleTheme] - Callback invoked when 't' is pressed.
 * @param {() => void} [options.onFocusSearch] - Callback invoked when '/' is pressed.
 * @param {() => void} [options.onEscape] - Callback invoked when Escape key is pressed.
 */
export function useKeyboardShortcuts({ onGenerate, onToggleTheme, onFocusSearch, onEscape }) {
  useEffect(() => {
    const handleKeyDown = (e) => {
      const activeTag = document.activeElement ? document.activeElement.tagName.toLowerCase() : '';
      const isInputActive =
        activeTag === 'input' ||
        activeTag === 'textarea' ||
        activeTag === 'select' ||
        document.activeElement?.isContentEditable;

      // Escape always handles modal/editor dismissal
      if (e.key === 'Escape') {
        if (onEscape) onEscape();
        return;
      }

      // Cmd+Enter or Ctrl+Enter triggers Generation
      if ((e.metaKey || e.ctrlKey) && e.key === 'Enter') {
        e.preventDefault();
        if (onGenerate) onGenerate();
        return;
      }

      // If typing in input, ignore single-character navigation shortcuts
      if (isInputActive) return;

      // Key: T -> Toggle Theme
      if (e.key.toLowerCase() === 't' && !e.metaKey && !e.ctrlKey) {
        if (onToggleTheme) {
          e.preventDefault();
          onToggleTheme();
        }
        return;
      }

      // Key: / -> Focus Search
      if (e.key === '/' && !e.metaKey && !e.ctrlKey) {
        if (onFocusSearch) {
          e.preventDefault();
          onFocusSearch();
        }
        return;
      }

    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [onGenerate, onToggleTheme, onFocusSearch, onEscape]);
}
