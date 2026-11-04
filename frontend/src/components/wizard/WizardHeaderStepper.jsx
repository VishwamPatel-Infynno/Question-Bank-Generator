import React from 'react';
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
      <div className="wizard-topbar-header" style={{ marginBottom: '12px' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', width: '100%', flexWrap: 'wrap', gap: '8px' }}>
          <span style={{ fontSize: '0.875rem', color: 'var(--text-secondary)', fontWeight: 600 }}>
            Step {step}: {activeConfig?.label}
          </span>
          <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
            {totalQuestions} Questions
          </span>
        </div>
      </div>

      {/* Interactive Step Pills Tracker (3 Steps) */}
      <div className="wizard-stepper-3" style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '10px', overflowX: 'auto', paddingBottom: '2px' }}>
        {stepConfig.map((cfg) => {
          const isCurrent = step === cfg.num;
          const isCompleted = step > cfg.num;

          return (
            <button
              key={cfg.num}
              type="button"
              onClick={() => onStepClick?.(cfg.num)}
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
  );
}

