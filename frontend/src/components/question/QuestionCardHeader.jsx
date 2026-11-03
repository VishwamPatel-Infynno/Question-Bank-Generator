import { Award, Edit3, ShieldCheck, Image as ImageIcon, Tag } from 'lucide-react';
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
              background: 'var(--status-purple-bg)',
              border: '1px solid var(--status-purple-border)',
              color: 'var(--status-purple)'
            }}
            title={`Trap: ${effectiveTrapInfo.label}`}
          >
            <Tag size={11} /> {effectiveTrapInfo.label}
          </span>
        )}

        {question.aamc_skill && (
          <span
            className="badge badge-cyan"
            style={{ fontSize: '0.65rem', padding: '1px 6px' }}
            title={`AAMC Reasoning Skill: ${question.aamc_skill}`}
          >
            {question.aamc_skill}
          </span>
        )}

        <span className="badge badge-emerald" style={{ fontSize: '0.675rem', fontWeight: 600 }}>
          <Award size={11} /> {question.final_score}/100
        </span>

        {question.mcat_scaled_score && (
          <span
            className="badge"
            style={{
              fontSize: '0.675rem',
              fontWeight: 700,
              background: 'var(--brand-light)',
              color: 'var(--brand-primary)',
              border: '1px solid var(--border-brand)'
            }}
          >
            MCAT {question.mcat_scaled_score}
          </span>
        )}
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
            <span>Audit</span>
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
            <span>{isEditing ? 'Cancel' : 'Edit'}</span>
            <span className="kbd-hint" style={{ fontSize: '0.6rem' }}>E</span>
          </button>
        )}
      </div>
    </div>
  );
}

