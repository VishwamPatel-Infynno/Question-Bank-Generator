import { resolveTrapInfo, detectTrapFromText } from './trapHelpers';

export const DISTRACTOR_HEADER_REGEX = /(?:why\s+other\s+options\s+are\s+incorrect(?:\s*\(distractor\s*&\s*trap\s*breakdown\))?|why\s+distractors\s+fail|why\s+other\s+options\s+(?:are\s+traps|fail|are\s+wrong|are\s+incorrect)|why\s+other\s+choices\s+fail|why\s+incorrect\s+options\s+fail|(?:explicit\s+)?distractor\s+(?:breakdown|analysis|notes|traps)|common\s+traps|trap\s+breakdown|why\s+distractors\s+are\s+incorrect)(?:[^\S\r\n]*(?:[•·\-–—:|/]|&|\+)[^\S\r\n]*[^\r\n]*)?:?/i;

/**
 * Extracts individual distractor items and trap chips from distractor breakdown text.
 * Pure JavaScript utility without React/JSX dependencies.
 *
 * @param {string} rawText - Raw text block containing distractor items
 * @returns {Array<{label: string|null, trap: string|null, body: string}>}
 */
export function extractDistractorLines(rawText) {
  if (!rawText) return [];

  const OPTION_PREFIX_REGEX = /^(?:[-•*]\s*)?((?:Options?|Choices?|Distractors?|Statements?)\s+[A-D](?:\s*(?:and|&|,)\s*(?:(?:Options?|Choices?|Distractors?|Statements?)\s+)?[A-D])*(?:\s*(?:\([^)\n]{2,60}\)|\[[^\]\n]{2,60}\]))?)(?:\s*[:\-–—;,]\s*|\s+)(.*)/is;
  const SOLO_OPTION_REGEX = /^(?:[-•*]\s*)?((?:Options?|Choices?|Distractors?|Statements?)\s+[A-D](?:\s*(?:and|&|,)\s*(?:(?:Options?|Choices?|Distractors?|Statements?)\s+)?[A-D])*(?:\s*(?:\([^)\n]{2,60}\)|\[[^\]\n]{2,60}\]))?)\s*$/i;

  // Split either by newlines or by option item boundary
  const chunks = rawText
    .split(/(?:\r?\n+)|(?<=[.!?])\s+(?=(?:[-•*]\s*)?(?:Options?|Choices?|Distractors?|Statements?)\s+[A-D]\b)/i)
    .map(line => line.trim())
    .filter(Boolean);

  const items = [];

  for (const chunk of chunks) {
    const match = chunk.match(OPTION_PREFIX_REGEX);
    const solo = !match ? chunk.match(SOLO_OPTION_REGEX) : null;

    if (match || solo) {
      const rawLabel = (match ? match[1] : solo[1]).trim();
      let body = match ? match[2].trim() : '';

      let trapChip = null;

      // Check pattern 1: "is INCORRECT (Trap Name):" or "INCORRECT [Trap Name]:"
      const incorrectWithParen = body.match(
        /^(?:is\s+)?(?:INCORRECT|WRONG|FALSE|INVALID|DISTRACTOR)\s*(?:\(([^)\n]{2,60})\)|\[([^\]\n]{2,60})\])\s*[:\-–—]?\s*/i
      );

      // Check pattern 2: Parentheses or brackets in rawLabel or body
      const parenMatch =
        body.match(/^[:\-–—\s]*(?:\(([^)\n]{2,60})\)|\[([^\]\n]{2,60})\])/) ||
        rawLabel.match(/(?:\(([^)\n]{2,60})\)|\[([^\]\n]{2,60})\])/) ||
        body.match(
          /(?:\(([^)\n]{2,60}(?:Trap|Error|Language|Assumption|Scope|Knowledge|Correlation|Causation|Distortion|Opposite|Slip|Inversion|Premise|Misconception|Calculation|Inference|Overinterpretation|Confusion|Misapplied)[^)\n]*)\))/i
        );

      if (incorrectWithParen) {
        trapChip = (incorrectWithParen[1] || incorrectWithParen[2] || '').trim();
        body = body.slice(incorrectWithParen[0].length).trim();
      } else if (parenMatch) {
        trapChip = (parenMatch[1] || parenMatch[2] || '').trim();
        body = body.replace(parenMatch[0], '').trim();
      }

      // Clean leading "is INCORRECT:" or "is INCORRECT -" so explanations read like clean, natural human prose
      body = body
        .replace(/^(?:is\s+)?(?:INCORRECT|WRONG|FALSE|INVALID|DISTRACTOR)\s*[:\-–—]\s*/i, '')
        .trim();

      // Clean label (strip bracketed/parenthesized annotations and DISTRACTOR tag)
      const cleanLabel = rawLabel
        .replace(/\s*\[DISTRACTOR\]/i, '')
        .replace(/\s*\[[^\]]*\]/g, '')
        .replace(/\s*\([^)]*\)/g, '')
        .trim();

      items.push({
        label: cleanLabel,
        trap: trapChip,
        body
      });
    } else {
      // Freeform distractor line
      items.push({
        label: null,
        trap: null,
        body: chunk
      });
    }
  }

  // Sort items in alphabetical order: Option A, then B, then C, then D
  function getOptionLetterOrder(label) {
    if (!label) return 999;
    const letterMatch = String(label).match(/(?:Options?|Choices?|Distractors?|Statements?)?\s*([A-D])\b/i);
    return letterMatch ? letterMatch[1].toUpperCase().charCodeAt(0) : 999;
  }

  items.sort((a, b) => getOptionLetterOrder(a.label) - getOptionLetterOrder(b.label));

  return items;
}

