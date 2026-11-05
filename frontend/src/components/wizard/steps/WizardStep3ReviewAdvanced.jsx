import { useState, useMemo } from 'react';
import { Image as ImageIcon } from 'lucide-react';
import WizardReviewSummary from './WizardReviewSummary';
import WizardAdvancedSettings from './WizardAdvancedSettings';
import { EMPTY_ARRAY, EMPTY_OBJECT, LIKELY_MISTAKE_PATTERNS, getSkillsForSection } from '../../../constants';

export default function WizardStep3ReviewAdvanced({
  selectedSection = 'chem_phys',
  sectionMeta = EMPTY_OBJECT,
  setStep,
  selectedSubject = '',
  selectedTopic = '',
  selectedSubtopic = '',
  difficulty = 'medium',
  totalQuestions = 50,
  questionType = 'PASSAGE_BASED_MCQ',
  allowAiImages = false,
  setAllowAiImages,
  COGNITIVE_TRAPS = EMPTY_ARRAY,
  primaryTrap = 'Automatic',
  setPrimaryTrap,
  primaryTraps = EMPTY_ARRAY,
  onTogglePrimaryTrap,
  selectedSkill = '',
  setSelectedSkill: _setSelectedSkill,
  selectedSubskill = '',
  setSelectedSubskill,
  selectedSubskills = EMPTY_ARRAY,
  onToggleSubskill,
  likelyMistakePattern = '',
  setLikelyMistakePattern,
  likelyMistakePatterns = EMPTY_ARRAY,
  onToggleMistakePattern,
  customMistakePattern = '',
  setCustomMistakePattern: _setCustomMistakePattern,
  additionalInstructions = '',
  setAdditionalInstructions
}) {
  const [showAdvanced, setShowAdvanced] = useState(false);
  const isCars = selectedSection === 'cars';
  const hasInstructions = Boolean(additionalInstructions && additionalInstructions.trim().length > 0);

  const effectiveTraps = useMemo(() => {
    if (primaryTraps && primaryTraps.length > 0) return primaryTraps;
    if (primaryTrap && primaryTrap !== 'Automatic') return [primaryTrap];
    return [];
  }, [primaryTraps, primaryTrap]);

  const availableSkills = useMemo(() => {
    return getSkillsForSection(selectedSection);
  }, [selectedSection]);

  const activeSkill = useMemo(() => {
    return availableSkills.find((s) => s.id === selectedSkill) || availableSkills[0] || null;
  }, [availableSkills, selectedSkill]);

  const availableSubskills = useMemo(() => {
    return activeSkill?.subskills || [];
  }, [activeSkill]);

  const effectiveSubskills = useMemo(() => {
    if (selectedSubskills && selectedSubskills.length > 0) return selectedSubskills;
    if (selectedSubskill && selectedSubskill !== '' && selectedSubskill !== 'All') return [selectedSubskill];
    return [];
  }, [selectedSubskills, selectedSubskill]);

  const effectiveMistakes = useMemo(() => {
    if (customMistakePattern) return [customMistakePattern];
    if (likelyMistakePatterns && likelyMistakePatterns.length > 0) return likelyMistakePatterns;
    if (likelyMistakePattern && likelyMistakePattern !== 'Automatic' && likelyMistakePattern !== 'None') {
      return [likelyMistakePattern];
    }
    return [];
  }, [customMistakePattern, likelyMistakePatterns, likelyMistakePattern]);

  const isPassage = isCars || questionType === 'PASSAGE_BASED_MCQ';

  const formatSummary = isCars
    ? 'Passage-Based (CARS)'
    : isPassage
    ? 'Passage-Based'
    : 'Standalone';

  const diffLabel = difficulty
    ? difficulty.charAt(0).toUpperCase() + difficulty.slice(1).toLowerCase()
    : 'Medium';

  const topicLabel = selectedSubtopic || selectedTopic || selectedSubject || 'All Topics';
  const sectionLabel = sectionMeta.label || selectedSection;

  return (
    <div className="wizard-step3-container">
      <div className="wizard-heading-group">
        <h2 className="wizard-step-title">Review &amp; Create</h2>
      </div>

      {/* Review Summary Parameters */}
      <WizardReviewSummary
        sectionLabel={sectionLabel}
        topicLabel={topicLabel}
        diffLabel={diffLabel}
        formatSummary={formatSummary}
        totalQuestions={totalQuestions}
        setStep={setStep}
      />

      {/* Dedicated Scientific Diagrams & Reaction Schemes Card (Sciences Only) */}
      {!isCars && (
        <div
          role="switch"
          aria-checked={allowAiImages}
          tabIndex={0}
          onClick={() => setAllowAiImages?.(!allowAiImages)}
          onKeyDown={(e) => {
            if (e.key === ' ' || e.key === 'Enter') {
              e.preventDefault();
              setAllowAiImages?.(!allowAiImages);
            }
          }}
          className={`wizard-diagram-card ${allowAiImages ? 'active' : ''}`}
        >
          <div className="wizard-diagram-card-left">
            <div className={`wizard-diagram-icon-box ${allowAiImages ? 'active' : ''}`}>
              <ImageIcon size={16} />
            </div>
            <div>
              <div className="wizard-diagram-label">
                Include Images When Needed
              </div>
            </div>
          </div>

          {/* Pill Toggle Switch */}
          <div className={`wizard-switch-track ${allowAiImages ? 'active' : ''}`}>
            <div className={`wizard-switch-thumb ${allowAiImages ? 'active' : ''}`} />
          </div>
        </div>
      )}

      {/* Advanced Options Collapsible Accordion */}
      <WizardAdvancedSettings
        showAdvanced={showAdvanced}
        setShowAdvanced={setShowAdvanced}
        hasInstructions={hasInstructions}
        effectiveTraps={effectiveTraps}
        COGNITIVE_TRAPS={COGNITIVE_TRAPS}
        onTogglePrimaryTrap={onTogglePrimaryTrap}
        setPrimaryTrap={setPrimaryTrap}
        availableSubskills={availableSubskills}
        effectiveSubskills={effectiveSubskills}
        onToggleSubskill={onToggleSubskill}
        setSelectedSubskill={setSelectedSubskill}
        effectiveMistakes={effectiveMistakes}
        LIKELY_MISTAKE_PATTERNS={LIKELY_MISTAKE_PATTERNS}
        onToggleMistakePattern={onToggleMistakePattern}
        setLikelyMistakePattern={setLikelyMistakePattern}
        additionalInstructions={additionalInstructions}
        setAdditionalInstructions={setAdditionalInstructions}
      />
    </div>
  );
}
