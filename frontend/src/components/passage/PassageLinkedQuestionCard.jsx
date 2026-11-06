import React, { useState } from 'react';
import { CheckCircle2, Edit3, X } from 'lucide-react';
import { formatDifficulty, getDifficultyBadgeClass } from '../../constants/mcat';
import { getEffectiveTrapInfo } from '../../utils';
import { isCorrectOption } from '../../utils';

/**
 * PassageInlineQuestionEditor
 *
 * Compact inline form for editing question details directly from the Passage Desk.
 */
function PassageInlineQuestionEditor({ question, onSave, onCancel }) {
  const [stem, setStem] = useState(question.question_stem || '');
  const [options, setOptions] = useState(question.options || []);
  const [correctId, setCorrectId] = useState(question.correct_answer_id || 'A');
  const [explanation, setExplanation] = useState(question.explanation || '');

  const handleOptionChange = (idx, newText) => {
    setOptions(prev => prev.map((opt, i) => (i === idx ? { ...opt, text: newText } : opt)));
  };

  const handleSaveClick = () => {
    onSave({
      ...question,
      question_stem: stem,
      options,
      correct_answer_id: correctId,
      explanation
    });
  };

  return (
    <div className="passage-editor-form">
      <div className="passage-editor-field">
        <label className="passage-editor-label">
          Question Text
        </label>
        <textarea
          rows={3}
          value={stem}
          onChange={(e) => setStem(e.target.value)}
          className="passage-editor-input"
        />
      </div>

      <div className="passage-editor-options-list">
        <label className="passage-editor-label">
          Options
        </label>
        {options.map((opt, idx) => (
          <div key={opt.id} className="passage-editor-option-row">
            <button
              type="button"
              onClick={() => setCorrectId(opt.id)}
              className={`passage-editor-option-btn ${correctId === opt.id ? 'correct' : ''}`}
              title={`Mark Option ${opt.id} as Correct Answer`}
            >
              {opt.id}
            </button>
            <input
              type="text"
              value={opt.text}
              onChange={(e) => handleOptionChange(idx, e.target.value)}
              className="passage-editor-input"
            />
          </div>
        ))}
      </div>

      <div className="passage-editor-field">
        <label className="passage-editor-label">
          Explanation
        </label>
        <textarea
          rows={3}
          value={explanation}
          onChange={(e) => setExplanation(e.target.value)}
          className="passage-editor-input"
        />
      </div>

      <div className="passage-editor-actions">
        <button
          type="button"
          onClick={onCancel}
          className="btn-ghost passage-editor-cancel-btn"
        >
          Cancel
        </button>
        <button
          type="button"
          onClick={handleSaveClick}
          className="btn-primary passage-editor-save-btn"
        >
          Save
        </button>
      </div>
    </div>
  );
}

/**
 * PassageLinkedQuestionCard
 *
 * Renders an individual passage-linked question with its metadata strip,
 * difficulty badge, psychometric score, distractor traps, and expandable inline editor.
 */
export default function PassageLinkedQuestionCard({
  question,
  index,
  totalQuestions,
  isEditing,
  onToggleEdit,
  onSaveQuestion
}) {
  const trapInfo = getEffectiveTrapInfo(question);

  return (
    <div className="passage-linked-card">
      {/* Header Strip */}
      <div className="passage-linked-header">
        <div className="passage-linked-meta">
          <span className="passage-linked-num-badge">
            Q{index + 1} of {totalQuestions}
          </span>

          <span className={`badge ${getDifficultyBadgeClass(question.difficulty)}`}>
            {formatDifficulty(question.difficulty)}
          </span>

          {question.final_score && (
            <span className="badge badge-emerald">
              Score: {question.final_score}/100
            </span>
          )}

          {trapInfo?.label && (
            <span
              className="badge badge-purple"
              title={`Common Test Trap: ${trapInfo.label}`}
            >
              {trapInfo.label}
            </span>
          )}
        </div>

        <button
          type="button"
          onClick={onToggleEdit}
          className="btn-secondary passage-linked-edit-btn"
          title={isEditing ? 'Close editor' : 'Edit question text, choices, or explanation'}
        >
          {isEditing ? <X size={12} /> : <Edit3 size={12} color="var(--brand-primary)" />}
          <span>{isEditing ? 'Cancel' : 'Edit'}</span>
        </button>
      </div>

      {isEditing ? (
        <PassageInlineQuestionEditor
          question={question}
          onSave={onSaveQuestion}
          onCancel={onToggleEdit}
        />
      ) : (
        <>
          {/* Question Stem */}
          <div className="passage-linked-stem">
            {question.question_stem}
          </div>

          {/* Options A-D */}
          <div className="passage-linked-options">
            {question.options?.map((opt) => {
              const isCorrect = isCorrectOption(question, opt.id);

              return (
                <div
                  key={opt.id}
                  className={`passage-linked-option-row ${isCorrect ? 'correct' : ''}`}
                >
                  <span className={`passage-linked-option-letter ${isCorrect ? 'correct' : ''}`}>
                    {opt.id}.
                  </span>
                  <span className={`passage-linked-option-text ${isCorrect ? 'correct' : ''}`}>
                    {opt.text}
                  </span>
                  {isCorrect && (
                    <CheckCircle2
                      size={13}
                      color="var(--status-success)"
                      className="passage-linked-check-icon"
                    />
                  )}
                </div>
              );
            })}
          </div>

          {/* Pedagogical Explanation Preview */}
          {question.explanation && (
            <div className="passage-linked-explanation">
              <strong>
                Rationale &amp; Explanation:
              </strong>
              <p>{question.explanation}</p>
            </div>
          )}
        </>
      )}
    </div>
  );
}
