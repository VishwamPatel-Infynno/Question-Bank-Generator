import React from 'react';
import { CheckCircle2 } from 'lucide-react';

const EMPTY_OPTIONS = [];
const EMPTY_IDS = [];

/**
 * BatchQuestionOptionsList - Displays multiple choice options with correct answer highlighting.
 */
export default function BatchQuestionOptionsList({
  options = EMPTY_OPTIONS,
  correctAnswerId,
  correctAnswerIds = EMPTY_IDS
}) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '4px', marginBottom: '8px' }}>
      {options.map((opt) => {
        const isCorrect =
          (correctAnswerIds && correctAnswerIds.includes(opt.id)) ||
          correctAnswerId === opt.id;
        return (
          <div
            key={opt.id}
            style={{
              display: 'flex',
              alignItems: 'flex-start',
              gap: '6px',
              padding: '4px 8px',
              borderRadius: 'var(--radius-xs)',
              background: isCorrect ? 'rgba(16, 185, 129, 0.08)' : 'var(--bg-surface-subtle)',
              border: isCorrect ? '1px solid rgba(16, 185, 129, 0.3)' : '1px solid transparent',
              fontSize: '0.74rem'
            }}
          >
            <span
              style={{
                fontWeight: 700,
                color: isCorrect ? 'var(--status-success)' : 'var(--text-muted)',
                minWidth: '16px'
              }}
            >
              {opt.id}.
            </span>
            <span style={{ color: isCorrect ? 'var(--text-primary)' : 'var(--text-secondary)' }}>
              {opt.text}
            </span>
            {isCorrect && (
              <CheckCircle2
                size={12}
                style={{ color: 'var(--status-success)', marginLeft: 'auto', flexShrink: 0 }}
              />
            )}
          </div>
        );
      })}
    </div>
  );
}
