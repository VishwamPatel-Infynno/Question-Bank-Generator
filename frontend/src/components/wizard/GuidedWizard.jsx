import React, { useState, useEffect, useCallback } from 'react';
import {
  ArrowLeft,
  ArrowRight,
  Sparkles,
  Check,
  Zap
} from 'lucide-react';
import {
  PACING_INFO,
  getSkillsForSection,
  SECTION_METADATA,
  DIFFICULTY_TIERS,
  COGNITIVE_TRAPS
} from '../../constants';
import {
  WizardStep1SectionFocus,
  WizardStep2LevelFormat,
  WizardStep3ReviewAdvanced
} from './steps';

const STEP_CONFIG = [
  { num: 1, label: 'Section & Topic', short: 'Section', subtitle: 'Choose Exam Section & Topic', nextLabel: 'Continue' },
  { num: 2, label: 'Difficulty & Format', short: 'Format', subtitle: 'Choose Difficulty & Format', nextLabel: 'Review & Create' },
  { num: 3, label: 'Review & Create', short: 'Review', subtitle: 'Review & Start Generation', nextLabel: 'Create Questions' }
];

const QUICK_PRESETS = [
  {
    id: 'bio_biochem_5',
    label: 'Biochem Passage Set',
    tag: '5 Qs',
    section: 'bio_biochem',
    total: 5,
    passageRequired: 'Yes',
    passageMode: 'single_passage',
    desc: 'Enzyme kinetics & metabolic regulation passage'
  },
  {
    id: 'cars_essay_5',
    label: 'CARS Reasoning',
    tag: '5 Qs',
    section: 'cars',
    total: 5,
    passageRequired: 'Yes',
    passageMode: 'single_passage',
    desc: 'Humanities & social sciences reasoning passage'
  },
  {
    id: 'chem_phys_5',
    label: 'Physics Standalone',
    tag: '5 Qs',
    section: 'chem_phys',
    total: 5,
    passageRequired: 'No',
    passageMode: 'independent',
    desc: 'Discrete physics & chemistry questions'
  },
  {
    id: 'psych_soc_5',
    label: 'Psych / Sociology',
    tag: '5 Qs',
    section: 'psych_soc',
    total: 5,
    passageRequired: 'Yes',
    passageMode: 'single_passage',
    desc: 'Cognitive bias & behavioral health study'
  }
];

