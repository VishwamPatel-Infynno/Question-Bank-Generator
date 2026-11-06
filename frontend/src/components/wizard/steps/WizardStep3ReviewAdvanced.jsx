import { useState, useMemo } from 'react';
import { Image as ImageIcon } from 'lucide-react';
import WizardReviewSummary from './WizardReviewSummary';
import WizardAdvancedSettings from './WizardAdvancedSettings';
import {
  DIFFICULTY,
  EMPTY_ARRAY,
  EMPTY_OBJECT,
  SECTION_IDS,
  formatDifficulty,
  getSkillsForSection
} from '../../../constants';

export default function WizardStep3ReviewAdvanced({ generatorForm, sectionMeta = EMPTY_OBJECT, setStep }) {
  const form = generatorForm?.formData || EMPTY_OBJECT;
  const update = generatorForm?.updateField;
  const selectedSection = form.selectedSection || SECTION_IDS.CHEM_PHYS;
  const selectedSubject = form.selectedSubject || '';
  const selectedTopic = form.selectedTopic || '';
  const selectedSubtopic = form.selectedSubtopic || '';
  const difficulty = form.difficulty || DIFFICULTY.MEDIUM;
  const totalQuestions = form.totalQuestions || 50;
  const questionType = form.questionType || 'PASSAGE_BASED_MCQ';
  const allowAiImages = Boolean(form.allowAiImages ?? form.requireImage);
  const setAllowAiImages = generatorForm?.setAllowAiImages;
  const primaryTrap = form.primaryTrap || 'Automatic';
  const primaryTraps = form.primaryTraps || EMPTY_ARRAY;
  const selectedSkill = form.selectedSkill || '';
  const selectedSubskill = form.selectedSubskill || '';
  const selectedSubskills = form.selectedSubskills || EMPTY_ARRAY;
  const likelyMistakePattern = form.likelyMistakePattern || '';
  const likelyMistakePatterns = form.likelyMistakePatterns || EMPTY_ARRAY;
  const additionalInstructions = form.additionalInstructions || '';
  const onTogglePrimaryTrap = generatorForm?.togglePrimaryTrap;
  const onToggleSubskill = generatorForm?.toggleSubskill;
  const onToggleMistakePattern = generatorForm?.toggleMistakePattern;
  const setPrimaryTrap = (v) => update?.('primaryTrap', v);
  const setSelectedSubskill = (v) => update?.('selectedSubskill', v);
  const setLikelyMistakePattern = (v) => update?.('likelyMistakePattern', v);
  const setAdditionalInstructions = (v) => update?.('additionalInstructions', v);
  const [showAdvanced, setShowAdvanced] = useState(false);
  const isCars = selectedSection === SECTION_IDS.CARS;
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
    if (likelyMistakePatterns && likelyMistakePatterns.length > 0) return likelyMistakePatterns;
    if (likelyMistakePattern && likelyMistakePattern !== 'Automatic' && likelyMistakePattern !== 'None') {
      return [likelyMistakePattern];
    }
    return [];
  }, [likelyMistakePatterns, likelyMistakePattern]);

  const isPassage = isCars || questionType === 'PASSAGE_BASED_MCQ';

  const formatSummary = isCars
    ? 'Passage-Based (CARS)'
    : isPassage
    ? 'Passage-Based'
    : 'Standalone';

  const diffLabel = formatDifficulty(difficulty);

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
        onTogglePrimaryTrap={onTogglePrimaryTrap}
        setPrimaryTrap={setPrimaryTrap}
        availableSubskills={availableSubskills}
        effectiveSubskills={effectiveSubskills}
        onToggleSubskill={onToggleSubskill}
        setSelectedSubskill={setSelectedSubskill}
        effectiveMistakes={effectiveMistakes}
        onToggleMistakePattern={onToggleMistakePattern}
        setLikelyMistakePattern={setLikelyMistakePattern}
        additionalInstructions={additionalInstructions}
        setAdditionalInstructions={setAdditionalInstructions}
      />
    </div>
  );
}
