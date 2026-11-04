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
        className="btn-secondary"
        onClick={onBack}
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
        {stepConfig.map((cfg) => {
          const isClickable = step > cfg.num;
          return (
            <button
              type="button"
              key={cfg.num}
              onClick={() => isClickable && onStepClick?.(cfg.num)}
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
            onClick={onInstantLaunch}
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
          onClick={onNext}
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
              <span>{activeConfig?.nextLabel}</span>
              <ArrowRight size={16} />
            </>
          )}
        </button>
      </div>
    </div>
  );
}

