import React from 'react';
import {
  CheckCircle2,
  Trash2,
  Database,
  Sparkles,
  ChevronDown,
  ChevronUp,
  Image as ImageIcon,
  BookOpen,
  Tag,
  Target
} from 'lucide-react';
import { MCAT_SECTION_LABELS, formatDifficulty, getSectionBadgeClass } from '../../constants/mcat';
import { getEffectiveTrapInfo } from '../../utils';
import VisualStimulusViewer from '../question/VisualStimulusViewer';

function AiValidatedQuestionCard({
  question: q,
  index = 0,
  isSelected = false,
  onToggleSelect,
  isPassageExpanded = false,
  onTogglePassage,
  onOpenAudit,
  onMoveToBank,
  onDiscard,
  actionInProgress = false
}) {
  const hasPassage = Boolean(q.stimulus_text && q.stimulus_text.trim());
  const hasDiagram = Boolean(
    q.image_svg ||
    q.image_url ||
    q.stage_outcomes?.visual_stimulus?.image_svg ||
    q.stage_outcomes?.visual_stimulus?.image_url ||
    q.stage_outcomes?.passage_visual_stimulus?.image_svg ||
    q.stage_outcomes?.passage_visual_stimulus?.image_url
  );
  const trapInfo = getEffectiveTrapInfo(q);

  return (
    <div
      style={{
        background: 'var(--bg-surface)',
        border: isSelected ? '1.5px solid var(--brand-primary)' : '1px solid var(--border-light)',
        borderRadius: 'var(--radius-sm)',
        padding: '16px 18px',
        boxShadow: isSelected ? '0 0 0 1px var(--brand-primary)' : 'var(--shadow-xs)',
        transition: 'all var(--transition-fast)'
      }}
    >
      {/* Card Header */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: '10px',
          marginBottom: '10px',
          flexWrap: 'wrap'
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
          <input
            type="checkbox"
            checked={isSelected}
            onChange={() => onToggleSelect?.(q.id)}
            style={{ accentColor: 'var(--brand-primary)', cursor: 'pointer', width: '16px', height: '16px' }}
          />
          <span style={{ fontWeight: 800, fontSize: '0.85rem', color: 'var(--brand-primary)' }}>
            #{index + 1}
          </span>
          <span
            className={`badge ${getSectionBadgeClass(q.section)}`}
            style={{
              fontSize: '0.68rem',
              fontWeight: 700
            }}
          >
            {q.section_label || MCAT_SECTION_LABELS[q.section] || q.section}
          </span>
          <span
            style={{
              fontSize: '0.72rem',
              fontWeight: 600,
              padding: '2px 8px',
              borderRadius: 'var(--radius-xs)',
              background: 'var(--bg-surface-subtle)',
              color: 'var(--text-muted)'
            }}
          >
            {formatDifficulty(q.difficulty)}
          </span>
          {trapInfo?.label && (
            <span
              className="badge badge-purple"
              style={{
                fontSize: '0.675rem',
                padding: '1px 6px',
                display: 'inline-flex',
                alignItems: 'center',
                gap: '4px',
                background: 'var(--status-purple-bg)',
                border: '1px solid var(--status-purple-border)',
                color: 'var(--status-purple)'
              }}
              title={`Trap: ${trapInfo.label}`}
            >
              <Tag size={10} /> {trapInfo.label}
            </span>
          )}
          {q.aamc_skill && (
            <span
              className="badge badge-cyan"
              style={{ fontSize: '0.65rem', padding: '1px 6px' }}
              title={`AAMC Reasoning Skill: ${q.aamc_skill}`}
            >
              {q.aamc_skill}
            </span>
          )}
          {q.likely_mistake_pattern && (
            <span
              className="badge"
              style={{
                fontSize: '0.675rem',
                padding: '1px 6px',
                display: 'inline-flex',
                alignItems: 'center',
                gap: '4px',
                background: 'var(--status-warning-bg)',
                color: 'var(--status-warning)',
                border: '1px solid var(--status-warning-border)'
              }}
              title={`Mistake: ${q.likely_mistake_pattern}`}
            >
              <Target size={10} /> {q.likely_mistake_pattern}
            </span>
          )}
          {hasDiagram && (
            <span
              className="badge badge-purple"
              style={{ fontSize: '0.675rem', padding: '1px 6px', display: 'inline-flex', alignItems: 'center', gap: '4px' }}
              title="Contains Diagram"
            >
              <ImageIcon size={10} /> Diagram
            </span>
          )}
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
          {q.mcat_scaled_score && (
            <span
              className="badge"
              style={{
                background: 'var(--brand-light)',
                color: 'var(--brand-primary)',
                border: '1px solid var(--border-brand)',
                borderRadius: '12px',
                fontSize: '0.72rem',
                fontWeight: 800,
                padding: '2px 10px'
              }}
            >
              MCAT {q.mcat_scaled_score}
            </span>
          )}
          <span
            style={{
              background: 'var(--status-success-bg)',
              color: 'var(--status-success)',
              border: '1px solid var(--status-success-border)',
              borderRadius: '12px',
              fontSize: '0.72rem',
              fontWeight: 800,
              padding: '2px 10px',
              display: 'inline-flex',
              alignItems: 'center',
              gap: '5px'
            }}
          >
            <Sparkles size={11} />
            Score {q.final_score}/100
          </span>
        </div>
      </div>

      {/* Stimulus / Passage Snippet */}
      {hasPassage && (
        <div
          style={{
            background: 'var(--bg-surface-subtle)',
            border: '1px solid var(--border-light)',
            borderRadius: 'var(--radius-xs)',
            padding: '8px 12px',
            marginBottom: '12px',
            fontSize: '0.775rem'
          }}
        >
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              cursor: 'pointer',
              userSelect: 'none'
            }}
            onClick={() => onTogglePassage?.(q.id)}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontWeight: 600, color: 'var(--text-secondary)' }}>
              <BookOpen size={12} />
              <span>Reading Passage ({q.stimulus_text.split(/\s+/).length} words)</span>
            </div>
            <button
              type="button"
              className="btn-secondary"
              style={{ padding: '2px 6px', fontSize: '0.675rem' }}
            >
              {isPassageExpanded ? <ChevronUp size={11} /> : <ChevronDown size={11} />}
              <span style={{ marginLeft: '3px' }}>{isPassageExpanded ? 'Hide' : 'View'}</span>
            </button>
          </div>

          {isPassageExpanded && (
            <div style={{ marginTop: '8px' }}>
              <div
                style={{
                  color: 'var(--text-primary)',
                  fontFamily: 'var(--font-serif)',
                  fontSize: '0.85rem',
                  lineHeight: 1.6,
                  whiteSpace: 'pre-wrap',
                  maxHeight: '260px',
                  overflowY: 'auto'
                }}
              >
                {q.stimulus_text}
              </div>

              {/* Embedded Visual Stimulus Diagram */}
              {hasDiagram && (
                <div style={{ marginTop: '10px', borderTop: '1px solid var(--border-light)', paddingTop: '10px' }}>
                  <VisualStimulusViewer question={q} compact={false} />
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* Visual Stimulus Diagram / Image for standalone questions (without passage) */}
      {!hasPassage && hasDiagram && (
        <div style={{ marginBottom: '12px' }}>
          <VisualStimulusViewer question={q} compact={false} />
        </div>
      )}

      {/* Question Stem */}
      <div
        style={{
          fontSize: '0.875rem',
          fontWeight: 600,
          color: 'var(--text-primary)',
          lineHeight: 1.45,
          marginBottom: '12px'
        }}
      >
        {q.question_stem}
      </div>

      {/* 4 Options Grid/List */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr', gap: '6px', marginBottom: '14px' }}>
        {(q.options || []).map((opt) => {
          const isCorrect =
            (q.correct_answer_ids && q.correct_answer_ids.includes(opt.id)) ||
            q.correct_answer_id === opt.id;

          return (
            <div
              key={opt.id}
              style={{
                display: 'flex',
                alignItems: 'flex-start',
                gap: '8px',
                padding: '6px 10px',
                borderRadius: 'var(--radius-xs)',
                background: isCorrect ? 'var(--status-success-bg)' : 'var(--bg-surface-subtle)',
                border: isCorrect ? '1px solid var(--status-success-border)' : '1px solid var(--border-light)',
                fontSize: '0.78rem'
              }}
            >
              <span
                style={{
                  fontWeight: 800,
                  color: isCorrect ? 'var(--status-success)' : 'var(--text-muted)',
                  minWidth: '18px'
                }}
              >
                {opt.id}.
              </span>
              <span
                style={{
                  color: isCorrect ? 'var(--text-primary)' : 'var(--text-secondary)',
                  fontWeight: isCorrect ? 600 : 400,
                  flex: 1
                }}
              >
                {opt.text}
              </span>
              {isCorrect && (
                <span
                  style={{
                    fontSize: '0.675rem',
                    fontWeight: 700,
                    color: 'var(--status-success)',
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: '4px',
                    marginLeft: 'auto'
                  }}
                >
                  <CheckCircle2 size={12} /> Correct
                </span>
              )}
            </div>
          );
        })}
      </div>

      {/* Card Footer: Metadata Tags & Action Buttons */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: '12px',
          paddingTop: '10px',
          borderTop: '1px solid var(--border-light)',
          flexWrap: 'wrap'
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
          <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>
            Subtopic: <strong>{q.subtopic || 'General'}</strong>
          </span>
          {q.primary_trap && (
            <span
              style={{
                fontSize: '0.68rem',
                padding: '1px 6px',
                background: 'var(--bg-surface-subtle)',
                borderRadius: '4px',
                color: 'var(--text-secondary)'
              }}
            >
              Common Trap: {q.primary_trap}
            </span>
          )}
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          {onOpenAudit && (
            <button
              type="button"
              onClick={() => onOpenAudit(q)}
              className="btn-secondary"
              style={{ padding: '5px 10px', fontSize: '0.74rem' }}
            >
              Quality Review
            </button>
          )}

          <button
            type="button"
            onClick={() => onDiscard?.(q)}
            disabled={actionInProgress}
            className="btn-secondary"
            style={{
              padding: '5px 10px',
              fontSize: '0.74rem',
              color: 'var(--status-danger)'
            }}
            title="Discard question"
          >
            <Trash2 size={12} />
            <span style={{ marginLeft: '4px' }}>Discard</span>
          </button>

          <button
            type="button"
            onClick={() => onMoveToBank?.(q)}
            disabled={actionInProgress}
            className="btn-primary"
            style={{
              padding: '5px 14px',
              fontSize: '0.74rem',
              display: 'inline-flex',
              alignItems: 'center',
              gap: '5px',
              background: 'var(--status-success)',
              borderColor: 'var(--status-success)'
            }}
          >
            <Database size={12} />
            <span>Save to Question Bank</span>
          </button>
        </div>
      </div>
    </div>
  );
}

export default React.memo(AiValidatedQuestionCard);
