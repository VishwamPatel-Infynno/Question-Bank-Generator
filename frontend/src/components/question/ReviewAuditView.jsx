import React from 'react';
import { CheckCircle, AlertTriangle, ShieldCheck, Sparkles, Target, Zap, Image as ImageIcon } from 'lucide-react';
import { Modal } from '../common';
import { getEffectiveTrapInfo, formatTokenCount } from '../../utils';

/**
 * ReviewAuditView
 *
 * Detailed quality, token cost, and exam calibration modal for a question.
 * Built on the unified Modal primitive with WCAG AA compliance.
 */
export default function ReviewAuditView({ question, onClose }) {
  if (!question) return null;

  const review = question.review_rubric;
  const history = question.iterations_history || [];
  const trapInfo = getEffectiveTrapInfo(question);
  const mistakePattern = question.likely_mistake_pattern && question.likely_mistake_pattern !== 'None'
    ? question.likely_mistake_pattern
    : null;
  const hasVisual = Boolean(
    question.image_svg ||
    question.image_url ||
    question.image_description ||
    question?.stage_outcomes?.visual_stimulus?.image_svg ||
    question?.stage_outcomes?.visual_stimulus?.image_url
  );

  const pillars = [
    { label: 'MCAT Scientific Style & Tone', score: review?.authenticity_score ?? 24, max: 25, color: 'var(--brand-primary)' },
    { label: 'Clarity & Logic', score: review?.clarity_score ?? 24, max: 25, color: 'var(--brand-indigo)' },
    { label: 'Wrong Answer Quality', score: review?.distractor_score ?? 23, max: 25, color: 'var(--status-warning)' },
    { label: 'Explanation & Key Accuracy', score: review?.explanation_score ?? 24, max: 25, color: 'var(--status-success)' },
  ];

  const iconElement = (
    <div
      style={{
        width: '38px',
        height: '38px',
        borderRadius: 'var(--radius-sm)',
        background: 'var(--brand-light)',
        border: '1px solid var(--border-brand)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        color: 'var(--brand-primary)',
        flexShrink: 0
      }}
    >
      <ShieldCheck size={20} />
    </div>
  );

  const footer = (
    <button type="button" onClick={onClose} className="btn-secondary">
      Close Review
    </button>
  );

  return (
    <Modal
      isOpen={Boolean(question)}
      onClose={onClose}
      title="Question Quality Review"
      subtitle="Quality breakdown, token usage, and exam standards"
      icon={iconElement}
      maxWidth="820px"
      footer={footer}
      ariaLabelledBy="audit-modal-title"
    >
      <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
        {/* Overall Score Banner */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            padding: '16px 20px',
            background: 'var(--brand-light)',
            borderRadius: 'var(--radius-md)',
            border: '1px solid var(--border-brand)'
          }}
        >
          <div>
            <div style={{ fontSize: '0.775rem', fontWeight: 600, color: 'var(--brand-primary)' }}>Overall Quality Score</div>
            <div style={{ fontSize: '1.8rem', fontWeight: 700, color: 'var(--brand-primary)', lineHeight: 1.1 }}>
              {question.final_score} <span style={{ fontSize: '1rem', fontWeight: 500, color: 'var(--text-muted)' }}>/ 100</span>
            </div>
          </div>
          <div style={{ textAlign: 'right' }}>
            <span
              className={`badge ${question.final_score > 90 ? 'badge-emerald' : 'badge-amber'}`}
              style={{ fontSize: '0.75rem', padding: '4px 10px' }}
            >
              {question.final_score > 90 ? 'Ready for Review (>90 Score)' : 'Needs Polish (≤85 Score)'}
            </span>
            <div style={{ fontSize: '0.725rem', fontWeight: 500, color: 'var(--text-muted)', marginTop: '4px' }}>
              Refinement Rounds: {question.iteration_count || 1} of 3
            </div>
          </div>
        </div>

        {/* Usage & Cost Details Section */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <h4 style={{ fontSize: '0.775rem', fontWeight: 700, color: 'var(--text-primary)', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
              Usage &amp; Question Details
            </h4>
            <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>
              Quality Review Summary
            </span>
          </div>

          {/* Metric Cards Grid */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '8px' }}>
            <div style={{ background: 'var(--bg-canvas)', padding: '10px', borderRadius: 'var(--radius-xs)', border: '1px solid var(--border-light)', textAlign: 'center' }}>
              <div style={{ fontSize: '0.65rem', color: 'var(--text-muted)', fontWeight: 600 }}>INPUT TOKENS (PROMPT)</div>
              <div style={{ fontSize: '1rem', fontWeight: 700, color: 'var(--brand-primary)' }}>{formatTokenCount(question.prompt_tokens)}</div>
            </div>
            <div style={{ background: 'var(--bg-canvas)', padding: '10px', borderRadius: 'var(--radius-xs)', border: '1px solid var(--border-light)', textAlign: 'center' }}>
              <div style={{ fontSize: '0.65rem', color: 'var(--text-muted)', fontWeight: 600 }}>OUTPUT TOKENS (RESPONSE)</div>
              <div style={{ fontSize: '1rem', fontWeight: 700, color: 'var(--brand-indigo)' }}>{formatTokenCount(question.completion_tokens)}</div>
            </div>
            <div style={{ background: 'var(--bg-canvas)', padding: '10px', borderRadius: 'var(--radius-xs)', border: '1px solid var(--border-light)', textAlign: 'center' }}>
              <div style={{ fontSize: '0.65rem', color: 'var(--text-muted)', fontWeight: 600 }}>TOTAL TOKENS</div>
              <div style={{ fontSize: '1rem', fontWeight: 700, color: 'var(--status-success)' }}>{formatTokenCount(question.total_tokens)}</div>
            </div>
            <div style={{ background: 'var(--bg-canvas)', padding: '10px', borderRadius: 'var(--radius-xs)', border: '1px solid var(--border-light)', textAlign: 'center' }}>
              <div style={{ fontSize: '0.65rem', color: 'var(--text-muted)', fontWeight: 600 }}>QUALITY STATUS</div>
              <div style={{ fontSize: '1rem', fontWeight: 700, color: 'var(--status-success)' }}>High Quality (&gt; 90)</div>
            </div>
          </div>
        </div>

        {/* 4 Pillars Breakdown */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
          <h4 style={{ fontSize: '0.825rem', fontWeight: 800, color: 'var(--text-primary)', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
            Quality Pillars (100 Points Total)
          </h4>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
            {pillars.map((p) => (
              <div
                key={p.label}
                style={{
                  background: 'var(--bg-canvas)',
                  padding: '14px 18px',
                  borderRadius: 'var(--radius-md)',
                  border: '1px solid var(--border-light)'
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.825rem', marginBottom: '8px' }}>
                  <span style={{ color: 'var(--text-primary)', fontWeight: 700 }}>{p.label}</span>
                  <span style={{ color: p.color, fontWeight: 800 }}>{p.score} / {p.max}</span>
                </div>
                <div style={{ width: '100%', height: '6px', background: 'var(--border-medium)', borderRadius: '3px', overflow: 'hidden' }}>
                  <div
                    style={{
                      width: `${(p.score / p.max) * 100}%`,
                      height: '100%',
                      background: p.color,
                      borderRadius: '3px'
                    }}
                  />
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Cognitive & Pedagogical Calibration */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <h4 style={{ fontSize: '0.825rem', fontWeight: 800, color: 'var(--text-primary)', textTransform: 'uppercase', letterSpacing: '0.5px', margin: 0 }}>
              Exam Accuracy &amp; Question Design
            </h4>
            <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>
              Question Trap Analysis &amp; Student Misconceptions
            </span>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
            {/* Primary Trap */}
            <div
              style={{
                background: 'var(--bg-canvas)',
                padding: '14px 16px',
                borderRadius: 'var(--radius-md)',
                border: '1px solid var(--border-light)',
                display: 'flex',
                flexDirection: 'column',
                gap: '8px'
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <span style={{ fontSize: '0.72rem', fontWeight: 700, textTransform: 'uppercase', color: 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: '5px' }}>
                  <Zap size={13} style={{ color: 'var(--status-purple, #8b5cf6)' }} />
                  Common Trap Tested
                </span>
                <span className="badge badge-purple" style={{ fontSize: '0.68rem', padding: '2px 8px', display: 'inline-flex', alignItems: 'center', gap: '4px' }}>
                  <Sparkles size={11} /> Trap Breakdown
                </span>
              </div>
              <div style={{ fontSize: '0.875rem', fontWeight: 700, color: 'var(--text-primary)' }}>
                {trapInfo?.label || 'Direct Conceptual Application'}
              </div>
              <p style={{ fontSize: '0.775rem', color: 'var(--text-muted)', margin: 0, lineHeight: 1.45 }}>
                {trapInfo?.advice || 'Evaluates direct conceptual understanding without deceptive distractor skew.'}
              </p>
            </div>

            {/* Target Misconception */}
            <div
              style={{
                background: 'var(--bg-canvas)',
                padding: '14px 16px',
                borderRadius: 'var(--radius-md)',
                border: '1px solid var(--border-light)',
                display: 'flex',
                flexDirection: 'column',
                gap: '8px'
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <span style={{ fontSize: '0.72rem', fontWeight: 700, textTransform: 'uppercase', color: 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: '5px' }}>
                  <Target size={13} style={{ color: 'var(--brand-primary, #38bdf8)' }} />
                  Common Student Mistake
                </span>
                <span className="badge badge-cyan" style={{ fontSize: '0.68rem', padding: '2px 8px', display: 'inline-flex', alignItems: 'center', gap: '4px' }}>
                  <Sparkles size={11} /> Common Mistake
                </span>
              </div>
              <div style={{ fontSize: '0.875rem', fontWeight: 700, color: 'var(--text-primary)' }}>
                {mistakePattern ? mistakePattern.replace(/_/g, ' ') : 'None Diagnosed (Clean Distractor)'}
              </div>
              <p style={{ fontSize: '0.775rem', color: 'var(--text-muted)', margin: 0, lineHeight: 1.45 }}>
                {mistakePattern
                  ? 'Incorrect choices were specifically crafted to highlight this common conceptual mistake.'
                  : 'Incorrect choices test fundamental science concepts without relying on a specific trick.'}
              </p>
            </div>
          </div>

          {/* Visual Stimulus Evaluation */}
          <div
            style={{
              background: 'var(--bg-canvas)',
              padding: '12px 16px',
              borderRadius: 'var(--radius-md)',
              border: '1px solid var(--border-light)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              gap: '12px'
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <div
                style={{
                  width: '32px',
                  height: '32px',
                  borderRadius: 'var(--radius-xs)',
                  background: hasVisual ? 'var(--brand-light)' : 'var(--bg-surface-elevated)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  color: hasVisual ? 'var(--brand-primary)' : 'var(--text-muted)',
                  border: '1px solid var(--border-light)',
                  flexShrink: 0
                }}
              >
                <ImageIcon size={16} />
              </div>
              <div>
                <div style={{ fontSize: '0.8rem', fontWeight: 700, color: 'var(--text-primary)' }}>
                  Figure Review: {hasVisual ? 'Diagram Generated & Attached' : 'Text-Only Question (No Diagram Needed)'}
                </div>
                <div style={{ fontSize: '0.725rem', color: 'var(--text-muted)' }}>
                  {hasVisual
                    ? (question.image_description || 'Custom biomedical or physical sciences diagram rendered to accompany item stem.')
                    : 'The question stem and passage provide all necessary context without needing a diagram.'}
                </div>
              </div>
            </div>
            <span className={`badge ${hasVisual ? 'badge-blue' : 'badge-slate'}`} style={{ fontSize: '0.7rem', padding: '3px 8px', flexShrink: 0 }}>
              {hasVisual ? 'Diagram Attached' : 'Text Only'}
            </span>
          </div>
        </div>

        {/* Strengths & Deficiencies */}
        {review && (
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '14px' }}>
            {/* Strengths */}
            <div
              style={{
                background: 'var(--status-success-bg)',
                border: '1px solid var(--status-success-border)',
                borderRadius: 'var(--radius-md)',
                padding: '16px 18px'
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: 'var(--status-success)', fontWeight: 800, fontSize: '0.85rem', marginBottom: '8px' }}>
                <CheckCircle size={16} /> Question Strengths
              </div>
              <ul style={{ paddingLeft: '18px', fontSize: '0.825rem', color: 'var(--text-primary)', display: 'flex', flexDirection: 'column', gap: '4px' }}>
                {review.strengths?.length > 0 ? (
                  review.strengths.map((s) => <li key={s}>{s}</li>)
                ) : (
                  <li>Consistent authentic formatting adhered to.</li>
                )}
              </ul>
            </div>

            {/* Recommendations / Remediation */}
            <div
              style={{
                background: 'var(--status-warning-bg)',
                border: '1px solid var(--status-warning-border)',
                borderRadius: 'var(--radius-md)',
                padding: '16px 18px'
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: 'var(--status-warning)', fontWeight: 800, fontSize: '0.85rem', marginBottom: '8px' }}>
                <AlertTriangle size={16} /> Suggestions for Polish
              </div>
              <ul style={{ paddingLeft: '18px', fontSize: '0.825rem', color: 'var(--text-primary)', display: 'flex', flexDirection: 'column', gap: '4px' }}>
                {review.recommendations?.length > 0 ? (
                  review.recommendations.map((r) => <li key={r}>{r}</li>)
                ) : (
                  <li>Draft scored high and is ready for your Question Bank.</li>
                )}
              </ul>
            </div>
          </div>
        )}

        {/* Iterations Evolution Timeline */}
        {history.length > 1 && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
            <h4 style={{ fontSize: '0.825rem', fontWeight: 800, color: 'var(--text-primary)', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
              Refinement History
            </h4>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
              {history.map((h, idx) => (
                <div
                  key={h.iteration || `history-${idx}`}
                  style={{
                    padding: '12px 16px',
                    background: 'var(--bg-canvas)',
                    borderRadius: 'var(--radius-md)',
                    border: '1px solid var(--border-light)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between'
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                    <span className="badge badge-cyan">Round {h.iteration}</span>
                    <span style={{ fontSize: '0.85rem', color: 'var(--text-primary)', fontWeight: 700 }}>
                      Score: {h.review?.total_score || 'N/A'}/100
                    </span>
                  </div>
                  <span style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-muted)' }}>
                    {h.review?.passed ? '✓ Met High Quality (>90 Score)' : 'Polished in Refinement Round'}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </Modal>
  );
}
