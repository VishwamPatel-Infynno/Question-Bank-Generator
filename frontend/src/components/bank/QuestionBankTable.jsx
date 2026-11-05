import { memo, useMemo } from 'react';
import {
  Award,
  Copy,
  Check,
  Eye,
  ChevronDown,
  ChevronUp,
  CheckSquare,
  Square,
  Trash2,
  Image as ImageIcon,
  Tag,
  Target
} from 'lucide-react';
import VisualStimulusViewer from '../question/VisualStimulusViewer';
import SharedPassageCard from '../question/SharedPassageCard';
import MentorExplanationView from '../question/MentorExplanationView';
import { countWords, getEffectiveTrapInfo } from '../../utils';
import { EMPTY_ARRAY, formatDifficulty, getDifficultyBadgeClass, getSectionBadgeClass } from '../../constants';

const SECTION_SHORT_LABEL = {
  chem_phys: 'Chem / Phys',
  cars: 'CARS',
  bio_biochem: 'Bio / Biochem',
  psych_soc: 'Psych / Soc'
};

/**
 * QuestionBankCardRow
 *
 * Isolated, memoized card row preventing full-table re-render cascades
 * during multi-item selection, clipboard copying, and inline expansion.
 */
const QuestionBankCardRow = memo(function QuestionBankCardRow({
  q,
  isSelected,
  isExpanded,
  isCopied,
  onToggleSelect,
  onToggleExpand,
  onCopy,
  onDelete,
  onSelectQuestion,
}) {
  return (
    <div className={`qbank-card-row ${isSelected ? 'selected' : ''}`}>
      {/* Main Row */}
      <div className="qbank-card-main">
        {/* Checkbox & Details */}
        <div className="qbank-table-row-top">
          <button
            type="button"
            onClick={(e) => onToggleSelect(q.id, e)}
            className={`qbank-card-select-btn ${isSelected ? 'selected' : ''}`}
            title="Select question"
            aria-label="Select question"
            aria-pressed={isSelected}
          >
            {isSelected ? <CheckSquare size={16} /> : <Square size={16} />}
          </button>

          <div className="qbank-card-details">
            {/* Metadata Row */}
            <div className="qbank-badges-strip">
              <span className={`badge ${getSectionBadgeClass(q.section)} qbank-table-badge-sec`}>
                {SECTION_SHORT_LABEL[q.section] || q.section_label || q.section}
              </span>

              {q.subtopic && (
                <span className="qbank-table-subtopic-tag">{q.subtopic}</span>
              )}

              <span className={`badge ${getDifficultyBadgeClass(q.difficulty)} qbank-table-diff-badge`}>
                {formatDifficulty(q.difficulty)}
              </span>

              <span className="badge badge-emerald qbank-table-score-badge">
                <Award size={10} /> {q.final_score || 95}/100
              </span>

              {q.mcat_scaled_score && (
                <span className="badge qbank-mcat-badge">
                  MCAT {q.mcat_scaled_score}
                </span>
              )}

              {q.aamc_skill && (
                <span
                  className="badge badge-cyan qbank-table-type-badge"
                  title={`AAMC Reasoning Skill: ${q.aamc_skill}`}
                >
                  {q.aamc_skill}
                </span>
              )}

              {q.passage_id ? (
                <span className="badge badge-cyan qbank-table-type-badge">
                  Passage Set
                </span>
              ) : (q.passage_required === 'Yes' || countWords(q.stimulus_text) >= 180) ? (
                <span className="qbank-table-mode-label">Passage</span>
              ) : (
                <span className="qbank-table-mode-label">Standalone</span>
              )}

              {(q.image_svg || q.image_url || q.stage_outcomes?.visual_stimulus?.image_svg || q.stage_outcomes?.visual_stimulus?.image_url || q.stage_outcomes?.passage_visual_stimulus?.image_svg) && (
                <span className="badge badge-purple qbank-table-fig-pill">
                  <ImageIcon size={10} /> Diagram
                </span>
              )}

              {(() => {
                const trapInfo = getEffectiveTrapInfo(q);
                if (!trapInfo?.label) return null;
                return (
                  <span
                    className="badge badge-purple qbank-table-trap-pill"
                    title={`Common Test Trap: ${trapInfo.label}`}
                  >
                    <Tag size={9} /> {trapInfo.label}
                  </span>
                );
              })()}

              {q.likely_mistake_pattern && (
                <span
                  className="badge qbank-table-mistake-pill"
                  title={`Targeted Student Misconception: ${q.likely_mistake_pattern}`}
                >
                  <Target size={9} /> {q.likely_mistake_pattern}
                </span>
              )}
            </div>

            {/* Question Stem */}
            <div className="qbank-stem">
              {q.question_stem}
            </div>

            {/* Stimulus Snippet */}
            {q.stimulus_text && q.stimulus_text.trim() && (
              <div className="qbank-snippet">
                {q.stimulus_text}
              </div>
            )}
          </div>
        </div>

        {/* Actions */}
        <div className="qbank-actions">
          <button
            type="button"
            onClick={() => onSelectQuestion(q)}
            className="btn-secondary qbank-table-action-btn"
            title="Open question in editorial desk inspector"
          >
            <Eye size={13} /> Open
          </button>

          <button
            type="button"
            onClick={() => onToggleExpand(isExpanded ? null : q.id)}
            className="btn-secondary qbank-table-action-icon"
            title={isExpanded ? 'Collapse preview' : 'Expand preview inline'}
            aria-expanded={isExpanded}
          >
            {isExpanded ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
          </button>

          <button
            type="button"
            onClick={(e) => onCopy(q, e)}
            className="btn-secondary qbank-table-action-icon"
            title="Copy formatted question text"
          >
            {isCopied ? <Check size={14} color="var(--status-success)" /> : <Copy size={14} />}
          </button>

          <button
            type="button"
            onClick={(e) => onDelete(q.id, e)}
            className="btn-danger qbank-table-action-icon"
            title="Delete question"
          >
            <Trash2 size={14} />
          </button>
        </div>
      </div>

      {/* Inline Expansion Drawer */}
      {isExpanded && (
        <div className="qbank-drawer">
          {q.stimulus_text && (
            <div className="qbank-table-rationale-box">
              <SharedPassageCard
                title={q.passage_id ? 'Shared Reading Passage' : 'Reading Passage'}
                passageText={q.stimulus_text}
                questionCount={1}
                diagramQuestion={q}
                collapsible={false}
              />
            </div>
          )}

          {!q.stimulus_text && <VisualStimulusViewer question={q} />}

          {/* Options Grid */}
          <div className="qbank-options-grid">
            {(() => {
              const correctList = Array.isArray(q.correct_answer_ids) && q.correct_answer_ids.length > 0
                ? q.correct_answer_ids.map(k => String(k).trim().toUpperCase())
                : (q.correct_answer_id || '').split(',').map(k => k.trim().toUpperCase()).filter(Boolean);

              return q.options?.map(opt => {
                const isCorrect = correctList.includes(opt.id.toUpperCase());
                return (
                  <div
                    key={opt.id}
                    className={`qbank-option-cell ${isCorrect ? 'correct' : ''}`}
                  >
                    <span className={`qbank-option-cell-letter ${isCorrect ? 'correct' : ''}`}>
                      {opt.id}:
                    </span>
                    <span className={`qbank-option-cell-text ${isCorrect ? 'correct' : ''}`}>
                      {opt.text}
                    </span>
                    {isCorrect && (
                      <span className="badge badge-emerald qbank-table-rationale-tag">
                        Key
                      </span>
                    )}
                  </div>
                );
              });
            })()}
          </div>

          {/* Explanation */}
          {q.explanation && (
            <div className="qbank-explanation-box">
              <MentorExplanationView
                explanation={q.explanation}
                isCompact={true}
                options={q.options}
                correctAnswerId={q.correct_answer_id}
                primaryTrap={q.primary_trap}
                likelyMistakePattern={q.likely_mistake_pattern}
              />
            </div>
          )}
        </div>
      )}
    </div>
  );
});

/**
 * QuestionBankTable
 *
 * Renders the question bank repository using the canonical Editorial Cards view,
 * featuring interactive selection, expandable stimulus/diagram drawers,
 * options proof breakdowns, and mentor pedagogical explanations.
 */
export default function QuestionBankTable({
  paginatedQuestions = EMPTY_ARRAY,
  selectedIds = EMPTY_ARRAY,
  expandedId,
  setExpandedId,
  copiedId,
  onToggleSelect,
  onCopy,
  onDelete,
  onSelectQuestion,
}) {
  const selectedSet = useMemo(() => new Set(selectedIds), [selectedIds]);

  return (
    <div className="qbank-table-list-wrap">
      {paginatedQuestions.map((q) => (
        <QuestionBankCardRow
          key={q.id}
          q={q}
          isSelected={selectedSet.has(q.id)}
          isExpanded={expandedId === q.id}
          isCopied={copiedId === q.id}
          onToggleSelect={onToggleSelect}
          onToggleExpand={setExpandedId}
          onCopy={onCopy}
          onDelete={onDelete}
          onSelectQuestion={onSelectQuestion}
        />
      ))}
    </div>
  );
}
