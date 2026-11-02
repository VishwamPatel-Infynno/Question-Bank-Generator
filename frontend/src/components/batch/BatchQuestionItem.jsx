import React, { useState } from 'react';
import {
  CheckCircle2,
  Image as ImageIcon,
  Sparkles,
  XCircle,
  AlertCircle,
  Database,
  Layers,
  BookOpen,
  ChevronDown,
  ChevronUp,
  Trash2,
  RotateCcw
} from 'lucide-react';
import VisualStimulusViewer from '../question/VisualStimulusViewer';

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

  // Determine lifecycle status
  let status = question.status;
  const finalScore = question.final_score ?? 95;
  if (!status) {
    if (finalScore > 90) status = 'ai_validated';
    else if (finalScore > 85) status = 'batch_only';
    else status = 'below_threshold';
  }

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
                background: 'rgba(239, 68, 68, 0.12)',
                color: 'var(--status-danger, #ef4444)',
                border: '1px solid rgba(239, 68, 68, 0.3)',
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
        <div
          style={{
            marginBottom: '8px',
            borderRadius: 'var(--radius-xs)',
            border: '1px solid var(--border-light)',
            overflow: 'hidden',
            background: 'var(--bg-surface)'
          }}
        >
          <div
            style={{
              padding: '6px 10px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              background: 'var(--bg-surface-subtle)',
              borderBottom: isPassageExpanded ? '1px solid var(--border-light)' : 'none'
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <BookOpen size={13} style={{ color: 'var(--brand-primary)' }} />
              <span style={{ fontWeight: 600, fontSize: '0.75rem', color: 'var(--text-primary)' }}>
                Reading Passage
              </span>
              <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>
                ({question.stimulus_text.trim().split(/\s+/).length} words)
              </span>
            </div>
            <button
              type="button"
              onClick={() => setIsPassageExpanded((prev) => !prev)}
              className="btn-secondary"
              style={{
                padding: '2px 7px',
                fontSize: '0.7rem',
                gap: '4px',
                display: 'inline-flex',
                alignItems: 'center'
              }}
            >
              {isPassageExpanded ? (
                <>
                  <ChevronUp size={12} />
                  <span>Hide Passage</span>
                </>
              ) : (
                <>
                  <ChevronDown size={12} />
                  <span>View Passage</span>
                </>
              )}
            </button>
          </div>

          {isPassageExpanded && (
            <div
              style={{
                padding: '10px 12px',
                fontSize: '0.78rem',
                lineHeight: 1.6,
                color: 'var(--text-secondary)',
                maxHeight: '320px',
                overflowY: 'auto',
                whiteSpace: 'pre-wrap',
                background: 'var(--bg-canvas)'
              }}
            >
              {hasDiagram && (
                <div style={{ marginBottom: '10px' }}>
                  <VisualStimulusViewer question={question} />
                </div>
              )}
              {question.stimulus_text}
            </div>
          )}
        </div>
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
      <div style={{ display: 'flex', flexDirection: 'column', gap: '4px', marginBottom: '8px' }}>
        {(question.options || []).map((opt) => {
          const isCorrect =
            (question.correct_answer_ids && question.correct_answer_ids.includes(opt.id)) ||
            question.correct_answer_id === opt.id;
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

      {/* Question Tools */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          paddingTop: '6px',
          borderTop: '1px dashed var(--border-light)'
        }}
      >
        <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>
          {question.aamc_skill || question.primary_trap || 'MCAT Standard'}
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          {question.is_deleted && question.status !== 'discarded' && onRestoreQuestion && (
            <button
              type="button"
              onClick={() => onRestoreQuestion(question)}
              className="btn-primary"
              style={{
                padding: '3px 9px',
                fontSize: '0.7rem',
                display: 'inline-flex',
                alignItems: 'center',
                gap: '4px',
                background: 'rgba(16, 185, 129, 0.15)',
                color: 'var(--status-success, #10b981)',
                border: '1px solid rgba(16, 185, 129, 0.3)'
              }}
              title="Restore this question back to Question Bank"
            >
              <RotateCcw size={10} />
              <span>Restore to Bank</span>
            </button>
          )}

          {!question.is_deleted && status === 'batch_only' && onSaveToBank && (
            <button
              type="button"
              onClick={() => onSaveToBank(question)}
              className="btn-primary"
              style={{
                padding: '3px 9px',
                fontSize: '0.7rem',
                display: 'inline-flex',
                alignItems: 'center',
                gap: '4px'
              }}
              title="Save question directly to Question Bank"
            >
              <Database size={10} />
              <span>Save to Question Bank</span>
            </button>
          )}

          {!question.is_deleted && status === 'ai_validated' && onNavigateToValidated && (
            <button
              type="button"
              onClick={onNavigateToValidated}
              className="btn-primary"
              style={{ padding: '2px 8px', fontSize: '0.7rem', display: 'inline-flex', alignItems: 'center', gap: '4px' }}
              title="Review in Ready for Review screen"
            >
              <Sparkles size={10} />
              <span>Review Question</span>
            </button>
          )}

          {!question.is_deleted && status === 'in_bank' && onNavigateToBank && (
            <button
              type="button"
              onClick={onNavigateToBank}
              className="btn-secondary"
              style={{ padding: '2px 8px', fontSize: '0.7rem', display: 'inline-flex', alignItems: 'center', gap: '4px' }}
              title="View in Question Bank"
            >
              <Database size={10} />
              <span>In Question Bank</span>
            </button>
          )}

          {onOpenAudit && (
            <button
              type="button"
              onClick={() => onOpenAudit(question)}
              className="btn-secondary"
              style={{ padding: '2px 8px', fontSize: '0.7rem' }}
            >
              Quality Review
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
