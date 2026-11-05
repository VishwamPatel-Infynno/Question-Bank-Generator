import { ChevronDown, ChevronUp, Sliders, CheckCircle2 } from 'lucide-react';
import { EMPTY_ARRAY } from '../../../constants';

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
  effectiveTraps = EMPTY_ARRAY,
  COGNITIVE_TRAPS = EMPTY_ARRAY,
  onTogglePrimaryTrap,
  setPrimaryTrap,
  availableSubskills = EMPTY_ARRAY,
  effectiveSubskills = EMPTY_ARRAY,
  onToggleSubskill,
  setSelectedSubskill,
  effectiveMistakes = EMPTY_ARRAY,
  LIKELY_MISTAKE_PATTERNS = EMPTY_ARRAY,
  onToggleMistakePattern,
  setLikelyMistakePattern,
  additionalInstructions = '',
  setAdditionalInstructions
}) {
  return (
    <div className="wizard-advanced-card">
      <button
        type="button"
        onClick={() => setShowAdvanced?.((prev) => !prev)}
        className="wizard-advanced-toggle"
      >
        <div className="wizard-advanced-toggle-content">
          <Sliders size={14} color="var(--brand-primary)" />
          <span>Advanced Settings</span>
          {hasInstructions && (
            <span className="badge-minimal">
              + Custom Prompt Active
            </span>
          )}
        </div>
        {showAdvanced ? <ChevronUp size={15} /> : <ChevronDown size={15} />}
      </button>

      {showAdvanced && (
        <div className="wizard-advanced-panel">
          {/* Cognitive Traps */}
          <div>
            <div className="wizard-advanced-section-title">
              Test Traps
            </div>
            <div className="wizard-chips-list">
              <button
                type="button"
                onClick={() => {
                  if (onTogglePrimaryTrap) onTogglePrimaryTrap('Automatic');
                  else setPrimaryTrap?.('Automatic');
                }}
                className={`wizard-purple-chip ${effectiveTraps.length === 0 ? 'active' : ''}`}
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
                    className={`wizard-purple-chip ${isSelected ? 'active' : ''}`}
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
              <div className="wizard-advanced-section-title">
                Reasoning Skills
              </div>
              <div className="wizard-chips-list">
                <button
                  type="button"
                  onClick={() => {
                    if (onToggleSubskill) onToggleSubskill('All');
                    else setSelectedSubskill?.('');
                  }}
                  className={`wizard-filter-chip ${effectiveSubskills.length === 0 ? 'active' : ''}`}
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
                      className={`wizard-filter-chip ${isSubSelected ? 'active' : ''}`}
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
            <div className="wizard-advanced-section-title">
              Student Mistakes
            </div>
            <div className="wizard-chips-list">
              <button
                type="button"
                onClick={() => {
                  if (onToggleMistakePattern) onToggleMistakePattern('Automatic');
                  else setLikelyMistakePattern?.('Automatic');
                }}
                className={`wizard-filter-chip ${effectiveMistakes.length === 0 ? 'active' : ''}`}
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
                    className={`wizard-filter-chip ${isSelected ? 'active' : ''}`}
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
            <div className="wizard-advanced-header-row">
              <label
                htmlFor="wizard-additional-instructions"
                className="wizard-advanced-section-title no-margin"
              >
                Additional Instructions
              </label>
              {hasInstructions && (
                <span className="badge-minimal">
                  Active
                </span>
              )}
            </div>
            <textarea
              id="wizard-additional-instructions"
              rows={3}
              value={additionalInstructions}
              onChange={(e) => setAdditionalInstructions?.(e.target.value)}
              placeholder="e.g. Focus on enzyme pathways; keep math calculations simple; include a clinical scenario..."
              className="wizard-instructions-textarea"
            />
          </div>
        </div>
      )}
    </div>
  );
}
