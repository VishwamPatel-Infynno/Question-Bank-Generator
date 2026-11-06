import { useEffect } from 'react';

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
