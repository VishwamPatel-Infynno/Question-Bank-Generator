import React from 'react';
import { ChevronDown, ChevronUp, Sliders, CheckCircle2 } from 'lucide-react';

/**
 * WizardAdvancedSettings
 *
 * Collapsible advanced parameters accordion for Wizard Step 3:
 * Cognitive Traps, AAMC Reasoning Skills, Common Student Mistakes, and Additional Authoring Instructions.
 */
export default function WizardAdvancedSettings({
  showAdvanced = false,
  setShowAdvanced,
  hasInstructions = false,
  effectiveTraps = [],
  COGNITIVE_TRAPS = [],
  onTogglePrimaryTrap,
  setPrimaryTrap,
  availableSubskills = [],
  effectiveSubskills = [],
  onToggleSubskill,
  setSelectedSubskill,
  effectiveMistakes = [],
  LIKELY_MISTAKE_PATTERNS = [],
  onToggleMistakePattern,
  setLikelyMistakePattern,
  additionalInstructions = '',
  setAdditionalInstructions
}) {
  return (
    <div
      style={{
        border: '1px solid var(--border-light)',
        borderRadius: 'var(--radius-sm)',
        background: 'var(--bg-surface)',
        overflow: 'hidden'
      }}
    >
      <button
        type="button"
        onClick={() => setShowAdvanced?.((prev) => !prev)}
        style={{
          width: '100%',
          padding: '12px 16px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          background: 'var(--bg-surface-subtle)',
          border: 'none',
          cursor: 'pointer',
          fontSize: '0.82rem',
          fontWeight: 600,
          color: 'var(--text-primary)'
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
          <Sliders size={14} style={{ color: 'var(--brand-primary)' }} />
          <span>Advanced Settings</span>
          <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)', fontWeight: 400 }}>
            (Common Traps, Reasoning Skills, Student Mistakes)
          </span>
          {hasInstructions && (
            <span
              className="badge-minimal"
              style={{
                fontSize: '0.68rem',
                color: 'var(--brand-primary)',
                border: '1px solid var(--border-brand)',
                background: 'var(--brand-light)',
                padding: '1px 7px',
                fontWeight: 600
              }}
            >
              Custom Instructions Active
            </span>
          )}
        </div>
        {showAdvanced ? <ChevronUp size={15} /> : <ChevronDown size={15} />}
      </button>

      {showAdvanced && (
        <div style={{ padding: '16px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
          {/* Cognitive Traps */}
          <div>
            <div style={{ fontSize: '0.78rem', fontWeight: 600, color: 'var(--text-primary)', marginBottom: '8px' }}>
              Common Traps to Test
            </div>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
              <button
                type="button"
                onClick={() => {
                  if (onTogglePrimaryTrap) onTogglePrimaryTrap('Automatic');
                  else setPrimaryTrap?.('Automatic');
                }}
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '5px',
                  padding: '4px 10px',
                  borderRadius: 'var(--radius-full)',
                  background: effectiveTraps.length === 0 ? 'var(--status-purple)' : 'var(--bg-surface-subtle)',
                  border: effectiveTraps.length === 0 ? '1px solid var(--status-purple)' : '1px solid var(--border-light)',
                  color: effectiveTraps.length === 0 ? 'var(--text-on-brand, #ffffff)' : 'var(--text-secondary)',
                  fontSize: '0.72rem',
                  fontWeight: effectiveTraps.length === 0 ? 600 : 500,
                  cursor: 'pointer'
                }}
              >
                {effectiveTraps.length === 0 && <CheckCircle2 size={11} />}
                <span>Automatic (Balanced Mix)</span>
              </button>

              {(COGNITIVE_TRAPS || []).filter((t) => t.id !== 'Automatic').map((trap) => {
                const isSelected = effectiveTraps.includes(trap.id);
                return (
                  <button
                    key={trap.id}
                    type="button"
                    onClick={() => {
                      if (onTogglePrimaryTrap) onTogglePrimaryTrap(trap.id);
                      else setPrimaryTrap?.(trap.id);
                    }}
                    style={{
                      display: 'inline-flex',
                      alignItems: 'center',
                      gap: '5px',
                      padding: '4px 10px',
                      borderRadius: 'var(--radius-full)',
                      background: isSelected ? 'var(--status-purple)' : 'var(--bg-surface-subtle)',
                      border: isSelected ? '1px solid var(--status-purple)' : '1px solid var(--border-light)',
                      color: isSelected ? 'var(--text-on-brand, #ffffff)' : 'var(--text-secondary)',
                      fontSize: '0.72rem',
                      fontWeight: isSelected ? 600 : 500,
                      cursor: 'pointer'
                    }}
                  >
                    {isSelected && <CheckCircle2 size={11} />}
                    <span>{trap.label}</span>
                  </button>
                );
              })}
            </div>
          </div>

          {/* Subskills Selection */}
          {availableSubskills.length > 0 && (
            <div>
              <div style={{ fontSize: '0.78rem', fontWeight: 600, color: 'var(--text-primary)', marginBottom: '8px' }}>
                Exam Reasoning Skills
              </div>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
                <button
                  type="button"
                  onClick={() => {
                    if (onToggleSubskill) onToggleSubskill('All');
                    else setSelectedSubskill?.('');
                  }}
                  style={{
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: '5px',
                    padding: '4px 10px',
                    borderRadius: 'var(--radius-full)',
                    background: effectiveSubskills.length === 0 ? 'var(--brand-primary)' : 'var(--bg-surface-subtle)',
                    border: effectiveSubskills.length === 0 ? '1px solid var(--brand-primary)' : '1px solid var(--border-light)',
                    color: effectiveSubskills.length === 0 ? 'var(--text-on-brand)' : 'var(--text-secondary)',
                    fontSize: '0.72rem',
                    fontWeight: effectiveSubskills.length === 0 ? 600 : 500,
                    cursor: 'pointer'
                  }}
                >
                  {effectiveSubskills.length === 0 && <CheckCircle2 size={11} />}
                  <span>All Skills</span>
                </button>

                {availableSubskills.map((subsk) => {
                  const isSubSelected = effectiveSubskills.includes(subsk);
                  return (
                    <button
                      key={subsk}
                      type="button"
                      onClick={() => {
                        if (onToggleSubskill) onToggleSubskill(subsk);
                        else setSelectedSubskill?.(subsk);
                      }}
                      style={{
                        display: 'inline-flex',
                        alignItems: 'center',
                        gap: '5px',
                        padding: '4px 10px',
                        borderRadius: 'var(--radius-full)',
                        background: isSubSelected ? 'var(--brand-primary)' : 'var(--bg-surface-subtle)',
                        border: isSubSelected ? '1px solid var(--brand-primary)' : '1px solid var(--border-light)',
                        color: isSubSelected ? 'var(--text-on-brand)' : 'var(--text-secondary)',
                        fontSize: '0.72rem',
                        fontWeight: isSubSelected ? 600 : 500,
                        cursor: 'pointer'
                      }}
                    >
                      {isSubSelected && <CheckCircle2 size={11} />}
                      <span>{subsk}</span>
                    </button>
                  );
                })}
              </div>
            </div>
          )}

          {/* Misconception Patterns */}
          <div>
            <div style={{ fontSize: '0.78rem', fontWeight: 600, color: 'var(--text-primary)', marginBottom: '8px' }}>
              Common Student Mistakes to Target
            </div>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
              <button
                type="button"
                onClick={() => {
                  if (onToggleMistakePattern) onToggleMistakePattern('Automatic');
                  else setLikelyMistakePattern?.('Automatic');
                }}
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '5px',
                  padding: '4px 10px',
                  borderRadius: 'var(--radius-full)',
                  background: effectiveMistakes.length === 0 ? 'var(--brand-primary)' : 'var(--bg-surface-subtle)',
                  border: effectiveMistakes.length === 0 ? '1px solid var(--brand-primary)' : '1px solid var(--border-light)',
                  color: effectiveMistakes.length === 0 ? 'var(--text-on-brand)' : 'var(--text-secondary)',
                  fontSize: '0.72rem',
                  fontWeight: effectiveMistakes.length === 0 ? 600 : 500,
                  cursor: 'pointer'
                }}
              >
                {effectiveMistakes.length === 0 && <CheckCircle2 size={11} />}
                <span>Automatic (Recommended)</span>
              </button>

              {(LIKELY_MISTAKE_PATTERNS || []).slice(0, 8).map((mp) => {
                const isSelected = effectiveMistakes.includes(mp.label) || effectiveMistakes.includes(mp.id);
                return (
                  <button
                    key={mp.id}
                    type="button"
                    onClick={() => {
                      if (onToggleMistakePattern) onToggleMistakePattern(mp.label);
                      else setLikelyMistakePattern?.(mp.label);
                    }}
                    style={{
                      display: 'inline-flex',
                      alignItems: 'center',
                      gap: '5px',
                      padding: '4px 10px',
                      borderRadius: 'var(--radius-full)',
                      background: isSelected ? 'var(--brand-primary)' : 'var(--bg-surface-subtle)',
                      border: isSelected ? '1px solid var(--brand-primary)' : '1px solid var(--border-light)',
                      color: isSelected ? 'var(--text-on-brand)' : 'var(--text-secondary)',
                      fontSize: '0.72rem',
                      fontWeight: isSelected ? 600 : 500,
                      cursor: 'pointer'
                    }}
                  >
                    {isSelected && <CheckCircle2 size={11} />}
                    <span>{mp.label}</span>
                  </button>
                );
              })}
            </div>
          </div>

          {/* Additional Authoring Instructions */}
          <div>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
              <label
                htmlFor="wizard-additional-instructions"
                style={{ fontSize: '0.78rem', fontWeight: 600, color: 'var(--text-primary)' }}
              >
                Additional Authoring Instructions
              </label>
              {hasInstructions && (
                <span className="badge-minimal" style={{ fontSize: '0.68rem', color: 'var(--brand-primary)' }}>
                  Active
                </span>
              )}
            </div>
            <textarea
              id="wizard-additional-instructions"
              rows={3}
              value={additionalInstructions}
              onChange={(e) => setAdditionalInstructions?.(e.target.value)}
              placeholder="e.g. Emphasize Lineweaver-Burk kinetic derivations; incorporate a competitive inhibitor with Ki = 2.5 uM; avoid complex trigonometric arithmetic..."
              style={{
                width: '100%',
                padding: '10px 12px',
                fontSize: '0.82rem',
                borderRadius: 'var(--radius-sm)',
                border: '1px solid var(--border-light)',
                background: 'var(--bg-surface-subtle)',
                color: 'var(--text-primary)',
                resize: 'vertical',
                fontFamily: 'inherit',
                lineHeight: 1.5,
                outline: 'none',
                boxSizing: 'border-box'
              }}
            />
          </div>
        </div>
      )}
    </div>
  );
}

