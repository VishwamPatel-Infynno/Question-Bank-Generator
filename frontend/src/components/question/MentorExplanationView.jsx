import { useMemo } from 'react';
import {
  GraduationCap,
  CheckCircle2,
  AlertTriangle,
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

export default function MentorExplanationView({
  explanation = '',
  isCompact = false,
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
    <div className={`mentor-view-wrap ${isCompact ? 'compact' : ''}`}>
      {/* Mentor Header Bar */}
      <div className="mentor-header-bar">
        <div className="mentor-header-left">
          <div className="mentor-header-icon">
            <GraduationCap size={isCompact ? 13 : 15} />
          </div>
          <div>
            <div className="mentor-header-title">
              Explanations
            </div>
          </div>
        </div>

        {parsed.resolvedTrap && (
          <span
            className="badge badge-neutral mentor-header-trap-chip"
            title={parsed.resolvedTrap.advice}
          >
            <AlertTriangle size={11} color="var(--status-warning)" />
            {parsed.resolvedTrap.label}
          </span>
        )}
      </div>

      {/* SECTION 1: Why Option [Key] is Correct */}
      <div className="mentor-correct-box">
        <div className="mentor-correct-header">
          <CheckCircle2 size={13} />
          <span>Correct Answer ({keyLabel})</span>
        </div>

        {parsed.steps && parsed.steps.length > 0 ? (
          <div className="mentor-step-list">
            {parsed.steps.map((st, idx) => {
              const stepMatch = st.match(/^(?:\*\*)?(Step\s+\d+|[1-9]\d*\.)(?::|\s*-)?(?:\*\*)?\s*(.*)/is);
              const stepKey = `step-${idx}-${st.slice(0, 10)}`;
              if (stepMatch) {
                const label = stepMatch[1].replace(/:$/, '').trim();
                const stepBody = stepMatch[2].trim();
                return (
                  <div key={stepKey} className="mentor-step-row">
                    <span className="mentor-step-badge">
                      {label}
                    </span>
                    <span className="mentor-step-body">
                      <FormattedText text={stepBody} />
                    </span>
                  </div>
                );
              }
              return (
                <div key={stepKey} className="mentor-step-body">
                  <FormattedText text={st} />
                </div>
              );
            })}
          </div>
        ) : (
          <div className="mentor-correct-prose">
            <FormattedText text={parsed.correctExplanation} />
          </div>
        )}
      </div>

      {/* SECTION 2: Why Other Options are Incorrect (Distractors) */}
      {parsed.distractors && parsed.distractors.length > 0 && (
        <div className="mentor-distractor-box">
          <div className="mentor-distractor-header">
            <div className="mentor-distractor-title">
              <AlertTriangle size={13} color="var(--status-warning)" />
              <span>Incorrect Choices</span>
            </div>
            <span className="mentor-distractor-count">
              {parsed.distractors.length} choices
            </span>
          </div>

          <div className="mentor-distractor-list">
            {parsed.distractors.map((item, idx) => (
              <div
                key={item.label ? `dist-${item.label}` : `dist-${idx}-${item.text?.slice(0, 10)}`}
                className="mentor-distractor-item"
              >
                {item.label && (
                  <span className="mentor-distractor-key">
                    {item.label}
                  </span>
                )}

                {item.trap && (
                  <span className="mentor-distractor-trap">
                    {item.trap}
                  </span>
                )}

                <FormattedText text={item.body} highlightTraps className="mentor-distractor-body" />
              </div>
            ))}
          </div>
        </div>
      )}

      {/* SECTION 3: Primary Cognitive Trap Defense */}
      {parsed.resolvedTrap && (
        <div className="mentor-trap-box">
          <div className="mentor-header-bar">
            <div className="mentor-trap-header">
              <Target size={13} />
              <span>Exam Trap &bull; {parsed.resolvedTrap.label}</span>
            </div>
          </div>

          <div className="mentor-trap-body">
            <strong>Avoidance: </strong>
            {parsed.resolvedTrap.advice}
          </div>
        </div>
      )}

      {/* SECTION 4: Student Misconception if present */}
      {likelyMistakePattern && (
        <div className="mentor-mistake-box">
          <div className="mentor-mistake-header">
            <AlertTriangle size={13} />
            <span>Target Mistake &bull; {likelyMistakePattern}</span>
          </div>

          <div className="mentor-mistake-body">
            <strong>Exam Tip: </strong>
            Double-check foundational assumptions, formula boundary conditions, and sign/unit conventions before finalizing your choice.
          </div>
        </div>
      )}
    </div>
  );
}
