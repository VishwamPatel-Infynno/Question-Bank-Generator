import React, { useState, useMemo } from 'react';
import { Image as ImageIcon } from 'lucide-react';
import WizardReviewSummary from './WizardReviewSummary';
import WizardAdvancedSettings from './WizardAdvancedSettings';
import {
  getSkillsForSection,
  LIKELY_MISTAKE_PATTERNS
} from '../../../constants';

const EMPTY_OBJECT = Object.freeze({});
const EMPTY_ARRAY = Object.freeze([]);

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
    <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
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
          style={{
            background: 'var(--bg-surface)',
            border: allowAiImages ? '1px solid var(--brand-primary)' : '1px solid var(--border-light)',
            boxShadow: allowAiImages ? '0 0 0 1px var(--brand-primary), var(--shadow-sm)' : 'none',
            borderRadius: 'var(--radius-sm)',
            padding: '12px 16px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            gap: '16px',
            cursor: 'pointer',
            transition: 'border-color 0.2s ease, box-shadow 0.2s ease, background 0.2s ease'
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <div
              style={{
                width: '32px',
                height: '32px',
                borderRadius: 'var(--radius-sm)',
                background: allowAiImages ? 'rgba(51, 90, 207, 0.12)' : 'var(--bg-surface-subtle)',
                border: allowAiImages ? '1px solid rgba(51, 90, 207, 0.25)' : '1px solid var(--border-light)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: allowAiImages ? 'var(--brand-primary)' : 'var(--text-muted)',
                flexShrink: 0,
                transition: 'all 0.2s ease'
              }}
            >
              <ImageIcon size={16} />
            </div>
            <div>
              <div
                style={{
                  fontSize: '0.84rem',
                  fontWeight: 600,
                  color: 'var(--text-primary)'
                }}
              >
                Include Images When Needed
              </div>
            </div>
          </div>

          {/* Pill Toggle Switch */}
          <div
            style={{
              width: '36px',
              height: '20px',
              borderRadius: '9999px',
              background: allowAiImages ? 'var(--brand-primary)' : 'var(--border-medium)',
              position: 'relative',
              flexShrink: 0,
              transition: 'background 0.2s ease'
            }}
          >
            <div
              style={{
                width: '16px',
                height: '16px',
                borderRadius: '50%',
                background: 'var(--text-on-brand, #ffffff)',
                position: 'absolute',
                top: '2px',
                left: allowAiImages ? '18px' : '2px',
                boxShadow: '0 1px 3px rgba(0,0,0,0.2)',
                transition: 'left 0.2s ease'
              }}
            />
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
