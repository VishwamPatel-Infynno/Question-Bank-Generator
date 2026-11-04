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
    <div className="batch-qitem-options-list">
      {options.map((opt) => {
        const isCorrect =
          (correctAnswerIds && correctAnswerIds.includes(opt.id)) ||
          correctAnswerId === opt.id;
        return (
          <div
            key={opt.id}
            className={`batch-qitem-option-row ${isCorrect ? 'correct' : ''}`}
          >
            <span className={`batch-qitem-option-letter ${isCorrect ? 'correct' : ''}`}>
              {opt.id}.
            </span>
            <span className={`batch-qitem-option-body ${isCorrect ? 'correct' : ''}`}>
              {opt.text}
            </span>
            {isCorrect && (
              <CheckCircle2 size={12} className="batch-qitem-option-check" />
            )}
          </div>
        );
      })}
    </div>
  );
}
