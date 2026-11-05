import React, { useState, useEffect, useCallback } from 'react';
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
import { STEP_CONFIG, QUICK_PRESETS } from './wizardConstants';
import WizardHeaderStepper from './WizardHeaderStepper';
import WizardFooterNav from './WizardFooterNav';

/**
 * GuidedWizard - Coordinates multi-step question generation configuration.
 */
export default function GuidedWizard({
  generatorForm,
  onGenerateQuestions,
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
        passageCount: totalQuestions === 50 ? 10 : 1
      });
    } else {
      updateFields({
        passageMode: 'independent',
        passageRequired: 'No',
        questionType: 'DISCRETE_MCQ',
        passageQuestionCount: 0,
        passageCount: 0
      });
    }
  };

  const handleNext = useCallback(() => {
    if (step < totalSteps) {
      setStep(prev => prev + 1);
    } else {
      onGenerateQuestions?.();
    }
  }, [step, totalSteps, onGenerateQuestions, setStep]);

  const handleInstantLaunch = useCallback(() => {
    onGenerateQuestions?.();
  }, [onGenerateQuestions]);

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
      onGenerateQuestions?.();
      return;
    }
    if (e.key === 'Enter' && !e.shiftKey && e.target.tagName !== 'TEXTAREA') {
      e.preventDefault();
      handleNext();
    }
  }, [handleNext, onGenerateQuestions]);

  useEffect(() => {
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [handleKeyDown]);

  const currentStepConfig = STEP_CONFIG[step - 1] || STEP_CONFIG[0];

  return (
    <div className="wizard-card" id="guided-wizard-container">
      {/* Top Navigation & Interactive Progress Tracker */}
      <WizardHeaderStepper
        step={step}
        totalSteps={totalSteps}
        currentStepConfig={currentStepConfig}
        totalQuestions={totalQuestions}
        onStepClick={setStep}
        stepConfig={STEP_CONFIG}
      />

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
            selectedSubtopic={(v) => update('selectedSubtopic', v)}
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
      <WizardFooterNav
        step={step}
        totalSteps={totalSteps}
        currentStepConfig={currentStepConfig}
        totalQuestions={totalQuestions}
        isLaunchingBatch={isLaunchingBatch}
        onBack={handleBack}
        onNext={handleNext}
        onInstantLaunch={handleInstantLaunch}
        onStepClick={setStep}
        stepConfig={STEP_CONFIG}
      />
    </div>
  );
}
