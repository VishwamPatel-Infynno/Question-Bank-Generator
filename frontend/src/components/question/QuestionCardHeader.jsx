import React from 'react';
import { Award, Edit3, ShieldCheck, Image as ImageIcon, AlertTriangle } from 'lucide-react';
import { formatDifficulty, getDifficultyBadgeClass, getSectionBadgeClass } from '../../constants/mcat';

/**
 * QuestionCardHeader
 *
 * Header metadata strip for QuestionCard displaying status, section, difficulty,
 * diagram status, cognitive traps, overall score, and quick action buttons.
 */
export default function QuestionCardHeader({
  question,
  isSaved = false,
  hasImage = false,
  effectiveTrapInfo = null,
  onOpenAudit = null,
  isEditing = false,
  onToggleEditing = null
}) {
  if (!question) return null;

  const diffBadgeClass = getDifficultyBadgeClass(question.difficulty);
  const diffLabel = formatDifficulty(question.difficulty);

  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        flexWrap: 'wrap',
        gap: '12px',
        paddingBottom: '14px',
        borderBottom: '1px solid var(--border-light)'
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
        {isSaved ? (
          <span style={{ display: 'inline-flex', alignItems: 'center', gap: '5px', fontSize: '0.725rem', fontWeight: 600, color: 'var(--status-success)' }}>
            <span style={{ width: 6, height: 6, borderRadius: '50%', background: 'var(--status-success)' }} />
            Saved
          </span>
        ) : (
          <span style={{ display: 'inline-flex', alignItems: 'center', gap: '5px', fontSize: '0.725rem', fontWeight: 600, color: 'var(--status-warning)' }}>
            <span style={{ width: 6, height: 6, borderRadius: '50%', background: 'var(--status-warning)' }} />
            Ready
          </span>
        )}

        <span style={{ color: 'var(--border-medium)' }}>|</span>

        <span className={`badge ${getSectionBadgeClass(question.section)}`} style={{ fontSize: '0.68rem', fontWeight: 700 }}>
          {question.section_label || question.section}
        </span>

        <span className={`badge ${diffBadgeClass}`} style={{ fontSize: '0.65rem', textTransform: 'capitalize' }}>
          {diffLabel}
        </span>

        {hasImage && (
          <span className="badge badge-purple" style={{ fontSize: '0.675rem', display: 'inline-flex', alignItems: 'center', gap: '4px' }}>
            <ImageIcon size={11} /> Diagram
          </span>
        )}

        {effectiveTrapInfo?.label && (
          <span
            className="badge badge-purple"
            style={{
              fontSize: '0.675rem',
              display: 'inline-flex',
              alignItems: 'center',
              gap: '4px',
              background: 'rgba(139, 92, 246, 0.12)',
              border: '1px solid rgba(139, 92, 246, 0.3)',
              color: 'var(--status-purple)'
            }}
            title={`Primary Cognitive Trap: ${effectiveTrapInfo.label}`}
          >
            <AlertTriangle size={11} /> {effectiveTrapInfo.label}
          </span>
        )}

        <span className="badge badge-emerald" style={{ fontSize: '0.675rem', fontWeight: 600 }}>
          <Award size={11} /> {question.final_score}/100
        </span>
      </div>

      {/* Top Actions */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
        {onOpenAudit && (
          <button
            type="button"
            onClick={() => onOpenAudit(question)}
            className="btn-secondary"
            style={{ padding: '5px 10px', fontSize: '0.75rem' }}
            title="Open quality breakdown modal"
          >
            <ShieldCheck size={12} color="var(--brand-primary)" />
            <span>Quality Review</span>
          </button>
        )}

        {onToggleEditing && (
          <button
            type="button"
            onClick={onToggleEditing}
            className="btn-secondary"
            style={{ padding: '5px 10px', fontSize: '0.75rem' }}
            title="Edit question text (Press E)"
          >
            <Edit3 size={12} />
            <span>{isEditing ? 'Cancel' : 'Quick Edit'}</span>
            <span className="kbd-hint" style={{ fontSize: '0.6rem' }}>E</span>
          </button>
        )}
      </div>
    </div>
  );
}

