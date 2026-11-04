import { Check } from 'lucide-react';
import { STEP_CONFIG as DEFAULT_STEP_CONFIG } from './wizardConstants';

/**
 * WizardHeaderStepper - Interactive step tracker and progress bar for the question generator wizard.
 */
export default function WizardHeaderStepper({
  step = 1,
  totalSteps = 3,
  currentStepConfig,
  totalQuestions = 50,
  onStepClick,
  stepConfig = DEFAULT_STEP_CONFIG
}) {
  const activeConfig = currentStepConfig || stepConfig[step - 1] || stepConfig[0];

  return (
    <div className="wizard-topbar">
      <div className="wizard-topbar-header">
        <div className="wizard-stepper-meta">
          <span className="wizard-stepper-step-label">
            Step {step}: {activeConfig?.label}
          </span>
          <span className="wizard-stepper-count-label">
            {totalQuestions} Questions
          </span>
        </div>
      </div>

      {/* Interactive Step Pills Tracker (3 Steps) */}
      <div className="wizard-stepper-3 wizard-stepper-track">
        {stepConfig.map((cfg) => {
          const isCurrent = step === cfg.num;
          const isCompleted = step > cfg.num;

          return (
            <button
              key={cfg.num}
              type="button"
              onClick={() => onStepClick?.(cfg.num)}
              title={`Jump to Step ${cfg.num}: ${cfg.label}`}
              className={`wizard-stepper-pill ${isCurrent ? 'current' : isCompleted ? 'completed' : ''}`}
            >
              <span className={`wizard-stepper-circle ${isCurrent ? 'current' : isCompleted ? 'completed' : ''}`}>
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
  );
}
