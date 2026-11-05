import {
  Layers,
  FileText,
  CheckCircle2
} from 'lucide-react';
import { normalizeDifficulty } from '../../../constants';

const DEFAULT_DIFFICULTY_TIERS = [];
const COUNT_OPTIONS = Object.freeze([
  { count: 5, label: 'Practice Set (5 Qs)' },
  { count: 50, label: 'Full Exam (50 Qs)' }
]);

export default function WizardStep2LevelFormat({
  selectedSection = 'chem_phys',
  difficulty = 'medium',
  setDifficulty,
  DIFFICULTY_TIERS = DEFAULT_DIFFICULTY_TIERS,
  passageMode = 'single_passage',
  handlePassageModeChange,
  questionType = 'PASSAGE_BASED_MCQ',
  setQuestionType,
  totalQuestions = 50,
  setTotalQuestions
}) {
  const isCars = selectedSection === 'cars';

  const selectPassageMode = (mode) => {
    handlePassageModeChange?.(mode);
    setQuestionType?.(mode === 'single_passage' ? 'PASSAGE_BASED_MCQ' : 'DISCRETE_MCQ');
  };

  const isPassage = isCars || passageMode === 'single_passage' || questionType === 'PASSAGE_BASED_MCQ';

  return (
    <div className="wizard-step-column">
      <div className="wizard-heading-group">
        <h2 className="wizard-step-title">Difficulty &amp; Format</h2>
      </div>

      {/* Difficulty */}
      <div className="wizard-stacked-decision">
        <div className="wizard-decision-header">
          <span className="wizard-decision-title">Difficulty Level</span>
        </div>

        <div className="wizard-difficulty-grid">
          {DIFFICULTY_TIERS.map((tier) => {
            const isSelected = normalizeDifficulty(difficulty) === normalizeDifficulty(tier.id);

            return (
              <div
                key={tier.id}
                className={`wizard-tier-card ${isSelected ? 'selected' : ''}`}
                onClick={() => setDifficulty?.(tier.id)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    setDifficulty?.(tier.id);
                  }
                }}
                role="button"
                tabIndex={0}
                aria-pressed={isSelected}
              >
                <div className="wizard-tier-card-content">
                  <div className="wizard-tier-title-row">
                    <span className={`wizard-tier-dot tier-${tier.id.toLowerCase()}`} />
                    {tier.title}
                  </div>
                  {isSelected && (
                    <CheckCircle2 size={14} color="var(--brand-primary)" />
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Passage & Question Format */}
      <div className="wizard-stacked-decision">
        <div className="wizard-decision-header">
          <span className="wizard-decision-title">Question Format</span>
        </div>

        {isCars ? (
          /* CARS Mode: Strictly 100% Passage-Based */
          <div className="wizard-cars-banner">
            <div className="wizard-tier-card-title-group">
              <FileText size={16} color="var(--brand-primary)" />
              <div>
                <span className="wizard-tier-card-title">
                  Passage-Based (CARS)
                </span>
              </div>
            </div>
          </div>
        ) : (
          /* Sciences Mode: Binary choice between Passage-Based MCQ OR Independent MCQ */
          <div className="wizard-card-grid">
            {/* Mode A: Reading Passage + Questions */}
            <div
              className={`wizard-tier-card ${isPassage ? 'selected' : ''}`}
              onClick={() => selectPassageMode('single_passage')}
              onKeyDown={(e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                  e.preventDefault();
                  selectPassageMode('single_passage');
                }
              }}
              role="button"
              tabIndex={0}
              id="btn-question-type-passage"
            >
              <div className="wizard-tier-card-content">
                <div className="wizard-tier-card-title-group">
                  <FileText size={15} color="var(--brand-primary)" />
                  <div>
                    <span className="wizard-tier-card-title">
                      Passage-Based
                    </span>
                  </div>
                </div>
                {isPassage && (
                  <CheckCircle2 size={14} color="var(--brand-primary)" />
                )}
              </div>
            </div>

            {/* Mode B: Standalone Questions */}
            <div
              className={`wizard-tier-card ${!isPassage ? 'selected' : ''}`}
              onClick={() => selectPassageMode('independent')}
              onKeyDown={(e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                  e.preventDefault();
                  selectPassageMode('independent');
                }
              }}
              role="button"
              tabIndex={0}
              id="btn-question-type-independent"
            >
              <div className="wizard-tier-card-content">
                <div className="wizard-tier-card-title-group">
                  <Layers size={15} color="var(--status-purple)" />
                  <div>
                    <span className="wizard-tier-card-title">
                      Standalone
                    </span>
                  </div>
                </div>
                {!isPassage && (
                  <CheckCircle2 size={14} color="var(--brand-primary)" />
                )}
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Question Count (Strictly 5 or 50) */}
      <div className="wizard-stacked-decision">
        <div className="wizard-decision-header">
          <span className="wizard-decision-title">Question Count</span>
        </div>

        <div className="wizard-count-grid">
          {COUNT_OPTIONS.map((opt) => {
            const isSelected = totalQuestions === opt.count;
            return (
              <div
                key={opt.count}
                className={`wizard-tier-card wizard-count-card ${isSelected ? 'selected' : ''}`}
                onClick={() => setTotalQuestions?.(opt.count)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    setTotalQuestions?.(opt.count);
                  }
                }}
                role="button"
                tabIndex={0}
                aria-pressed={isSelected}
              >
                <div>
                  <div className={`wizard-count-label ${isSelected ? 'selected' : ''}`}>
                    {opt.label}
                  </div>
                </div>
                {isSelected && (
                  <CheckCircle2 size={16} color="var(--brand-primary)" />
                )}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
