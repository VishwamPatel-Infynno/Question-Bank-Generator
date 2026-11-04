import { CheckCircle, Trash2, Sparkles } from 'lucide-react';

/**
 * QuestionCardFooter
 *
 * Bottom action strip for QuestionCard containing Save, Discard, and Create Next Question actions,
 * complete with keyboard shortcut hints and loading states.
 */
export default function QuestionCardFooter({
  question,
  isSaved = false,
  isApproving = false,
  onApprove = null,
  onDiscard = null,
  onNextQuestion = null
}) {
  return (
    <div className="qcard-footer">
      <div className="qcard-footer-actions">
        {!isSaved && onApprove ? (
          <>
            <button
              type="button"
              id="btn-admin-approve-bottom"
              className="btn-success qcard-footer-save-btn"
              onClick={onApprove}
              disabled={isApproving}
              title="Save question to Question Bank (Press A)"
            >
              <CheckCircle size={15} />
              <span>{isApproving ? 'Saving...' : 'Save to Question Bank'}</span>
              <span className="kbd-hint qcard-footer-kbd-save">A</span>
            </button>

            {onDiscard && (
              <button
                type="button"
                className="btn-danger qcard-footer-discard-btn"
                onClick={() => onDiscard(question)}
                title="Discard question (Press D)"
              >
                <Trash2 size={13} />
                <span>Discard Question</span>
                <span className="kbd-hint qcard-footer-kbd-save">D</span>
              </button>
            )}
          </>
        ) : (
          <div className="qcard-footer-saved-label">
            <CheckCircle size={16} /> Saved in Question Bank
          </div>
        )}
      </div>

      {onNextQuestion && (
        <button
          type="button"
          id="btn-generate-another"
          className="btn-primary-luminous qcard-footer-next-btn"
          onClick={onNextQuestion}
          title="Generate Next Question (Press ⌘↵)"
        >
          <Sparkles size={14} />
          <span>Create Next Question</span>
          <span className="kbd-hint qcard-footer-kbd-next">⌘↵</span>
        </button>
      )}
    </div>
  );
}

