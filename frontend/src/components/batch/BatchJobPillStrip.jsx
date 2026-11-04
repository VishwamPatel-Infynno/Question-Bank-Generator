import React from 'react';
import { Check } from 'lucide-react';
import { resolveQuestionStatus } from '../../utils';

const EMPTY_QUESTIONS = [];

/**
 * BatchJobPillStrip - Visual progress strip showing done, in-bank, drafting, or pending states for questions.
 */
export default function BatchJobPillStrip({
  jobId = 'job',
  jobNumber = 1,
  targetCount = 5,
  visibleQuestions = EMPTY_QUESTIONS,
  isJobRunning = false
}) {
  return (
    <div className="job-q-pill-strip" role="group" aria-label={`Question progress for Set ${jobNumber}`}>
      {Array.from({ length: targetCount }, (_, i) => ({
        slotNum: i + 1,
        slotKey: `${jobId}-slot-${i + 1}`
      })).map((slot) => {
        const qNum = slot.slotNum;
        const matchedQ = visibleQuestions[qNum - 1];
        if (matchedQ) {
          const st = resolveQuestionStatus(matchedQ);
          const score = matchedQ.final_score ?? 95;
          const isBank = st === 'in_bank';
          return (
            <span
              key={matchedQ.id || slot.slotKey}
              className={`job-q-pill ${isBank ? 'in-bank' : 'done'}`}
              title={`Question ${qNum}: Score ${score}/100 • ${isBank ? 'In Question Bank' : 'Ready for Review'}`}
            >
              <Check size={10} />
              <span>Q{qNum} ({score})</span>
            </span>
          );
        }
        if (isJobRunning && qNum - 1 === visibleQuestions.length) {
          return (
            <span
              key={`active-${slot.slotKey}`}
              className="job-q-pill active"
              title={`Question ${qNum}: Currently generating passage, stem & distractors`}
            >
              <span
                style={{
                  width: '4px',
                  height: '4px',
                  borderRadius: '50%',
                  background: 'var(--brand-primary)',
                  animation: 'pulse 1.2s infinite'
                }}
              />
              <span>Q{qNum} drafting</span>
            </span>
          );
        }
        return (
          <span
            key={`pending-${slot.slotKey}`}
            className="job-q-pill pending"
            title={`Question ${qNum}: Pending in set`}
          >
            <span>Q{qNum}</span>
          </span>
        );
      })}
    </div>
  );
}
