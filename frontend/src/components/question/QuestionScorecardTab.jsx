import React from 'react';

/**
 * QuestionScorecardTab:
 * Renders the 100-point psychometric rubric breakdown tab, displaying
 * the overall quality score and four pillar metric progress bars.
 *
 * Props:
 * - question: object - The question instance containing final_score and review_rubric
 * - pillars: Array<{ label: string, score: number, max: number, color: string }>
 */
const EMPTY_PILLARS = [];

export default function QuestionScorecardTab({ question, pillars = EMPTY_PILLARS }) {
  if (!question) return null;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div>
          <h4 style={{ fontSize: '0.9rem', fontWeight: 700, color: 'var(--text-primary)', margin: 0 }}>
            Quality Scorecard
          </h4>
        </div>
        <span className="badge badge-emerald" style={{ fontSize: '0.8rem', padding: '4px 10px' }}>
          Score: {question.final_score}/100
        </span>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '10px' }}>
        {pillars.map(p => (
          <div
            key={p.label}
            style={{
              background: 'var(--bg-surface-elevated)',
              border: '1px solid var(--border-light)',
              borderRadius: 'var(--radius-sm)',
              padding: '12px 14px'
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '6px', fontSize: '0.775rem' }}>
              <span style={{ fontWeight: 600, color: 'var(--text-primary)' }}>{p.label}</span>
              <span style={{ fontWeight: 700, color: p.color }}>{p.score}/{p.max}</span>
            </div>
            <div style={{ width: '100%', height: '4px', background: 'var(--bg-app)', borderRadius: '2px', overflow: 'hidden' }}>
              <div style={{ width: `${(p.score / p.max) * 100}%`, height: '100%', background: p.color, borderRadius: '2px' }} />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
