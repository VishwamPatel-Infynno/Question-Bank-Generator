import React from 'react';
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
    <div
      style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        flexWrap: 'wrap',
        gap: '10px',
        paddingTop: '14px',
        borderTop: '1px solid var(--border-light)'
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
        {!isSaved && onApprove ? (
          <>
            <button
              type="button"
              id="btn-admin-approve-bottom"
              className="btn-success"
              onClick={onApprove}
              disabled={isApproving}
              style={{ padding: '8px 18px', fontSize: '0.825rem' }}
              title="Save question to Question Bank (Press A)"
            >
              <CheckCircle size={15} />
              <span>{isApproving ? 'Saving...' : 'Save to Question Bank'}</span>
              <span className="kbd-hint" style={{ fontSize: '0.6rem', color: 'var(--text-on-brand, #ffffff)', borderColor: 'rgba(255,255,255,0.3)' }}>A</span>
            </button>

            {onDiscard && (
              <button
                type="button"
                className="btn-danger"
                onClick={() => onDiscard(question)}
                style={{ padding: '8px 14px', fontSize: '0.825rem' }}
                title="Discard question (Press D)"
              >
                <Trash2 size={13} />
                <span>Discard Question</span>
                <span className="kbd-hint" style={{ fontSize: '0.6rem' }}>D</span>
              </button>
            )}
          </>
        ) : (
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: 'var(--status-success)', fontWeight: 600, fontSize: '0.825rem' }}>
            <CheckCircle size={16} /> Saved in Question Bank
          </div>
        )}
      </div>

      {onNextQuestion && (
        <button
          type="button"
          id="btn-generate-another"
          className="btn-primary-luminous"
          onClick={onNextQuestion}
          style={{ padding: '8px 16px', fontSize: '0.825rem' }}
          title="Generate Next Question (Press ⌘↵)"
        >
          <Sparkles size={14} />
          <span>Create Next Question</span>
          <span className="kbd-hint" style={{ fontSize: '0.6rem', color: 'var(--text-on-brand, #ffffff)', border: 'none', background: 'rgba(255,255,255,0.2)' }}>⌘↵</span>
        </button>
      )}
    </div>
  );
}

