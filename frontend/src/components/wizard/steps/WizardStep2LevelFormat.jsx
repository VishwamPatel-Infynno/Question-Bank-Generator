import { Layers, FileText } from 'lucide-react';
import { DIFFICULTY_TIERS, normalizeDifficulty, SECTION_IDS, DIFFICULTY } from '../../../constants';
import WizardChoiceCard from '../WizardChoiceCard';

const COUNT_OPTIONS = Object.freeze([
  { count: 5, label: '5 Questions' },
  { count: 50, label: '50 Questions' }
]);

export default function WizardStep2LevelFormat({
  selectedSection = SECTION_IDS.CHEM_PHYS,
  difficulty = DIFFICULTY.MEDIUM,
  setDifficulty,
  passageMode = 'single_passage',
  handlePassageModeChange,
  questionType = 'PASSAGE_BASED_MCQ',
  setQuestionType,
  totalQuestions = 50,
  setTotalQuestions
}) {
  const isCars = selectedSection === SECTION_IDS.CARS;

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
              <WizardChoiceCard key={tier.id} selected={isSelected} onSelect={() => setDifficulty?.(tier.id)}>
                <div className="wizard-tier-title-row">
                  <span className={`wizard-tier-dot tier-${tier.id.toLowerCase()}`} />
                  {tier.title}
                </div>
              </WizardChoiceCard>
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
            <WizardChoiceCard
              id="btn-question-type-passage"
              selected={isPassage}
              onSelect={() => selectPassageMode('single_passage')}
            >
              <div className="wizard-tier-card-title-group">
                <FileText size={15} color="var(--brand-primary)" />
                <span className="wizard-tier-card-title">Passage-Based</span>
              </div>
            </WizardChoiceCard>

            {/* Mode B: Standalone Questions */}
            <WizardChoiceCard
              id="btn-question-type-independent"
              selected={!isPassage}
              onSelect={() => selectPassageMode('independent')}
            >
              <div className="wizard-tier-card-title-group">
                <Layers size={15} color="var(--status-purple)" />
                <span className="wizard-tier-card-title">Standalone</span>
              </div>
            </WizardChoiceCard>
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
              <WizardChoiceCard
                key={opt.count}
                className="wizard-count-card"
                selected={isSelected}
                onSelect={() => setTotalQuestions?.(opt.count)}
              >
                <div className={`wizard-count-label ${isSelected ? 'selected' : ''}`}>{opt.label}</div>
              </WizardChoiceCard>
            );
          })}
        </div>
      </div>
    </div>
  );
}
