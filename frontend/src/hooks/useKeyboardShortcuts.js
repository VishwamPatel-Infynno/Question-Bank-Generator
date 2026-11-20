import { useEffect } from 'react';

/** True while a modal dialog is open: single-key shortcuts must not act behind it. */
function isModalOpen() {
  return Boolean(document.querySelector('[role="dialog"][aria-modal="true"]'));
}

/**
 * Global keyboard shortcuts listener.
 *
 * Supported shortcuts:
 * - Escape: Trigger modal or view dismiss action
 * - Cmd+Enter / Ctrl+Enter: Trigger generation action
 * - 't' / 'T': Toggle UI light/dark theme
 * - '/': Focus active search bar
 * - 'a' / 'A': Approve the active item
 * - 'd' / 'D': Discard the active item
 *
 * The single-key shortcuts (t, /, a, d) never fire while typing in a form field, while a modal
 * dialog is open, with Cmd/Ctrl/Alt held, or on key repeat. Pass `enabled: false` to turn them off
 * (WCAG 2.1.4); Escape and Cmd/Ctrl+Enter are unaffected.
 *
 * @param {Object} [options]
 * @param {() => void} [options.onGenerate] - Callback invoked when Cmd/Ctrl+Enter is pressed.
 * @param {() => void} [options.onToggleTheme] - Callback invoked when 't' is pressed.
 * @param {() => void} [options.onFocusSearch] - Callback invoked when '/' is pressed.
 * @param {() => void} [options.onEscape] - Callback invoked when Escape key is pressed.
 * @param {() => void} [options.onApprove] - Callback invoked when 'a' is pressed.
 * @param {() => void} [options.onDelete] - Callback invoked when 'd' is pressed.
 * @param {boolean} [options.enabled=true] - Set false to disable the single-key shortcuts.
 */
export function useKeyboardShortcuts({
  onGenerate,
  onToggleTheme,
  onFocusSearch,
  onEscape,
  onApprove,
  onDelete,
  enabled = true
} = {}) {
  useEffect(() => {
    const handleKeyDown = (e) => {
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

      // Everything below is a single-key shortcut
      if (!enabled) return;
      if (e.metaKey || e.ctrlKey || e.altKey || e.repeat) return;

      const active = document.activeElement;
      const activeTag = active ? active.tagName.toLowerCase() : '';
      const isInputActive =
        activeTag === 'input' ||
        activeTag === 'textarea' ||
        activeTag === 'select' ||
        active?.isContentEditable;
      if (isInputActive) return;
      if (isModalOpen()) return;

      const key = typeof e.key === 'string' ? e.key.toLowerCase() : '';
      const run = (callback) => {
        if (!callback) return;
        e.preventDefault();
        callback();
      };

      if (key === 't') run(onToggleTheme);
      else if (key === '/') run(onFocusSearch);
      else if (key === 'a') run(onApprove);
      else if (key === 'd') run(onDelete);
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [onGenerate, onToggleTheme, onFocusSearch, onEscape, onApprove, onDelete, enabled]);
}
