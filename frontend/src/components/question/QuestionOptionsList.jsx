import { CheckCircle, Scale } from 'lucide-react';
import { countWords } from '../../utils';

const EMPTY_ARRAY = Object.freeze([]);

/**
 * QuestionOptionsList
 *
 * Renders the multiple-choice options with anti-guessability symmetry indicators,
 * word count counters, correct answer indicators, and inline-edit support.
 */
export default function QuestionOptionsList({
  options = EMPTY_ARRAY,
  correctKeysList = EMPTY_ARRAY,
  optionSymmetry = null,
  isEditing = false,
  editedOptions = EMPTY_ARRAY,
  onEditedOptionsChange = null
}) {
  const currentOptionsList = options || [];

  return (
    <div className="choice-options-wrap">
      {/* Options Header & Anti-Guessability Symmetry Badge */}
      <div className="choice-options-header">
        <span className="choice-options-label">
          Choices
        </span>
        {optionSymmetry && (
          <span
            className={`badge ${optionSymmetry.is_balanced ? 'badge-emerald' : 'badge-amber'} choice-options-symmetry-badge`}
            title="Choice length balance"
          >
            <Scale size={11} />
            <span>
              {optionSymmetry.status} ({optionSymmetry.min_word_count}-{optionSymmetry.max_word_count}w)
            </span>
          </span>
        )}
      </div>

      {/* Options List */}
      <div className="choice-options-list">
        {currentOptionsList.map((opt, idx) => {
          const optId = (opt.id || '').trim().toUpperCase();
          const isCorrectKey = correctKeysList.includes(optId);
          const currentText = isEditing ? (editedOptions[idx]?.text || '') : (opt.text || '');
          const optWordCount = countWords(currentText);
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
              <div className="choice-option-content">
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
                    className="choice-option-input"
                  />
                ) : (
                  <div className="choice-option-stem">
                    {opt.text}
                  </div>
                )}
              </div>

              {/* Option Word Count Indicator */}
              <span
                className="choice-option-words-tag"
                title={`Word count for Option ${opt.id}: ${optWordCount} words`}
              >
                {optWordCount}w
              </span>

              {/* Answer Key Badge */}
              {isCorrectKey && (
                <span className="badge badge-emerald choice-option-key-badge">
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

