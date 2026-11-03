import { Edit3 } from 'lucide-react';

/**
 * WizardReviewSummary
 *
 * Summary card grid displaying current generation parameters (Section, Focus, Difficulty, Format, Count)
 * with quick-jump edit buttons back to corresponding wizard steps.
 */
export default function WizardReviewSummary({
  sectionLabel,
  topicLabel,
  diffLabel,
  formatSummary,
  totalQuestions,
  setStep
}) {
  return (
    <div
      style={{
        background: 'var(--bg-surface)',
        border: '1px solid var(--border-light)',
        borderRadius: 'var(--radius-sm)',
        overflow: 'hidden'
      }}
    >
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
          gap: '1px',
          background: 'var(--border-light)'
        }}
      >
        {/* Section */}
        <div style={{ background: 'var(--bg-surface)', padding: '12px 14px' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '4px' }}>
            <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>Section</span>
            <button
              type="button"
              onClick={() => setStep(1)}
              style={{ background: 'none', border: 'none', padding: 0, color: 'var(--brand-primary)', cursor: 'pointer' }}
              title="Edit Section"
            >
              <Edit3 size={12} />
            </button>
          </div>
          <div style={{ fontSize: '0.88rem', fontWeight: 600, color: 'var(--text-primary)' }}>
            {sectionLabel}
          </div>
        </div>

        {/* Focus */}
        <div style={{ background: 'var(--bg-surface)', padding: '12px 14px' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '4px' }}>
            <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>Topic Focus</span>
            <button
              type="button"
              onClick={() => setStep(1)}
              style={{ background: 'none', border: 'none', padding: 0, color: 'var(--brand-primary)', cursor: 'pointer' }}
              title="Edit Topic"
            >
              <Edit3 size={12} />
            </button>
          </div>
          <div style={{ fontSize: '0.88rem', fontWeight: 600, color: 'var(--text-primary)' }}>
            {topicLabel}
          </div>
        </div>

        {/* Difficulty */}
        <div style={{ background: 'var(--bg-surface)', padding: '12px 14px' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '4px' }}>
            <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>Difficulty</span>
            <button
              type="button"
              onClick={() => setStep(2)}
              style={{ background: 'none', border: 'none', padding: 0, color: 'var(--brand-primary)', cursor: 'pointer' }}
              title="Edit Difficulty"
            >
              <Edit3 size={12} />
            </button>
          </div>
          <div style={{ fontSize: '0.88rem', fontWeight: 600, color: 'var(--text-primary)' }}>
            {diffLabel}
          </div>
        </div>

        {/* Format */}
        <div style={{ background: 'var(--bg-surface)', padding: '12px 14px' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '4px' }}>
            <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>Format</span>
            <button
              type="button"
              onClick={() => setStep(2)}
              style={{ background: 'none', border: 'none', padding: 0, color: 'var(--brand-primary)', cursor: 'pointer' }}
              title="Edit Format"
            >
              <Edit3 size={12} />
            </button>
          </div>
          <div style={{ fontSize: '0.88rem', fontWeight: 600, color: 'var(--text-primary)' }}>
            {formatSummary}
          </div>
        </div>

        {/* Count */}
        <div style={{ background: 'var(--bg-surface)', padding: '12px 14px' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '4px' }}>
            <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>Questions</span>
            <button
              type="button"
              onClick={() => setStep(2)}
              style={{ background: 'none', border: 'none', padding: 0, color: 'var(--brand-primary)', cursor: 'pointer' }}
              title="Edit Count"
            >
              <Edit3 size={12} />
            </button>
          </div>
          <div style={{ fontSize: '0.88rem', fontWeight: 600, color: 'var(--text-primary)' }}>
            {totalQuestions} Questions
          </div>
        </div>
      </div>
    </div>
  );
}

