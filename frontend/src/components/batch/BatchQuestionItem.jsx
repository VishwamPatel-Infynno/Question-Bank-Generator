import React, { useState } from 'react';
import {
  CheckCircle2,
  Image as ImageIcon,
  Sparkles,
  XCircle,
  AlertCircle,
  Layers,
  Trash2
} from 'lucide-react';
import VisualStimulusViewer from '../question/VisualStimulusViewer';
import BatchQuestionPassageDrawer from './BatchQuestionPassageDrawer';
import BatchQuestionOptionsList from './BatchQuestionOptionsList';
import BatchQuestionActions from './BatchQuestionActions';
import { resolveQuestionStatus } from '../../utils';
import { QUESTION_STATUS, SCORE_CUTOFFS } from '../../constants';

/**
 * BatchQuestionItem - Renders an individual question item accordion within a batch set drawer.
 */
export default function BatchQuestionItem({
  question,
  index = 0,
  onNavigateToBank,
  onNavigateToValidated,
  onOpenAudit,
  onSaveToBank,
  onRestoreQuestion
}) {
  const [isPassageExpanded, setIsPassageExpanded] = useState(false);

  if (!question) return null;

  const hasPassage = Boolean(question.stimulus_text && question.stimulus_text.trim().length > 0);
  const hasDiagram = Boolean(
    question.image_url ||
      question.image_svg ||
      question.stage_outcomes?.visual_stimulus?.image_url ||
      question.stage_outcomes?.visual_stimulus?.image_svg ||
      question.stage_outcomes?.passage_visual_stimulus?.image_url ||
      question.stage_outcomes?.passage_visual_stimulus?.image_svg
  );

  const status = resolveQuestionStatus(question);
  const finalScore = question.final_score ?? 95;
  const isBelowThreshold = status === QUESTION_STATUS.BELOW_THRESHOLD || finalScore <= SCORE_CUTOFFS.batchAbove;

  const scoreTierClass =
    finalScore > SCORE_CUTOFFS.aiValidatedAbove ? 'high' : finalScore > SCORE_CUTOFFS.batchAbove ? 'mid' : 'low';

  return (
    <div className={`batch-qitem ${isBelowThreshold ? 'below-threshold' : ''}`}>
      {/* Question Header: Number, Status badge, Score, Diagram pill */}
      <div className="batch-qitem-top-row">
        <div className="batch-qitem-top-left">
          <span className="batch-qitem-number">
            Question {index + 1}
          </span>

          {/* Status Badge */}
          {question.is_deleted && question.status !== QUESTION_STATUS.DISCARDED ? (
            <span className="batch-qitem-tag deleted">
              <Trash2 size={11} /> Deleted from Bank
            </span>
          ) : (
            <>
              {status === QUESTION_STATUS.IN_BANK && (
                <span className="batch-qitem-tag in-bank">
                  <CheckCircle2 size={11} /> In Question Bank
                </span>
              )}

              {status === QUESTION_STATUS.AI_VALIDATED && (
                <span className="batch-qitem-tag validated">
                  <Sparkles size={11} /> Ready for Review
                </span>
              )}

              {status === QUESTION_STATUS.BATCH_ONLY && (
                <span className="batch-qitem-tag batch-only">
                  <Layers size={11} /> Good Quality
                </span>
              )}

              {status === QUESTION_STATUS.DISCARDED && (
                <span className="batch-qitem-tag discarded">
                  <XCircle size={11} /> Discarded
                </span>
              )}

              {status === QUESTION_STATUS.BELOW_THRESHOLD && (
                <span className="batch-qitem-tag below">
                  <AlertCircle size={11} /> Needs Polish (&le;85)
                </span>
              )}
            </>
          )}
        </div>

        <div className="batch-qitem-top-right">
          <span className={`badge batch-qitem-score-badge ${scoreTierClass}`}>
            Score {finalScore}/100
          </span>
          {hasDiagram && (
            <span
              className="badge-minimal batch-qitem-diagram-pill"
              title={hasPassage ? 'Has passage visual diagram' : 'Has visual diagram'}
            >
              <ImageIcon size={10} /> {hasPassage ? 'Passage Diagram' : 'Diagram'}
            </span>
          )}
        </div>
      </div>

      {/* Passage Display Drawer */}
      {hasPassage && (
        <BatchQuestionPassageDrawer
          question={question}
          hasDiagram={hasDiagram}
          isExpanded={isPassageExpanded}
          onToggle={() => setIsPassageExpanded((prev) => !prev)}
        />
      )}

      {/* Standalone question visual stimulus (when not embedded in a passage) */}
      {!hasPassage && hasDiagram && (
        <div className="batch-qitem-stimulus-box">
          <VisualStimulusViewer question={question} />
        </div>
      )}

      {/* Question Stem */}
      <div className="batch-qitem-stem">
        {question.question_stem}
      </div>

      {/* Options List */}
      <BatchQuestionOptionsList
        options={question.options || []}
        correctAnswerId={question.correct_answer_id}
        correctAnswerIds={question.correct_answer_ids}
      />

      {/* Question Action Tools */}
      <BatchQuestionActions
        question={question}
        status={status}
        onNavigateToBank={onNavigateToBank}
        onNavigateToValidated={onNavigateToValidated}
        onOpenAudit={onOpenAudit}
        onSaveToBank={onSaveToBank}
        onRestoreQuestion={onRestoreQuestion}
      />
    </div>
  );
}
