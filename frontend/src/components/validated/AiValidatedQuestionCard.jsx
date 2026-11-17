import { memo } from 'react';
import {
  Award,
  CheckCircle2,
  Trash2,
  Database,
  ChevronDown,
  ChevronUp,
  Image as ImageIcon,
  BookOpen,
  Tag,
  Target
} from 'lucide-react';
import {
  formatAamcSkill,
  formatDifficulty,
  getDifficultyBadgeClass,
  getSectionBadgeClass,
  getSectionShortLabel
} from '../../constants/mcat';
import {
  countWords,
  getEffectiveTrapInfo,
  hasQuestionImage,
  isCorrectOption
} from '../../utils';
import VisualStimulusViewer from '../question/VisualStimulusViewer';
import SharedPassageCard from '../question/SharedPassageCard';

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
  const hasDiagram = hasQuestionImage(q);
  const trapInfo = getEffectiveTrapInfo(q);

  return (
    <div className={`validated-card ${isSelected ? 'selected' : ''}`}>
      {/* Card Header */}
      <div className="validated-card-header">
        <div className="validated-card-header-left">
          <input
            type="checkbox"
            checked={isSelected}
            onChange={() => onToggleSelect?.(q.id)}
            className="validated-card-checkbox"
          />
          <span className="validated-index">
            #{index + 1}
          </span>
          <span className={`badge ${getSectionBadgeClass(q.section)} validated-card-badge-sm`}>
            {getSectionShortLabel(q.section) || q.section_label || q.section}
          </span>
          <span className={`badge ${getDifficultyBadgeClass(q.difficulty)} validated-card-diff`}>
            {formatDifficulty(q.difficulty)}
          </span>
          {trapInfo?.label && (
            <span
              className="badge badge-purple validated-card-trap-tag"
              title={`Trap: ${trapInfo.label}`}
            >
              <Tag size={10} /> {trapInfo.label}
            </span>
          )}
          {q.aamc_skill && (
            <span
              className="badge badge-cyan validated-card-skill-tag"
              title={`AAMC Reasoning Skill: ${formatAamcSkill(q.aamc_skill)}`}
            >
              {formatAamcSkill(q.aamc_skill)}
            </span>
          )}
          {q.likely_mistake_pattern && (
            <span
              className="badge validated-card-mistake-tag"
              title={`Mistake: ${q.likely_mistake_pattern}`}
            >
              <Target size={10} /> {q.likely_mistake_pattern}
            </span>
          )}
          {hasDiagram && (
            <span
              className="badge badge-purple validated-card-figure-tag"
              title="Contains Diagram"
            >
              <ImageIcon size={10} /> Diagram
            </span>
          )}
        </div>

        <div className="validated-card-header-right">
          <span className="validated-score-pill">
            <Award size={11} /> {q.final_score}/100
          </span>
        </div>
      </div>

      {/* Stimulus / Passage Snippet */}
      {hasPassage && (
        <div className="validated-passage-box">
          <div
            className="validated-passage-header"
            role="button"
            tabIndex={0}
            aria-expanded={isPassageExpanded}
            aria-controls={`passage-body-${q.id}`}
            onClick={() => onTogglePassage?.(q.id)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                onTogglePassage?.(q.id);
              }
            }}
          >
            <div className="validated-card-passage-header">
              <BookOpen size={12} />
              <span>Reading Passage ({countWords(q.stimulus_text)} words)</span>
            </div>
            <button
              type="button"
              className="btn-secondary validated-card-passage-toggle-btn"
              tabIndex={-1}
              onClick={(e) => {
                e.stopPropagation();
                onTogglePassage?.(q.id);
              }}
              aria-label={isPassageExpanded ? 'Hide passage' : 'View passage'}
            >
              {isPassageExpanded ? <ChevronUp size={11} /> : <ChevronDown size={11} />}
              <span>{isPassageExpanded ? 'Hide' : 'View'}</span>
            </button>
          </div>

          {isPassageExpanded && (
            <div className="validated-card-passage-body" id={`passage-body-${q.id}`}>
              <SharedPassageCard
                title="Reading Passage"
                passageText={q.stimulus_text}
                diagramQuestion={hasDiagram ? q : null}
              />
            </div>
          )}
        </div>
      )}

      {/* Visual Stimulus Diagram / Image for standalone questions (without passage) */}
      {!hasPassage && hasDiagram && (
        <div className="validated-card-stem-box">
          <VisualStimulusViewer question={q} compact={false} />
        </div>
      )}

      {/* Question Stem */}
      <div className="validated-stem">
        {q.question_stem}
      </div>

      {/* 4 Options List */}
      <div className="validated-options-list">
        {(q.options || []).map((opt) => {
          const isCorrect = isCorrectOption(q, opt.id);

          return (
            <div
              key={opt.id}
              className={`validated-option-row ${isCorrect ? 'correct' : ''}`}
            >
              <span className={`validated-card-option-letter ${isCorrect ? 'correct' : ''}`}>
                {opt.id}.
              </span>
              <span className="validated-option-text">
                {opt.text}
              </span>
              {isCorrect && (
                <span className="validated-option-correct-badge">
                  <CheckCircle2 size={12} /> Correct
                </span>
              )}
            </div>
          );
        })}
      </div>

      {/* Card Footer: Metadata Tags & Action Buttons */}
      <div className="validated-card-footer">
        <div className="validated-card-footer-left">
          <span className="validated-card-footer-meta">
            Subtopic: <strong>{q.subtopic || 'General'}</strong>
          </span>
        </div>

        <div className="validated-actions">
          {onOpenAudit && (
            <button
              type="button"
              onClick={() => onOpenAudit(q)}
              className="btn-secondary validated-card-audit-btn"
            >
              Quality Review
            </button>
          )}

          <button
            type="button"
            onClick={() => onDiscard?.(q)}
            disabled={actionInProgress}
            className="btn-secondary validated-card-discard-btn"
            title="Discard question"
          >
            <Trash2 size={12} />
            <span>Discard</span>
          </button>

          <button
            type="button"
            onClick={() => onMoveToBank?.(q)}
            disabled={actionInProgress}
            className="btn-primary validated-save-btn validated-card-bank-btn"
          >
            <Database size={12} />
            <span>Save to Question Bank</span>
          </button>
        </div>
      </div>
    </div>
  );
}

export default memo(AiValidatedQuestionCard);