export default function GuidedWizard({
  generatorForm,
  onGenerateQuestions,
  onLaunchGeneration,
  isLaunchingBatch = false,
  step: controlledStep,
  setStep: controlledSetStep
}) {
  const [internalStep, setInternalStep] = useState(1);
  const step = controlledStep !== undefined ? controlledStep : internalStep;
  const setStep = controlledSetStep || setInternalStep;
  const totalSteps = 3;

  const form = generatorForm?.formData || {};
  const update = generatorForm?.updateField;
  const updateFields = generatorForm?.updateFields;

  const selectedSection = form.selectedSection || 'chem_phys';
  const selectedSubject = form.selectedSubject || '';
  const selectedUnit = form.selectedUnit || '';
  const selectedTopic = form.selectedTopic || '';
  const selectedSubtopic = form.selectedSubtopic || '';
  const selectedSkill = form.selectedSkill || '';
  const selectedSubskill = form.selectedSubskill || '';
  const questionType = form.questionType || 'PASSAGE_BASED_MCQ';
  const difficulty = form.difficulty || 'medium';
  const totalQuestions = form.totalQuestions || 50;
  const setGenerationTotal = generatorForm?.setGenerationTotal || ((t) => update('totalQuestions', t));
  const primaryTrap = form.primaryTrap || 'Automatic';
  const primaryTraps = form.primaryTraps || [];
  const likelyMistakePattern = form.likelyMistakePattern || '';
  const likelyMistakePatterns = form.likelyMistakePatterns || [];
  const selectedSubskills = form.selectedSubskills || [];
  const selectedSubtopics = form.selectedSubtopics || [];
  const customMistakePattern = form.customMistakePattern || '';

  const togglePrimaryTrap = generatorForm?.togglePrimaryTrap;
  const toggleSubskill = generatorForm?.toggleSubskill;
  const toggleMistakePattern = generatorForm?.toggleMistakePattern;
  const toggleSubtopic = generatorForm?.toggleSubtopic;

  const setDifficulty = (v) => update('difficulty', v);
  const setQuestionType = (v) => update('questionType', v);
  const passageMode = form.passageMode || 'single_passage';
  const setPrimaryTrap = (v) => update('primaryTrap', v);
  const allowAiImages = Boolean(form.allowAiImages ?? form.requireImage);
  const setAllowAiImages = generatorForm?.setAllowAiImages || ((v) => update('allowAiImages', v));

  const sectionMeta = SECTION_METADATA[selectedSection] || SECTION_METADATA.chem_phys;
  const pacing = PACING_INFO[selectedSection] || PACING_INFO.chem_phys;

  // Section Selection handler
  const handleSelectSection = (sectionId) => {
    const isCars = sectionId === 'cars';
    const skills = getSkillsForSection(sectionId);
    const firstSkill = skills[0];

    if (isCars) {
      updateFields({
        selectedSection: sectionId,
        selectedSubject: '',
        selectedUnit: '',
        selectedTopic: '',
        selectedSubtopic: 'All Core Topics (Balanced Mix)',
        selectedSubtopics: [],
        selectedSkill: firstSkill?.id || 'CARS1',
        selectedSubskill: firstSkill?.subskills?.[0] || '',
        selectedSubskills: [],
        passageMode: 'single_passage',
        passageRequired: 'Yes',
        questionType: 'PASSAGE_BASED_MCQ',
        passageQuestionCount: totalQuestions,
        passageCount: totalQuestions,
        passageSingleCount: totalQuestions,
        passageMultiCount: 0,
        singleChoiceCount: totalQuestions,
        multiChoiceCount: 0,
        independentSingleCount: 0,
        independentMultiCount: 0,
        requireImage: false,
        allowAiImages: false,
        requirePassageImage: false,
        visual_type: 'None'
      });
    } else {
      updateFields({
        selectedSection: sectionId,
        selectedSubject: '',
        selectedUnit: '',
        selectedTopic: '',
        selectedSubtopic: 'All Core Topics (Balanced Mix)',
        selectedSubtopics: [],
        selectedSkill: firstSkill?.id || 'S1',
        selectedSubskill: firstSkill?.subskills?.[0] || '',
        selectedSubskills: [],
        singleChoiceCount: totalQuestions,
        multiChoiceCount: 0,
        allowAiImages: true,
        requireImage: true,
        requirePassageImage: true,
        visual_type: 'AI_FLUX_Image'
      });
    }
  };

  const handlePassageModeChange = (mode) => {
    if (mode === 'single_passage') {
      updateFields({
        passageMode: 'single_passage',
        passageRequired: 'Yes',
        questionType: 'PASSAGE_BASED_MCQ',
        passageQuestionCount: totalQuestions,
        passageCount: totalQuestions === 50 ? 10 : 1,
        passageSingleCount: totalQuestions,
        passageMultiCount: 0,
        singleChoiceCount: totalQuestions,
        multiChoiceCount: 0,
        independentSingleCount: 0,
        independentMultiCount: 0
      });
    } else {
      updateFields({
        passageMode: 'independent',
        passageRequired: 'No',
        questionType: 'DISCRETE_MCQ',
        passageQuestionCount: 0,
        passageCount: 0,
        passageSingleCount: 0,
        passageMultiCount: 0,
        singleChoiceCount: totalQuestions,
        multiChoiceCount: 0,
        independentSingleCount: totalQuestions,
        independentMultiCount: 0
      });
    }
  };

  const handleNext = useCallback(() => {
    if (step < totalSteps) {
      setStep(prev => prev + 1);
    } else {
      (onGenerateQuestions || onLaunchGeneration)?.();
    }
  }, [step, totalSteps, onGenerateQuestions, onLaunchGeneration, setStep]);

  const handleInstantLaunch = useCallback(() => {
    (onGenerateQuestions || onLaunchGeneration)?.();
  }, [onGenerateQuestions, onLaunchGeneration]);

  const handleBack = () => {
    if (step > 1) {
      setStep(prev => prev - 1);
    }
  };

  const handleApplyQuickPreset = (preset) => {
    handleSelectSection(preset.section);
    setGenerationTotal(preset.total);
    update('passageRequired', preset.passageRequired);
    update('passageMode', preset.passageMode);
    setStep(3); // Fast track straight to Step 3 Review
  };

  // Keyboard navigation
  const handleKeyDown = useCallback((e) => {
    if ((e.metaKey || e.ctrlKey) && e.key === 'Enter') {
      e.preventDefault();
      (onGenerateQuestions || onLaunchGeneration)?.();
      return;
    }
    if (e.key === 'Enter' && !e.shiftKey && e.target.tagName !== 'TEXTAREA') {
      e.preventDefault();
      handleNext();
    }
  }, [handleNext, onGenerateQuestions, onLaunchGeneration]);

  useEffect(() => {
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [handleKeyDown]);

  const currentStepConfig = STEP_CONFIG[step - 1] || STEP_CONFIG[0];

  return (
    <div className="wizard-card" id="guided-wizard-container">
      {/* Top Navigation & Interactive Progress Tracker */}
      <div className="wizard-topbar">
        <div className="wizard-topbar-header" style={{ marginBottom: '12px' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', width: '100%', flexWrap: 'wrap', gap: '8px' }}>
            <span style={{ fontSize: '0.875rem', color: 'var(--text-secondary)', fontWeight: 600 }}>
              Step {step}: {currentStepConfig.label}
            </span>
            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
              {totalQuestions} Questions
            </span>
          </div>
        </div>

        {/* Interactive Step Pills Tracker (3 Steps) */}
        <div className="wizard-stepper-3" style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '10px', overflowX: 'auto', paddingBottom: '2px' }}>
          {STEP_CONFIG.map((cfg) => {
            const isCurrent = step === cfg.num;
            const isCompleted = step > cfg.num;

            return (
              <button
                key={cfg.num}
                type="button"
                onClick={() => setStep(cfg.num)}
                title={`Jump to Step ${cfg.num}: ${cfg.label}`}
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '7px',
                  padding: '5px 14px',
                  borderRadius: 'var(--radius-full)',
                  fontSize: '0.78rem',
                  fontWeight: isCurrent ? 600 : 500,
                  cursor: 'pointer',
                  background: isCurrent
                    ? 'var(--brand-primary)'
                    : isCompleted
                    ? 'var(--bg-surface-subtle)'
                    : 'var(--bg-surface)',
                  border: isCurrent
                    ? '1px solid var(--brand-primary)'
                    : isCompleted
                    ? '1px solid var(--border-medium)'
                    : '1px solid var(--border-light)',
                  color: isCurrent
                    ? 'var(--text-on-brand)'
                    : isCompleted
                    ? 'var(--text-primary)'
                    : 'var(--text-muted)',
                  transition: 'all 0.15s ease',
                  flexShrink: 0
                }}
              >
                <span
                  style={{
                    width: '18px',
                    height: '18px',
                    borderRadius: '50%',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    fontSize: '0.68rem',
                    background: isCurrent ? 'rgba(255, 255, 255, 0.25)' : 'transparent',
                    fontWeight: 600
                  }}
                >
                  {isCompleted ? <Check size={11} /> : cfg.num}
                </span>
                <span>{cfg.label}</span>
              </button>
            );
          })}
        </div>

        {/* Continuous Progress Track */}
        <div className="wizard-progress-track">
          <div
            className="wizard-progress-fill"
            style={{ width: `${(step / totalSteps) * 100}%` }}
          />
        </div>
      </div>

      {/* Wizard Body: 3 Focused Progressive Steps */}
      <div className="wizard-body wizard-step-fade-enter" key={step}>
        {/* Step 1: Exam Section & Topic Focus */}
        {step === 1 && (
          <WizardStep1SectionFocus
            selectedSection={selectedSection}
            onSelectSection={handleSelectSection}
            SECTION_METADATA={SECTION_METADATA}
            selectedSubject={selectedSubject}
            onSelectSubject={(v) => update('selectedSubject', v)}
            onSelectUnit={(v) => update('selectedUnit', v)}
            selectedTopic={selectedTopic}
            onSelectTopic={(v) => update('selectedTopic', v)}
            onSelectSubtopic={(v) => update('selectedSubtopic', v)}
            selectedSubtopics={selectedSubtopics}
            onToggleSubtopic={toggleSubtopic}
            presets={QUICK_PRESETS}
            onApplyPreset={handleApplyQuickPreset}
            totalQuestions={totalQuestions}
          />
        )}

        {/* Step 2: Challenge Level, Format & Batch Scope */}
        {step === 2 && (
          <WizardStep2LevelFormat
            selectedSection={selectedSection}
            difficulty={difficulty}
            setDifficulty={setDifficulty}
            DIFFICULTY_TIERS={DIFFICULTY_TIERS}
            passageMode={passageMode}
            handlePassageModeChange={handlePassageModeChange}
            questionType={questionType}
            setQuestionType={setQuestionType}
            totalQuestions={totalQuestions}
            setTotalQuestions={setGenerationTotal}
          />
        )}

        {/* Step 3: Review & Multi-Agent Launch (+ Optional Advanced Tuning) */}
        {step === 3 && (
          <WizardStep3ReviewAdvanced
            selectedSection={selectedSection}
            sectionMeta={sectionMeta}
            pacing={pacing}
            setStep={setStep}
            selectedSubject={selectedSubject}
            selectedUnit={selectedUnit}
            selectedTopic={selectedTopic}
            selectedSubtopic={selectedSubtopic}
            selectedSubtopics={selectedSubtopics}
            difficulty={difficulty}
            setDifficulty={setDifficulty}
            totalQuestions={totalQuestions}
            setTotalQuestions={setGenerationTotal}
            questionType={questionType}
            setQuestionType={setQuestionType}
            passageMode={passageMode}
            allowAiImages={allowAiImages}
            setAllowAiImages={setAllowAiImages}
            COGNITIVE_TRAPS={COGNITIVE_TRAPS}
            primaryTrap={primaryTrap}
            setPrimaryTrap={setPrimaryTrap}
            primaryTraps={primaryTraps}
            onTogglePrimaryTrap={togglePrimaryTrap}
            selectedSkill={selectedSkill}
            setSelectedSkill={(v) => update('selectedSkill', v)}
            selectedSubskill={selectedSubskill}
            setSelectedSubskill={(v) => update('selectedSubskill', v)}
            selectedSubskills={selectedSubskills}
            onToggleSubskill={toggleSubskill}
            likelyMistakePattern={likelyMistakePattern}
            setLikelyMistakePattern={(v) => update('likelyMistakePattern', v)}
            likelyMistakePatterns={likelyMistakePatterns}
            onToggleMistakePattern={toggleMistakePattern}
            customMistakePattern={customMistakePattern}
            setCustomMistakePattern={(v) => update('customMistakePattern', v)}
            additionalInstructions={form.additionalInstructions || ''}
            setAdditionalInstructions={(v) => update('additionalInstructions', v)}
          />
        )}
      </div>

      {/* Navigation Footer */}
      <div className="wizard-footer">
        <button
          type="button"
          className="btn-secondary"
          onClick={handleBack}
          disabled={step === 1}
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: '6px',
            opacity: step === 1 ? 0.5 : 1,
            cursor: step === 1 ? 'not-allowed' : 'pointer'
          }}
        >
          <ArrowLeft size={16} />
          <span>Back</span>
        </button>

        {/* Step dots for compact view */}
        <div className="wizard-step-indicators">
          {STEP_CONFIG.map((cfg) => {
            const isClickable = step > cfg.num;
            return (
              <button
                type="button"
                key={cfg.num}
                onClick={() => isClickable && setStep(cfg.num)}
                disabled={!isClickable}
                style={{ cursor: isClickable ? 'pointer' : 'default', padding: 0, border: 'none', background: 'none' }}
                className={`wizard-dot ${step === cfg.num ? 'active' : isClickable ? 'completed' : ''}`}
                title={`Step ${cfg.num}: ${cfg.label}`}
                aria-label={`Go to Step ${cfg.num}: ${cfg.label}`}
              />
            );
          })}
        </div>

        {/* Action Buttons */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          {/* Step 2 Instant Launch Shortcut */}
          {step === 2 && (
            <button
              type="button"
              className="btn-secondary"
              onClick={handleInstantLaunch}
              disabled={isLaunchingBatch}
              title="Start generating immediately"
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '6px',
                padding: '8px 14px',
                fontSize: '0.82rem',
                fontWeight: 600,
                color: 'var(--brand-primary)',
                borderColor: 'var(--border-brand)'
              }}
            >
              <Zap size={14} />
              <span>Quick Start</span>
            </button>
          )}

          <button
            type="button"
            className="workspace-action-btn-primary"
            id={step === totalSteps ? 'btn-wizard-generate-questions' : 'btn-wizard-next-step'}
            onClick={handleNext}
            disabled={step === totalSteps && isLaunchingBatch}
            style={{
              padding: '10px 22px',
              fontSize: '0.92rem',
              opacity: step === totalSteps && isLaunchingBatch ? 0.6 : 1,
              cursor: step === totalSteps && isLaunchingBatch ? 'not-allowed' : 'pointer'
            }}
          >
            {step === totalSteps ? (
              <>
                <Sparkles size={16} className={isLaunchingBatch ? 'spin-icon' : ''} />
                <span>
                  {isLaunchingBatch
                    ? 'Starting...'
                    : `Generate ${totalQuestions} Questions`}
                </span>
              </>
            ) : (
              <>
                <span>{currentStepConfig.nextLabel}</span>
                <ArrowRight size={16} />
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
