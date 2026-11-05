import { useEffect } from 'react';

export function useKeyboardShortcuts({
  onGenerate,
  onApprove,
  onDiscard,
  onToggleEdit,
  onToggleTheme,
  onFocusSearch,
  onEscape,
  onNextQuestion,
  onPrevQuestion
}) {
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

      // Key: A -> Approve Candidate
      if (e.key.toLowerCase() === 'a' && !e.metaKey && !e.ctrlKey) {
        if (onApprove) {
          e.preventDefault();
          onApprove();
        }
        return;
      }

      // Key: D -> Discard Candidate
      if (e.key.toLowerCase() === 'd' && !e.metaKey && !e.ctrlKey) {
        if (onDiscard) {
          e.preventDefault();
          onDiscard();
        }
        return;
      }

      // Key: E -> Quick Edit
      if (e.key.toLowerCase() === 'e' && !e.metaKey && !e.ctrlKey) {
        if (onToggleEdit) {
          e.preventDefault();
          onToggleEdit();
        }
        return;
      }

      // Key: J or ArrowRight -> Next Staged Question
      if ((e.key.toLowerCase() === 'j' || e.key === 'ArrowRight') && !e.metaKey && !e.ctrlKey) {
        if (onNextQuestion) {
          e.preventDefault();
          onNextQuestion();
          return;
        }
      }

      // Key: K or ArrowLeft -> Previous Staged Question
      if ((e.key.toLowerCase() === 'k' || e.key === 'ArrowLeft') && !e.metaKey && !e.ctrlKey) {
        if (onPrevQuestion) {
          e.preventDefault();
          onPrevQuestion();
          return;
        }
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [
    onGenerate,
    onApprove,
    onDiscard,
    onToggleEdit,
    onToggleTheme,
    onFocusSearch,
    onEscape,
    onNextQuestion,
    onPrevQuestion
  ]);
}
