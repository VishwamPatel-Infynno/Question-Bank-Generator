import React from 'react';
import { ArrowLeft, ArrowRight, Sparkles, Zap } from 'lucide-react';
import { STEP_CONFIG as DEFAULT_STEP_CONFIG } from './wizardConstants';

/**
 * WizardFooterNav - Sticky bottom navigation controls and action buttons for GuidedWizard.
 */
export default function WizardFooterNav({
  step = 1,
  totalSteps = 3,
  currentStepConfig,
  totalQuestions = 50,
  isLaunchingBatch = false,
  onBack,
  onNext,
  onInstantLaunch,
  onStepClick,
  stepConfig = DEFAULT_STEP_CONFIG
}) {
  const activeConfig = currentStepConfig || stepConfig[step - 1] || stepConfig[0];

  return (
    <div className="wizard-footer">
      <button
        type="button"
        className="btn-secondary wizard-footer-back-btn"
        onClick={onBack}
        disabled={step === 1}
      >
        <ArrowLeft size={16} />
        <span>Back</span>
      </button>

      {/* Step dots for compact view */}
      <div className="wizard-step-indicators">
        {stepConfig.map((cfg) => {
          const isClickable = step > cfg.num;
          return (
            <button
              type="button"
              key={cfg.num}
              onClick={() => isClickable && onStepClick?.(cfg.num)}
              disabled={!isClickable}
              className={`wizard-dot wizard-footer-stepper-btn ${step === cfg.num ? 'active' : isClickable ? 'completed' : ''} ${!isClickable ? 'disabled' : ''}`}
              title={`Step ${cfg.num}: ${cfg.label}`}
              aria-label={`Go to Step ${cfg.num}: ${cfg.label}`}
            />
          );
        })}
      </div>

      {/* Action Buttons */}
      <div className="wizard-footer-actions">
        {/* Step 2 Instant Launch Shortcut */}
        {step === 2 && (
          <button
            type="button"
            className="btn-secondary wizard-footer-quick-btn"
            onClick={onInstantLaunch}
            disabled={isLaunchingBatch}
            title="Start generating immediately"
          >
            <Zap size={14} />
            <span>Quick Start</span>
          </button>
        )}

        <button
          type="button"
          className="workspace-action-btn-primary wizard-footer-next-btn"
          id={step === totalSteps ? 'btn-wizard-generate-questions' : 'btn-wizard-next-step'}
          onClick={onNext}
          disabled={step === totalSteps && isLaunchingBatch}
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
              <span>{activeConfig?.nextLabel}</span>
              <ArrowRight size={16} />
            </>
          )}
        </button>
      </div>
    </div>
  );
}

