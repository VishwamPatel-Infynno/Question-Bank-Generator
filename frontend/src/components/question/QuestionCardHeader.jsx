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
    <div className="qcard-header">
      <div className="qcard-header-meta">
        {isSaved ? (
          <span className="qcard-header-status-saved">
            <span className="qcard-header-dot saved" />
            Saved
          </span>
        ) : (
          <span className="qcard-header-status-ready">
            <span className="qcard-header-dot ready" />
            Ready
          </span>
        )}

        <span className="qcard-header-divider">|</span>

        <span className={`badge ${getSectionBadgeClass(question.section)} qcard-header-section-badge`}>
          {question.section_label || question.section}
        </span>

        <span className={`badge ${diffBadgeClass} qcard-header-diff-badge`}>
          {diffLabel}
        </span>

        {hasImage && (
          <span className="badge badge-purple qcard-header-badge-diagram">
            <ImageIcon size={11} /> Diagram
          </span>
        )}

        {effectiveTrapInfo?.label && (
          <span
            className="badge badge-purple qcard-header-trap-chip"
            title={`Trap: ${effectiveTrapInfo.label}`}
          >
            <Tag size={11} /> {effectiveTrapInfo.label}
          </span>
        )}

        {question.aamc_skill && (
          <span
            className="badge badge-cyan qcard-header-skill-chip"
            title={`AAMC Reasoning Skill: ${question.aamc_skill}`}
          >
            {question.aamc_skill}
          </span>
        )}

        <span className="badge badge-emerald qcard-header-score-badge">
          <Award size={11} /> {question.final_score}/100
        </span>

        {question.mcat_scaled_score && (
          <span className="badge qcard-header-scaled-badge">
            MCAT {question.mcat_scaled_score}
          </span>
        )}
      </div>

      {/* Top Actions */}
      <div className="qcard-header-actions">
        {onOpenAudit && (
          <button
            type="button"
            onClick={() => onOpenAudit(question)}
            className="btn-secondary qcard-header-btn"
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
            className="btn-secondary qcard-header-btn"
            title="Edit question text (Press E)"
          >
            <Edit3 size={12} />
            <span>{isEditing ? 'Cancel' : 'Edit'}</span>
            <span className="kbd-hint">E</span>
          </button>
        )}
      </div>
    </div>
  );
}

