import React, { useState } from 'react';
import { CheckCircle2, Edit3, X } from 'lucide-react';
import { formatDifficulty, getDifficultyBadgeClass } from '../../constants/mcat';
import { getEffectiveTrapInfo } from '../../utils';

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
    <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', paddingTop: '6px' }}>
      <div>
        <label
          style={{
            display: 'block',
            fontSize: '0.7rem',
            color: 'var(--text-secondary)',
            marginBottom: '3px',
            fontWeight: 600
          }}
        >
          Question Text
        </label>
        <textarea
          rows={3}
          value={stem}
          onChange={(e) => setStem(e.target.value)}
          style={{
            width: '100%',
            padding: '6px 8px',
            fontSize: '0.8rem',
            borderRadius: 'var(--radius-sm)',
            border: '1px solid var(--border-light)',
            background: 'var(--bg-surface-elevated)',
            color: 'var(--text-primary)'
          }}
        />
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
        <label style={{ fontSize: '0.7rem', color: 'var(--text-secondary)', fontWeight: 600 }}>
          Options &amp; Correct Answer Key
        </label>
        {options.map((opt, idx) => (
          <div key={opt.id} style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <button
              type="button"
              onClick={() => setCorrectId(opt.id)}
              style={{
                width: '26px',
                height: '26px',
                borderRadius: 'var(--radius-sm)',
                border:
                  correctId === opt.id
                    ? '2px solid var(--status-success)'
                    : '1px solid var(--border-light)',
                background:
                  correctId === opt.id
                    ? 'rgba(16, 185, 129, 0.15)'
                    : 'var(--bg-surface-elevated)',
                color:
                  correctId === opt.id
                    ? 'var(--status-success)'
                    : 'var(--text-secondary)',
                fontWeight: 700,
                fontSize: '0.75rem',
                cursor: 'pointer'
              }}
              title={`Mark Option ${opt.id} as Correct Answer`}
            >
              {opt.id}
            </button>
            <input
              type="text"
              value={opt.text}
              onChange={(e) => handleOptionChange(idx, e.target.value)}
              style={{
                flex: 1,
                padding: '5px 8px',
                fontSize: '0.78rem',
                borderRadius: 'var(--radius-sm)',
                border: '1px solid var(--border-light)',
                background: 'var(--bg-surface-elevated)',
                color: 'var(--text-primary)'
              }}
            />
          </div>
        ))}
      </div>

      <div>
        <label
          style={{
            display: 'block',
            fontSize: '0.7rem',
            color: 'var(--text-secondary)',
            marginBottom: '3px',
            fontWeight: 600
          }}
        >
          Explanation &amp; Distractor Traps
        </label>
        <textarea
          rows={3}
          value={explanation}
          onChange={(e) => setExplanation(e.target.value)}
          style={{
            width: '100%',
            padding: '6px 8px',
            fontSize: '0.78rem',
            borderRadius: 'var(--radius-sm)',
            border: '1px solid var(--border-light)',
            background: 'var(--bg-surface-elevated)',
            color: 'var(--text-primary)'
          }}
        />
      </div>

      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'flex-end',
          gap: '6px',
          marginTop: '4px'
        }}
      >
        <button
          type="button"
          onClick={onCancel}
          className="btn-ghost"
          style={{ padding: '4px 8px', fontSize: '0.72rem' }}
        >
          Cancel
        </button>
        <button
          type="button"
          onClick={handleSaveClick}
          className="btn-primary"
          style={{ padding: '4px 10px', fontSize: '0.72rem' }}
        >
          Save Question Updates
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
    <div
      style={{
        background: 'var(--bg-surface)',
        border: '1px solid var(--border-light)',
        borderRadius: 'var(--radius-md)',
        padding: '16px',
        display: 'flex',
        flexDirection: 'column',
        gap: '12px'
      }}
    >
      {/* Header Strip */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span
            style={{
              background: 'var(--bg-surface-elevated)',
              border: '1px solid var(--border-light)',
              borderRadius: 'var(--radius-sm)',
              padding: '2px 8px',
              fontSize: '0.72rem',
              fontWeight: 700,
              color: 'var(--text-primary)'
            }}
          >
            Q{index + 1} of {totalQuestions}
          </span>

          <span
            className={`badge ${getDifficultyBadgeClass(question.difficulty)}`}
            style={{ fontSize: '0.64rem' }}
          >
            {formatDifficulty(question.difficulty)}
          </span>

          {question.final_score && (
            <span className="badge badge-emerald" style={{ fontSize: '0.64rem' }}>
              Score: {question.final_score}/100
            </span>
          )}

          {trapInfo?.label && (
            <span
              className="badge badge-purple"
              style={{ fontSize: '0.64rem' }}
              title={`Common Test Trap: ${trapInfo.label}`}
            >
              {trapInfo.label}
            </span>
          )}
        </div>

        <button
          type="button"
          onClick={onToggleEdit}
          className="btn-secondary"
          style={{
            padding: '4px 8px',
            fontSize: '0.72rem',
            display: 'flex',
            alignItems: 'center',
            gap: '4px'
          }}
          title={isEditing ? 'Close editor' : 'Edit question text, choices, or explanation'}
        >
          {isEditing ? <X size={12} /> : <Edit3 size={12} color="var(--brand-primary)" />}
          <span>{isEditing ? 'Cancel' : 'Edit Question'}</span>
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
          <div
            style={{
              fontSize: '0.86rem',
              fontWeight: 600,
              color: 'var(--text-primary)',
              lineHeight: 1.45
            }}
          >
            {question.question_stem}
          </div>

          {/* Options A-D */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
            {question.options?.map((opt) => {
              const isCorrect =
                String(opt.id).toUpperCase() === String(question.correct_answer_id).toUpperCase() ||
                (question.correct_answer_ids && question.correct_answer_ids.includes(opt.id));

              return (
                <div
                  key={opt.id}
                  style={{
                    padding: '8px 10px',
                    borderRadius: 'var(--radius-sm)',
                    border: isCorrect
                      ? '1px solid var(--status-success)'
                      : '1px solid var(--border-light)',
                    background: isCorrect
                      ? 'rgba(16, 185, 129, 0.05)'
                      : 'var(--bg-surface-elevated)',
                    display: 'flex',
                    alignItems: 'flex-start',
                    gap: '8px',
                    fontSize: '0.78rem'
                  }}
                >
                  <span
                    style={{
                      fontWeight: 700,
                      color: isCorrect ? 'var(--status-success)' : 'var(--text-secondary)',
                      minWidth: '18px'
                    }}
                  >
                    {opt.id}.
                  </span>
                  <span
                    style={{
                      flex: 1,
                      color: isCorrect ? 'var(--text-primary)' : 'var(--text-secondary)'
                    }}
                  >
                    {opt.text}
                  </span>
                  {isCorrect && (
                    <CheckCircle2
                      size={13}
                      color="var(--status-success)"
                      style={{ marginTop: '2px' }}
                    />
                  )}
                </div>
              );
            })}
          </div>

          {/* Pedagogical Explanation Preview */}
          {question.explanation && (
            <div
              style={{
                padding: '10px 12px',
                borderRadius: 'var(--radius-sm)',
                background: 'var(--bg-surface-subtle)',
                border: '1px solid var(--border-light)',
                fontSize: '0.75rem',
                color: 'var(--text-secondary)',
                lineHeight: 1.45
              }}
            >
              <strong
                style={{
                  color: 'var(--text-primary)',
                  display: 'block',
                  marginBottom: '3px'
                }}
              >
                Rationale &amp; Explanation:
              </strong>
              <p style={{ margin: 0, whiteSpace: 'pre-line' }}>{question.explanation}</p>
            </div>
          )}
        </>
      )}
    </div>
  );
}