/**
 * Parses raw explanation text into structured components for mentor-style presentation.
 *
 * @param {string} explanation - Raw explanation text
 * @param {string|null} [primaryTrap] - Optional pre-classified trap identifier
 * @returns {{
 *   correctExplanation: string,
 *   steps: string[]|null,
 *   distractors: Array<{label: string|null, trap: string|null, body: string}>,
 *   resolvedTrap: object|null
 * }}
 */
export function parseMentorExplanation(explanation, primaryTrap = null) {
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
  const match = text.match(DISTRACTOR_HEADER_REGEX);

  if (match && match.index !== undefined) {
    const correctRaw = text.substring(0, match.index).trim();
    const distractorsRaw = text.substring(match.index + match[0].length).trim();

    const cleanedCorrect = correctRaw
      .replace(
        /^(?:why\s+options?\s+[A-E](?:\s*,\s*[A-E])*\s+is\s+correct|correct\s+answer(?:\s+analysis)?|how\s+to\s+think\s+about\s+this|pedagogical\s+evaluation):?/i,
        ''
      )
      .trim();

    let steps = null;
    if (/(?:\*\*|\b)Step\s+\d+:?\*?\*?/i.test(cleanedCorrect)) {
      const rawSteps = cleanedCorrect.split(
        /(?=(?:(?:\r?\n|^)\s*(?:\*\*)?|(?<=\s)(?:\*\*)?)Step\s+\d+:?\*?\*?)/i
      );
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

  // 3. Fallback: line-by-line categorization
  const lines = text.split(/\r?\n+/).map(l => l.trim()).filter(Boolean);
  const correctLines = [];
  const distractorLines = [];

  let inDistractorSection = false;
  for (const line of lines) {
    if (
      /(?:INCORRECT|DISTRACTOR|Wrong|Trap)/i.test(line) &&
      /(?:[-•*]\s*)?(?:Options?|Choices?|Distractors?|Statements?)\s+[A-D]\b/i.test(line)
    ) {
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
      .replace(
        /^(?:why\s+options?\s+[A-E](?:\s*,\s*[A-E])*\s+is\s+correct|correct\s+answer(?:\s+analysis)?|pedagogical\s+evaluation|analysis\s+of\s+options):?/i,
        ''
      )
      .trim();

    return {
      correctExplanation: correctText || text,
      steps: null,
      distractors: extractDistractorLines(distractorLines.join('\n')),
      resolvedTrap
    };
  }

  const cleanedUnified = text
    .replace(
      /^(?:why\s+options?\s+[A-E](?:\s*,\s*[A-E])*\s+is\s+correct|correct\s+answer|how\s+to\s+think\s+about\s+this):?/i,
      ''
    )
    .trim();

  return {
    correctExplanation: cleanedUnified || text,
    steps: null,
    distractors: [],
    resolvedTrap
  };
}
