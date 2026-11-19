import { describe, expect, it } from 'vitest';
import {
  DISTRACTOR_HEADER_REGEX,
  extractDistractorLines,
  parseMentorExplanation
} from '../explanationHelpers';

describe('extractDistractorLines', () => {
  it('returns an empty array when given null or empty text', () => {
    expect(extractDistractorLines('')).toEqual([]);
    expect(extractDistractorLines(null)).toEqual([]);
    expect(extractDistractorLines(undefined)).toEqual([]);
  });

  it('extracts all 3 distractors with clean labels, traps, and bodies', () => {
    const raw = `
- Option B is INCORRECT (Distortion / Competitive Trap): A rightward shift in the x-intercept with an unchanged y-intercept describes competitive inhibition.
- Option C is INCORRECT (Uncompetitive Trap): Parallel shifts in both intercepts characterize uncompetitive inhibition.
- Option D is INCORRECT (Mathematical Slip): The slope is Km/Vmax. Because Vmax decreases in the denominator, the slope MUST increase.
    `.trim();

    const result = extractDistractorLines(raw);
    expect(result).toHaveLength(3);

    expect(result[0]).toEqual({
      label: 'Option B',
      trap: 'Distortion / Competitive Trap',
      body: 'A rightward shift in the x-intercept with an unchanged y-intercept describes competitive inhibition.'
    });

    expect(result[1]).toEqual({
      label: 'Option C',
      trap: 'Uncompetitive Trap',
      body: 'Parallel shifts in both intercepts characterize uncompetitive inhibition.'
    });

    expect(result[2]).toEqual({
      label: 'Option D',
      trap: 'Mathematical Slip',
      body: 'The slope is Km/Vmax. Because Vmax decreases in the denominator, the slope MUST increase.'
    });
  });

  it('handles bracketed trap notations and strips redundant prefixes', () => {
    const raw = `
- Option A [Extreme Language Trap]: Always using absolute terms.
- Option B: INCORRECT - Insufficient evidence in paragraph 2.
- Option D is incorrect because the passage contradicts this finding.
    `.trim();

    const result = extractDistractorLines(raw);
    expect(result).toHaveLength(3);

    expect(result[0].label).toBe('Option A');
    expect(result[0].trap).toBe('Extreme Language Trap');
    expect(result[0].body).toBe('Always using absolute terms.');

    expect(result[1].label).toBe('Option B');
    expect(result[1].body).toBe('Insufficient evidence in paragraph 2.');

    expect(result[2].label).toBe('Option D');
    expect(result[2].body).toBe('is incorrect because the passage contradicts this finding.');
  });

  it('handles freeform distractor lines gracefully without crashing', () => {
    const raw = 'General note: Distractor analysis was omitted by the author.';
    const result = extractDistractorLines(raw);
    expect(result).toHaveLength(1);
    expect(result[0].label).toBeNull();
    expect(result[0].trap).toBeNull();
    expect(result[0].body).toBe('General note: Distractor analysis was omitted by the author.');
  });

  it('preserves all 3 distractors when parsing a full explanation through the distractor header regex', () => {
    const fullExplanation = `Why Option A is Correct:
Step 1: Test step showing why A is right.

Why Other Options are Incorrect (Distractor & Trap Breakdown):
- Option B is INCORRECT (Distortion): B is wrong.
- Option C is INCORRECT (Out of Scope): C is wrong.
- Option D is INCORRECT (Calculation Slip): D is wrong.`;

    const match = fullExplanation.match(DISTRACTOR_HEADER_REGEX);
    expect(match).not.toBeNull();
    expect(match[0].trim()).toBe('Why Other Options are Incorrect (Distractor & Trap Breakdown):');

    const distractorsRaw = fullExplanation.substring(match.index + match[0].length).trim();
    const items = extractDistractorLines(distractorsRaw);

    expect(items).toHaveLength(3);
    expect(items.map((item) => item.label)).toEqual(['Option B', 'Option C', 'Option D']);
    expect(items.map((item) => item.trap)).toEqual(['Distortion', 'Out of Scope', 'Calculation Slip']);
  });

  it('sorts distractor choices strictly in alphabetical order (A then B then C then D as applicable)', () => {
    const raw = `
- Option D is INCORRECT (Calculation Slip): Slip explanation.
- Option A is INCORRECT (Distortion): Distortion explanation.
- Option B is INCORRECT (Extreme Language): Language explanation.
    `.trim();

    const result = extractDistractorLines(raw);
    expect(result).toHaveLength(3);
    expect(result.map((item) => item.label)).toEqual(['Option A', 'Option B', 'Option D']);
    expect(result[0].trap).toBe('Distortion');
    expect(result[1].trap).toBe('Extreme Language');
    expect(result[2].trap).toBe('Calculation Slip');
  });
});

describe('parseMentorExplanation', () => {
  it('returns default fallback when explanation is null or empty', () => {
    const res = parseMentorExplanation('');
    expect(res.correctExplanation).toBe('No explanation currently available.');
    expect(res.steps).toBeNull();
    expect(res.distractors).toEqual([]);
    expect(res.resolvedTrap).toBeNull();
  });

  it('parses structured explanation into steps, correct rationale, and sorted distractors', () => {
    const text = `Why Option C is Correct:
**Step 1:** First understand the reaction quotient Q.
**Step 2:** Compare Q to Keq to determine shift direction.

Why Other Options are Incorrect (Distractor & Trap Breakdown):
- Option D is INCORRECT (Calculation Slip): Inverted Q calculation.
- Option A is INCORRECT (Distortion / Opposite): Reaction shifts right, not left.
- Option B is INCORRECT (Extreme Language): The system never reaches infinite rate.`;

    const parsed = parseMentorExplanation(text, 'Distortion_Opposite');

    expect(parsed.steps).toHaveLength(2);
    expect(parsed.steps[0]).toContain('Step 1:');
    expect(parsed.steps[1]).toContain('Step 2:');

    expect(parsed.distractors).toHaveLength(3);
    // Verify distractors are sorted alphabetically A -> B -> D
    expect(parsed.distractors.map((d) => d.label)).toEqual(['Option A', 'Option B', 'Option D']);
    expect(parsed.distractors[0].trap).toBe('Distortion / Opposite');
    expect(parsed.distractors[1].trap).toBe('Extreme Language');
    expect(parsed.distractors[2].trap).toBe('Calculation Slip');

    expect(parsed.resolvedTrap).not.toBeNull();
  });

  it('handles fallback line-by-line unstructured explanation', () => {
    const text = `The primary mechanism is acid-catalyzed hydrolysis.
Option A is INCORRECT because ester hydrolysis requires water.
Option B is INCORRECT because nucleophilic attack occurs at the carbonyl.
Option D is INCORRECT because amide formation does not occur.`;

    const parsed = parseMentorExplanation(text);
    expect(parsed.correctExplanation).toContain('The primary mechanism is acid-catalyzed hydrolysis.');
    expect(parsed.distractors.length).toBeGreaterThanOrEqual(1);
  });
});
