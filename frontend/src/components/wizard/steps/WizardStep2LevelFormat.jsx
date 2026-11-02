import React from 'react';
import {
  Layers,
  FileText,
  CheckCircle2
} from 'lucide-react';

const DEFAULT_DIFFICULTY_TIERS = [];
const COUNT_OPTIONS = Object.freeze([
  { count: 5, label: '5 Questions' },
  { count: 50, label: '50 Questions' }
]);

export default function WizardStep2LevelFormat({
  selectedSection = 'chem_phys',
  difficulty = 'medium',
  setDifficulty,
  DIFFICULTY_TIERS = DEFAULT_DIFFICULTY_TIERS,
  passageMode = 'single_passage',
  handlePassageModeChange,
  questionType = 'PASSAGE_BASED_MCQ',
  setQuestionType,
  totalQuestions = 50,
  setTotalQuestions
}) {
  const isCars = selectedSection === 'cars';

  const selectPassageMode = (mode) => {
    handlePassageModeChange?.(mode);
    setQuestionType?.(mode === 'single_passage' ? 'PASSAGE_BASED_MCQ' : 'DISCRETE_MCQ');
  };

  const isPassage = isCars || passageMode === 'single_passage' || questionType === 'PASSAGE_BASED_MCQ';

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
      <div className="wizard-heading-group">
        <h2 className="wizard-step-title">Difficulty &amp; Format</h2>
      </div>

      {/* Difficulty */}
      <div className="wizard-stacked-decision">
        <div className="wizard-decision-header">
          <span className="wizard-decision-title">Difficulty Level</span>
        </div>

        <div className="wizard-difficulty-grid" style={{ gridTemplateColumns: 'repeat(3, 1fr)', gap: '10px' }}>
          {DIFFICULTY_TIERS.map((tier) => {
            const diffNormalized = (difficulty || '').toLowerCase();
            const tierId = tier.id.toLowerCase();
            const isSelected = diffNormalized === tierId ||
              (tierId === 'low' && diffNormalized === 'easy') ||
              (tierId === 'high' && diffNormalized === 'hard');

            return (
              <div
                key={tier.id}
                className={`wizard-tier-card ${isSelected ? 'selected' : ''}`}
                onClick={() => setDifficulty?.(tier.id)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    setDifficulty?.(tier.id);
                  }
                }}
                role="button"
                tabIndex={0}
                aria-pressed={isSelected}
                style={{ padding: '12px 14px' }}
              >
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                  <div className="wizard-tier-title" style={{ fontSize: '0.88rem', margin: 0, display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <span
                      style={{
                        width: '8px',
                        height: '8px',
                        borderRadius: '50%',
                        backgroundColor: tier.color || 'var(--brand-primary)',
                        display: 'inline-block',
                        flexShrink: 0
                      }}
                    />
                    {tier.title}
                  </div>
                  {isSelected && (
                    <CheckCircle2 size={14} style={{ color: 'var(--brand-primary)', flexShrink: 0 }} />
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Passage & Question Format */}
      <div className="wizard-stacked-decision">
        <div className="wizard-decision-header">
          <span className="wizard-decision-title">Question Format</span>
        </div>

        {isCars ? (
          /* CARS Mode: Strictly 100% Passage-Based */
          <div
            style={{
              padding: '12px 14px',
              borderRadius: 'var(--radius-sm)',
              background: 'var(--bg-surface-subtle)',
              border: '1px solid var(--border-light)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              gap: '12px'
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <FileText size={16} style={{ color: 'var(--brand-primary)', flexShrink: 0 }} />
              <div>
                <span style={{ fontSize: '0.86rem', fontWeight: 600, color: 'var(--text-primary)' }}>
                  Passage-Based (CARS)
                </span>
              </div>
            </div>
          </div>
        ) : (
          /* Sciences Mode: Binary choice between Passage-Based MCQ OR Independent MCQ */
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '10px' }}>
            {/* Mode A: Reading Passage + Questions */}
            <div
              className={`wizard-tier-card ${isPassage ? 'selected' : ''}`}
              onClick={() => selectPassageMode('single_passage')}
              onKeyDown={(e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                  e.preventDefault();
                  selectPassageMode('single_passage');
                }
              }}
              role="button"
              tabIndex={0}
              id="btn-question-type-passage"
              style={{ padding: '12px 14px' }}
            >
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <FileText size={15} style={{ color: 'var(--brand-primary)', flexShrink: 0 }} />
                  <div>
                    <span style={{ fontSize: '0.86rem', fontWeight: 600, color: 'var(--text-primary)' }}>
                      Passage-Based
                    </span>
                  </div>
                </div>
                {isPassage && (
                  <CheckCircle2 size={14} style={{ color: 'var(--brand-primary)', flexShrink: 0 }} />
                )}
              </div>
            </div>

            {/* Mode B: Standalone Questions */}
            <div
              className={`wizard-tier-card ${!isPassage ? 'selected' : ''}`}
              onClick={() => selectPassageMode('independent')}
              onKeyDown={(e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                  e.preventDefault();
                  selectPassageMode('independent');
                }
              }}
              role="button"
              tabIndex={0}
              id="btn-question-type-independent"
              style={{ padding: '12px 14px' }}
            >
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <Layers size={15} style={{ color: 'var(--status-purple)', flexShrink: 0 }} />
                  <div>
                    <span style={{ fontSize: '0.86rem', fontWeight: 600, color: 'var(--text-primary)' }}>
                      Standalone
                    </span>
                  </div>
                </div>
                {!isPassage && (
                  <CheckCircle2 size={14} style={{ color: 'var(--brand-primary)', flexShrink: 0 }} />
                )}
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Question Count (Strictly 5 or 50) */}
      <div className="wizard-stacked-decision">
        <div className="wizard-decision-header">
          <span className="wizard-decision-title">Question Count</span>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '10px' }}>
          {COUNT_OPTIONS.map((opt) => {
            const isSelected = totalQuestions === opt.count;
            return (
              <div
                key={opt.count}
                className={`wizard-tier-card ${isSelected ? 'selected' : ''}`}
                onClick={() => setTotalQuestions?.(opt.count)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    setTotalQuestions?.(opt.count);
                  }
                }}
                role="button"
                tabIndex={0}
                aria-pressed={isSelected}
                style={{
                  padding: '14px 16px',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  cursor: 'pointer'
                }}
              >
                <div>
                  <div style={{ fontSize: '0.96rem', fontWeight: 700, color: isSelected ? 'var(--brand-primary)' : 'var(--text-primary)' }}>
                    {opt.label}
                  </div>
                </div>
                {isSelected && (
                  <CheckCircle2 size={16} style={{ color: 'var(--brand-primary)', flexShrink: 0 }} />
                )}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
