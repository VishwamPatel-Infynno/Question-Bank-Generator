// @vitest-environment jsdom
import { describe, expect, it } from 'vitest';
import { generateExamCsv } from '../export/csv';
import { escapeHtml, escapeInlineMarkdown, safeImageUrl, sanitizeSvg } from '../export/escape';
import { generateExamHtmlDoc } from '../export/htmlDoc';

const question = (over = {}) => ({
  id: 'q1',
  section: 'chem_phys',
  subtopic: 'Kinetics',
  question_stem: 'What happens?',
  options: [
    { id: 'A', text: 'one' },
    { id: 'B', text: 'two' }
  ],
  correct_answer_id: 'A',
  explanation: 'Because.',
  final_score: 95,
  ...over
});

describe('escape helpers', () => {
  it('escapes HTML metacharacters', () => {
    expect(escapeHtml('<img onerror="x"> & \'q\'')).toBe(
      '&lt;img onerror=&quot;x&quot;&gt; &amp; &#39;q&#39;'
    );
    expect(escapeHtml(null)).toBe('');
  });

  it('keeps bold and italic after escaping', () => {
    expect(escapeInlineMarkdown('**b** *i* <b>')).toBe('<strong>b</strong> <em>i</em> &lt;b&gt;');
  });

  it('only accepts plain image locations', () => {
    expect(safeImageUrl('javascript:alert(1)')).toBe('');
    expect(safeImageUrl('//evil.example/x.png')).toBe('');
    expect(safeImageUrl('data:image/svg+xml;base64,AAA')).toBe('');
    expect(safeImageUrl('/api/questions/1/image')).toBe('/api/questions/1/image');
    expect(safeImageUrl('https://a.example/c.png?x=1&y=2')).toBe('https://a.example/c.png?x=1&amp;y=2');
  });

  it('strips scripts and handlers from SVG', () => {
    const clean = sanitizeSvg('<svg onload="x()"><script>alert(1)</script><circle r="2"/></svg>');
    expect(clean).not.toContain('script');
    expect(clean).not.toContain('onload');
    expect(clean).toContain('circle');
  });
});

describe('generateExamCsv', () => {
  it('neutralises spreadsheet formulas and quotes cells', () => {
    const csv = generateExamCsv([question({ question_stem: '=HYPERLINK("x")', explanation: '-2+3' })]);
    const row = csv.split('\r\n')[1];
    expect(row).toContain('"\'=HYPERLINK(""x"")"');
    expect(row).toContain('"\'-2+3"');
  });

  it('returns an empty string for no questions', () => {
    expect(generateExamCsv([])).toBe('');
  });
});

describe('generateExamHtmlDoc', () => {
  it('never lets question text become markup', () => {
    const html = generateExamHtmlDoc(
      [question({ question_stem: '<img src=x onerror=alert(1)>', options: [{ id: 'A', text: 'pH < 7' }] })],
      { paperMode: 'student' }
    );
    expect(html).not.toContain('<img src=x');
    expect(html).toContain('&lt;img src=x');
    expect(html).toContain('pH &lt; 7');
  });

  it('adds the answer key only for study packs', () => {
    expect(generateExamHtmlDoc([question()], { paperMode: 'student' })).not.toContain('Answer Key');
    expect(generateExamHtmlDoc([question()], { paperMode: 'studypack' })).toContain('Answer Key');
  });

  it('returns an empty string for no questions', () => {
    expect(generateExamHtmlDoc([])).toBe('');
  });
});
