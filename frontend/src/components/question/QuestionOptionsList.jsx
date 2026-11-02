import React from 'react';
import { CheckCircle, Scale } from 'lucide-react';

/**
 * QuestionOptionsList
 *
 * Renders the multiple-choice options with anti-guessability symmetry indicators,
 * word count counters, correct answer indicators, and inline-edit support.
 */
export default function QuestionOptionsList({
  options = [],
  correctKeysList = [],
  optionSymmetry = null,
  isEditing = false,
  editedOptions = [],
  onEditedOptionsChange = null
}) {
  const currentOptionsList = options || [];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
      {/* Options Header & Anti-Guessability Symmetry Badge */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '0 2px' }}>
        <span style={{ fontSize: '0.725rem', fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
          Choices
        </span>
        {optionSymmetry && (
          <span
            className={`badge ${optionSymmetry.is_balanced ? 'badge-emerald' : 'badge-amber'}`}
            style={{ fontSize: '0.675rem', display: 'inline-flex', alignItems: 'center', gap: '5px', padding: '2px 8px' }}
            title="Choice length balance"
          >
            <Scale size={11} />
            <span>
              {optionSymmetry.status} ({optionSymmetry.min_word_count}–{optionSymmetry.max_word_count}w)
            </span>
          </span>
        )}
      </div>

      {/* Options List */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
        {currentOptionsList.map((opt, idx) => {
          const optId = (opt.id || '').trim().toUpperCase();
          const isCorrectKey = correctKeysList.includes(optId);
          const currentText = isEditing ? (editedOptions[idx]?.text || '') : (opt.text || '');
          const optWordCount = currentText.trim().split(/\s+/).filter(Boolean).length;
          let cardClass = 'choice-option-card';
          if (isCorrectKey) cardClass += ' is-correct';

          return (
            <div
              key={opt.id || `opt-${idx}`}
              className={cardClass}
            >
              {/* Option Letter Indicator */}
              <div className="choice-letter-badge">
                {opt.id}
              </div>

              {/* Option Text */}
              <div style={{ flex: 1, paddingTop: '2px' }}>
                {isEditing ? (
                  <input
                    type="text"
                    value={editedOptions[idx]?.text ?? opt.text}
                    onChange={(e) => {
                      if (!onEditedOptionsChange) return;
                      const updated = [...editedOptions];
                      updated[idx] = { ...updated[idx], text: e.target.value };
                      onEditedOptionsChange(updated);
                    }}
                    style={{ width: '100%', fontSize: '0.85rem' }}
                  />
                ) : (
                  <div
                    style={{
                      fontSize: '0.875rem',
                      fontWeight: isCorrectKey ? 600 : 400,
                      color: isCorrectKey ? 'var(--status-success)' : 'var(--text-primary)',
                      lineHeight: 1.5
                    }}
                  >
                    {opt.text}
                  </div>
                )}
              </div>

              {/* Option Word Count Indicator */}
              <span
                style={{
                  fontSize: '0.675rem',
                  color: 'var(--text-muted)',
                  fontFamily: 'var(--font-mono)',
                  background: 'var(--bg-surface-subtle)',
                  padding: '2px 6px',
                  borderRadius: 'var(--radius-xs)',
                  flexShrink: 0
                }}
                title={`Word count for Option ${opt.id}: ${optWordCount} words`}
              >
                {optWordCount}w
              </span>

              {/* Answer Key Badge */}
              {isCorrectKey && (
                <span
                  className="badge badge-emerald"
                  style={{ fontSize: '0.675rem', padding: '2px 8px', flexShrink: 0 }}
                >
                  <CheckCircle size={11} /> Correct Answer
                </span>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

