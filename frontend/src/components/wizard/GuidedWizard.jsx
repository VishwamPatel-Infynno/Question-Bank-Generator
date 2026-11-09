import { useState, useCallback } from 'react';
import { applySectionRules } from '../../utils/generatorFormState';
import { SECTION_METADATA, DIFFICULTY, SECTION_IDS } from '../../constants';
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

  const selectedSection = form.selectedSection || SECTION_IDS.CHEM_PHYS;
  const selectedSubject = form.selectedSubject || '';
  const selectedTopic = form.selectedTopic || '';
  const questionType = form.questionType || 'PASSAGE_BASED_MCQ';
  const difficulty = form.difficulty || DIFFICULTY.MEDIUM;
  const totalQuestions = form.totalQuestions || 50;
  const setGenerationTotal = generatorForm?.setGenerationTotal || ((t) => update('totalQuestions', t));
  const selectedSubtopics = form.selectedSubtopics || [];

  const toggleSubtopic = generatorForm?.toggleSubtopic;

  const setDifficulty = (v) => update('difficulty', v);
  const setQuestionType = (v) => update('questionType', v);
  const passageMode = form.passageMode || 'single_passage';

  const sectionMeta = SECTION_METADATA[selectedSection] || SECTION_METADATA.chem_phys;

  // Section Selection handler
  const handleSelectSection = (sectionId) => {
    updateFields(applySectionRules(form, sectionId));
  };

  const handlePassageModeChange = (mode) => {
    if (mode === 'single_passage') {
      updateFields({
        passageMode: 'single_passage',
        passageRequired: 'Yes',
        questionType: 'PASSAGE_BASED_MCQ',
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

  // Cmd/Ctrl+Enter on the review step is handled once, by useKeyboardShortcuts in useAppState;
  // plain Enter is left to the focused control (cards and buttons activate themselves).

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
            selectedSubject={selectedSubject}
            onSelectSubject={(v) => update('selectedSubject', v)}
            onSelectUnit={(v) => update('selectedUnit', v)}
            selectedTopic={selectedTopic}
            onSelectTopic={(id, name) => updateFields({ selectedTopic: id, selectedTopicName: name || '' })}
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
          <WizardStep3ReviewAdvanced generatorForm={generatorForm} sectionMeta={sectionMeta} setStep={setStep} />
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
