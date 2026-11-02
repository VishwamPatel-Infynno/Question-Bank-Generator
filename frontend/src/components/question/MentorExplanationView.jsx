import React, { useMemo } from 'react';
import {
  GraduationCap,
  CheckCircle2,
  AlertTriangle,
  Lightbulb,
  Target
} from 'lucide-react';

import {
  resolveTrapInfo,
  detectTrapFromText,
  extractDistractorLines
} from '../../utils';
import { FormattedText } from '../common';

/**
 * MentorExplanationView
 *
 * Dedicated minimalist educational view for AAMC MCAT questions:
 * 1. Why the Correct Key is True (Core evidence, step-by-step mathematical/conceptual proof)
 * 2. Why Distractors Fail (Itemized option breakdown with subtle trap annotations)
 * 3. Tactical Trap Defense Strategy
 */
const EMPTY_ARRAY = [];

export default function MentorExplanationView({
  explanation = '',
  isCompact = false,
  _options = EMPTY_ARRAY,
  correctAnswerId = '',
  primaryTrap = null,
  likelyMistakePattern = null
}) {
  const parsed = useMemo(() => {
    if (!explanation) {
      return {
        correctExplanation: 'No explanation currently available.',
        steps: null,
        distractors: [],
        resolvedTrap: null
      };
    }

    const text = String(explanation).trim();

    // 1. Resolve Primary Trap
    let resolvedTrap = resolveTrapInfo(primaryTrap);
    if (!resolvedTrap) {
      resolvedTrap = detectTrapFromText(text);
    }

    // 2. Split on distractor header markers
    const distractorHeaderRegex = /(?:(?:why\s+other\s+options\s+are\s+incorrect(?:\s*\(distractor\s*&\s*trap\s*breakdown\))?|why\s+distractors\s+fail|why\s+other\s+options\s+(?:are\s+traps|fail|are\s+wrong|are\s+incorrect)|why\s+other\s+choices\s+fail|why\s+incorrect\s+options\s+fail|(?:explicit\s+)?distractor\s+(?:breakdown|analysis|notes|traps)|common\s+traps|trap\s+breakdown|why\s+distractors\s+are\s+incorrect)(?:\s*(?:[•·\-–—:|/]|&|\+)\s*[^\n\r]*)?):?/i;
    const match = text.match(distractorHeaderRegex);

    if (match && match.index !== undefined) {
      const correctRaw = text.substring(0, match.index).trim();
      const distractorsRaw = text.substring(match.index + match[0].length).trim();

      const cleanedCorrect = correctRaw
        .replace(/^(?:why\s+options?\s+[A-E](?:\s*,\s*[A-E])*\s+is\s+correct|correct\s+answer(?:\s+analysis)?|how\s+to\s+think\s+about\s+this|pedagogical\s+evaluation):?/i, '')
        .trim();

      let steps = null;
      if (/(?:\*\*|\b)Step\s+\d+:?\*?\*?/i.test(cleanedCorrect)) {
        const rawSteps = cleanedCorrect.split(/(?=(?:(?:\*\*|\b)Step\s+\d+:?\*?\*?))/i);
        const filtered = rawSteps.map(s => s.trim()).filter(Boolean);
        if (filtered.length > 1) steps = filtered;
      }

      const distractorItems = extractDistractorLines(distractorsRaw);

      return {
        correctExplanation: cleanedCorrect || correctRaw,
        steps,
        distractors: distractorItems,
        resolvedTrap
      };
    }

    const lines = text.split(/\r?\n+/).map(l => l.trim()).filter(Boolean);
    const correctLines = [];
    const distractorLines = [];

    let inDistractorSection = false;
    for (const line of lines) {
      if (/(?:INCORRECT|DISTRACTOR|Wrong|Trap)/i.test(line) && /(?:[-•*]\s*)?(?:Options?|Choices?|Distractors?|Statements?)\s+[A-E]\b/i.test(line)) {
        inDistractorSection = true;
      }
      if (inDistractorSection || /(?:INCORRECT|DISTRACTOR)/i.test(line)) {
        distractorLines.push(line);
      } else {
        correctLines.push(line);
      }
    }

    if (distractorLines.length > 0) {
      const correctText = correctLines
        .join('\n')
        .replace(/^(?:why\s+options?\s+[A-E](?:\s*,\s*[A-E])*\s+is\s+correct|correct\s+answer(?:\s+analysis)?|pedagogical\s+evaluation|analysis\s+of\s+options):?/i, '')
        .trim();

      return {
        correctExplanation: correctText || text,
        steps: null,
        distractors: extractDistractorLines(distractorLines.join('\n')),
        resolvedTrap
      };
    }

    const cleanedUnified = text
      .replace(/^(?:why\s+options?\s+[A-E](?:\s*,\s*[A-E])*\s+is\s+correct|correct\s+answer|how\s+to\s+think\s+about\s+this):?/i, '')
      .trim();

    return {
      correctExplanation: cleanedUnified || text,
      steps: null,
      distractors: [],
      resolvedTrap
    };
  }, [explanation, primaryTrap]);

  if (!explanation) return null;

  const keyLabel = correctAnswerId ? `Option ${correctAnswerId}` : 'Correct Key';

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: isCompact ? '12px' : '16px' }}>
      {/* Mentor Header Bar */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '8px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <div
            style={{
              width: isCompact ? '22px' : '26px',
              height: isCompact ? '22px' : '26px',
              borderRadius: 'var(--radius-xs)',
              background: 'var(--brand-light)',
              color: 'var(--brand-primary)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              flexShrink: 0
            }}
          >
            <GraduationCap size={isCompact ? 13 : 15} />
          </div>
          <div>
            <div style={{ fontWeight: 700, fontSize: isCompact ? '0.825rem' : '0.875rem', color: 'var(--text-primary)' }}>
              Why Each Choice is Right or Wrong
            </div>
            {!isCompact && (
              <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', marginTop: '1px' }}>
                Detailed breakdown of the correct solution and why the other options are wrong.
              </div>
            )}
          </div>
        </div>

        {parsed.resolvedTrap && (
          <span
            className="badge badge-neutral"
            style={{ fontSize: '0.675rem', padding: '2px 8px', display: 'inline-flex', alignItems: 'center', gap: '4px', fontWeight: 500 }}
            title={parsed.resolvedTrap.advice}
          >
            <AlertTriangle size={11} color="var(--status-warning)" />
            Common Trap: {parsed.resolvedTrap.label}
          </span>
        )}
      </div>

      {/* SECTION 1: Why Option [Key] is Correct */}
      <div
        style={{
          background: 'var(--status-success-bg)',
          border: '1px solid var(--status-success-border)',
          borderRadius: 'var(--radius-sm)',
          padding: isCompact ? '10px 12px' : '12px 14px',
          display: 'flex',
          flexDirection: 'column',
          gap: '8px'
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.78rem', fontWeight: 600, color: 'var(--status-success)' }}>
          <CheckCircle2 size={13} />
          <span>Correct Answer Explanation ({keyLabel})</span>
        </div>

        {parsed.steps && parsed.steps.length > 0 ? (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
            {parsed.steps.map((st, idx) => {
              const stepMatch = st.match(/^(?:\*\*)?(Step\s+\d+|[1-9]\d*\.)(?::|\s*-)?(?:\*\*)?\s*(.*)/is);
              const stepKey = `step-${idx}-${st.slice(0, 10)}`;
              if (stepMatch) {
                const label = stepMatch[1].replace(/:$/, '').trim();
                const stepBody = stepMatch[2].trim();
                return (
                  <div key={stepKey} style={{ display: 'flex', alignItems: 'flex-start', gap: '8px', fontSize: isCompact ? '0.8rem' : '0.84rem' }}>
                    <span
                      style={{
                        background: 'var(--bg-surface)',
                        border: '1px solid var(--status-success-border)',
                        color: 'var(--status-success)',
                        padding: '1px 5px',
                        borderRadius: 'var(--radius-xs)',
                        fontWeight: 600,
                        fontSize: '0.7rem',
                        whiteSpace: 'nowrap',
                        flexShrink: 0
                      }}
                    >
                      {label}
                    </span>
                    <span style={{ color: 'var(--text-primary)', flex: 1, lineHeight: 1.55 }}>
                      <FormattedText text={stepBody} />
                    </span>
                  </div>
                );
              }
              return (
                <div key={stepKey} style={{ color: 'var(--text-primary)', lineHeight: 1.55, fontSize: isCompact ? '0.8rem' : '0.84rem' }}>
                  <FormattedText text={st} />
                </div>
              );
            })}
          </div>
        ) : (
          <div
            style={{
              fontSize: isCompact ? '0.8rem' : '0.84rem',
              lineHeight: 1.6,
              color: 'var(--text-primary)',
              whiteSpace: 'pre-line'
            }}
          >
            <FormattedText text={parsed.correctExplanation} />
          </div>
        )}
      </div>

      {/* SECTION 2: Why Other Options are Incorrect (Distractors) */}
      {parsed.distractors && parsed.distractors.length > 0 && (
        <div
          style={{
            background: 'var(--status-warning-bg)',
            border: '1px solid var(--status-warning-border)',
            borderRadius: 'var(--radius-sm)',
            padding: isCompact ? '10px 12px' : '12px 14px',
            display: 'flex',
            flexDirection: 'column',
            gap: '8px'
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '6px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.78rem', fontWeight: 600, color: 'var(--status-warning)' }}>
              <AlertTriangle size={13} color="var(--status-warning)" />
              <span>Why Other Choices Are Incorrect (Common Traps &amp; Mistakes)</span>
            </div>
            <span style={{ fontSize: '0.675rem', color: 'var(--text-muted)' }}>
              {parsed.distractors.length} other choices
            </span>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', fontSize: isCompact ? '0.78rem' : '0.825rem' }}>
            {parsed.distractors.map((item, idx) => (
              <div
                key={item.label ? `dist-${item.label}` : `dist-${idx}-${item.text?.slice(0, 10)}`}
                style={{
                  display: 'flex',
                  alignItems: 'flex-start',
                  gap: '8px',
                  background: 'var(--bg-surface)',
                  border: '1px solid var(--border-light)',
                  borderRadius: 'var(--radius-xs)',
                  padding: '6px 8px',
                  lineHeight: 1.5
                }}
              >
                {item.label && (
                  <span
                    style={{
                      background: 'var(--status-danger-bg)',
                      border: '1px solid var(--status-danger-border)',
                      color: 'var(--status-danger)',
                      padding: '1px 5px',
                      borderRadius: 'var(--radius-xs)',
                      fontWeight: 600,
                      fontSize: '0.7rem',
                      whiteSpace: 'nowrap',
                      flexShrink: 0
                    }}
                  >
                    {item.label}
                  </span>
                )}

                {item.trap && (
                  <span
                    style={{
                      background: 'var(--status-purple-bg)',
                      border: '1px solid var(--status-purple-border)',
                      color: 'var(--status-purple)',
                      padding: '1px 5px',
                      borderRadius: 'var(--radius-xs)',
                      fontWeight: 500,
                      fontSize: '0.675rem',
                      whiteSpace: 'nowrap',
                      flexShrink: 0
                    }}
                  >
                    {item.trap}
                  </span>
                )}

                <FormattedText text={item.body} highlightTraps style={{ color: 'var(--text-secondary)', flex: 1 }} />
              </div>
            ))}
          </div>
        </div>
      )}

      {/* SECTION 3: Primary Cognitive Trap Defense */}
      {parsed.resolvedTrap && (
        <div
          style={{
            background: 'var(--status-purple-bg)',
            border: '1px solid var(--status-purple-border)',
            borderRadius: 'var(--radius-sm)',
            padding: isCompact ? '10px 12px' : '12px 14px',
            display: 'flex',
            flexDirection: 'column',
            gap: '5px'
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '6px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.78rem', fontWeight: 600, color: 'var(--status-purple)' }}>
              <Target size={13} />
              <span>Exam Trap to Watch Out For &bull; {parsed.resolvedTrap.label}</span>
            </div>
          </div>

          <div style={{ fontSize: isCompact ? '0.76rem' : '0.82rem', color: 'var(--text-secondary)', lineHeight: 1.55 }}>
            <strong style={{ color: 'var(--text-primary)' }}>How to avoid this trap on test day: </strong>
            {parsed.resolvedTrap.advice}
          </div>
        </div>
      )}

      {/* SECTION 4: Student Misconception if present */}
      {likelyMistakePattern && (
        <div
          style={{
            background: 'var(--status-warning-bg)',
            border: '1px solid var(--status-warning-border)',
            borderRadius: 'var(--radius-sm)',
            padding: isCompact ? '10px 12px' : '12px 14px',
            display: 'flex',
            flexDirection: 'column',
            gap: '5px'
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.78rem', fontWeight: 600, color: 'var(--status-warning)' }}>
            <AlertTriangle size={13} />
            <span>Common Student Mistake in Choices &bull; {likelyMistakePattern}</span>
          </div>

          <div style={{ fontSize: isCompact ? '0.76rem' : '0.82rem', color: 'var(--text-secondary)', lineHeight: 1.55 }}>
            <strong style={{ color: 'var(--text-primary)' }}>Exam Tip: </strong>
            Double-check foundational assumptions, formula boundary conditions, and sign/unit conventions before finalizing your choice.
          </div>
        </div>
      )}

      {/* Quiet Pro-Tip Footer */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: '6px',
          fontSize: '0.72rem',
          color: 'var(--text-muted)',
          paddingTop: '2px'
        }}
      >
        <Lightbulb size={12} style={{ color: 'var(--brand-primary)', flexShrink: 0 }} />
        <span>Tip: Understanding why wrong choices are incorrect is one of the fastest ways to improve your exam score.</span>
      </div>
    </div>
  );
}
