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
  const isBelowThreshold = status === 'below_threshold' || finalScore <= 85;

  return (
    <div
      style={{
        background: isBelowThreshold ? 'var(--bg-surface-subtle)' : 'var(--bg-canvas)',
        border: isBelowThreshold
          ? '1px dashed var(--border-medium)'
          : '1px solid var(--border-light)',
        borderRadius: 'var(--radius-xs)',
        padding: '10px 12px',
        fontSize: '0.78rem',
        opacity: isBelowThreshold ? 0.85 : 1,
        transition: 'all var(--transition-fast)'
      }}
    >
      {/* Question Header: Number, Status badge, Score, Diagram pill */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          marginBottom: '8px',
          flexWrap: 'wrap',
          gap: '6px'
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
          <span style={{ fontWeight: 800, color: 'var(--brand-primary)', fontSize: '0.75rem' }}>
            Question {index + 1}
          </span>

          {/* Status Badge */}
          {question.is_deleted && question.status !== 'discarded' ? (
            <span
              style={{
                fontSize: '0.675rem',
                padding: '2px 8px',
                borderRadius: '10px',
                background: 'var(--status-danger-bg)',
                color: 'var(--status-danger)',
                border: '1px solid var(--status-danger-border)',
                fontWeight: 700,
                display: 'inline-flex',
                alignItems: 'center',
                gap: '4px'
              }}
            >
              <Trash2 size={11} /> Deleted from Bank
            </span>
          ) : (
            <>
              {status === 'in_bank' && (
                <span
                  style={{
                    fontSize: '0.675rem',
                    padding: '2px 8px',
                    borderRadius: '10px',
                    background: 'rgba(16, 185, 129, 0.12)',
                    color: 'var(--status-success)',
                    border: '1px solid rgba(16, 185, 129, 0.3)',
                    fontWeight: 700,
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: '4px'
                  }}
                >
                  <CheckCircle2 size={11} /> In Question Bank
                </span>
              )}

              {status === 'ai_validated' && (
                <span
                  style={{
                    fontSize: '0.675rem',
                    padding: '2px 8px',
                    borderRadius: '10px',
                    background: 'rgba(79, 48, 185, 0.12)',
                    color: 'var(--brand-primary)',
                    border: '1px solid rgba(79, 48, 185, 0.3)',
                    fontWeight: 700,
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: '4px'
                  }}
                >
                  <Sparkles size={11} /> Ready for Review
                </span>
              )}

              {status === 'batch_only' && (
                <span
                  style={{
                    fontSize: '0.675rem',
                    padding: '2px 8px',
                    borderRadius: '10px',
                    background: 'rgba(51, 90, 207, 0.12)',
                    color: 'var(--brand-primary)',
                    border: '1px solid rgba(51, 90, 207, 0.3)',
                    fontWeight: 700,
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: '4px'
                  }}
                >
                  <Layers size={11} /> Good Quality
                </span>
              )}

              {status === 'discarded' && (
                <span
                  style={{
                    fontSize: '0.675rem',
                    padding: '2px 8px',
                    borderRadius: '10px',
                    background: 'rgba(244, 63, 94, 0.12)',
                    color: 'var(--status-danger)',
                    border: '1px solid rgba(244, 63, 94, 0.3)',
                    fontWeight: 700,
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: '4px'
                  }}
                >
                  <XCircle size={11} /> Discarded
                </span>
              )}

              {status === 'below_threshold' && (
                <span
                  style={{
                    fontSize: '0.675rem',
                    padding: '2px 8px',
                    borderRadius: '10px',
                    background: 'var(--status-warning-bg, rgba(245, 158, 11, 0.12))',
                    color: 'var(--status-warning, #d97706)',
                    border: '1px solid var(--status-warning-border, rgba(245, 158, 11, 0.3))',
                    fontWeight: 700,
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: '4px'
                  }}
                >
                  <AlertCircle size={11} /> Needs Polish (&le;85)
                </span>
              )}
            </>
          )}
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          <span
            className="badge"
            style={{
              fontSize: '0.65rem',
              padding: '1px 6px',
              background:
                finalScore > 90
                  ? 'rgba(16, 185, 129, 0.12)'
                  : finalScore > 85
                    ? 'rgba(51, 90, 207, 0.12)'
                    : 'var(--status-warning-bg, rgba(245, 158, 11, 0.12))',
              color:
                finalScore > 90
                  ? 'var(--status-success)'
                  : finalScore > 85
                    ? 'var(--brand-primary)'
                    : 'var(--status-warning, #d97706)',
              border:
                finalScore > 90
                  ? '1px solid rgba(16, 185, 129, 0.25)'
                  : finalScore > 85
                    ? '1px solid rgba(51, 90, 207, 0.25)'
                    : '1px solid var(--status-warning-border, rgba(245, 158, 11, 0.25))',
              fontWeight: 700
            }}
          >
            Score {finalScore}/100
          </span>
          {hasDiagram && (
            <span
              className="badge-minimal"
              style={{
                fontSize: '0.65rem',
                padding: '1px 6px',
                color: 'var(--brand-primary)',
                background: 'rgba(79, 48, 185, 0.08)',
                border: '1px solid rgba(79, 48, 185, 0.25)',
                borderRadius: '9999px',
                display: 'inline-flex',
                alignItems: 'center',
                gap: '3px'
              }}
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
        <div style={{ marginBottom: '8px' }}>
          <VisualStimulusViewer question={question} />
        </div>
      )}

      {/* Question Stem */}
      <div
        style={{
          color: 'var(--text-primary)',
          lineHeight: 1.4,
          fontWeight: 500,
          marginBottom: '8px'
        }}
      >
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
