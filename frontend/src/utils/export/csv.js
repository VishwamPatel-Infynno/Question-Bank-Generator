import { formatCorrectAnswers } from '../questionHelpers';
// CSV export of the question bank.
/**
 * Escapes a cell value for standard comma-separated values (CSV) export.
 * @param {any} val - Value to escape
 * @returns {string} Escaped string wrapped in double quotes if needed
 */
function escapeCsv(val) {
  if (val === null || val === undefined) return '""';
  let str = String(val);
  // Spreadsheets run cells that start with = + - @ (or tab/CR) as formulas, and question text is
  // LLM-generated: a leading apostrophe turns such a cell into plain text.
  if (/^[=+\-@\t\r]/.test(str)) str = `'${str}`;
  return `"${str.replace(/"/g, '""')}"`;
}

/**
 * Generates an RFC-4180 compliant CSV string for an array of MCAT questions.
 * @param {Array<object>} questions - Questions dataset to export
 * @returns {string} Formatted CSV string
 */
export function generateExamCsv(questions = []) {
  if (!questions || questions.length === 0) return '';

  const headers = [
    'Question Number',
    'ID',
    'Section',
    'Subtopic',
    'Difficulty',
    'Stimulus / Passage',
    'Question Stem',
    'Visual Type',
    'Image URL',
    'Image Description',
    'Option A',
    'Option B',
    'Option C',
    'Option D',
    'Correct Answer',
    'Explanation',
    'Primary Trap',
    'Quality Score'
  ];

  const rows = questions.map((q, idx) => {
    const opts = {};
    (q.options || []).forEach(opt => {
      opts[opt.id?.toUpperCase()] = opt.text || '';
    });

    const imgUrl = q.image_url 
      ? (q.image_url.startsWith('data:') ? `/api/questions/${q.id}/image` : q.image_url)
      : (q.image_svg ? `/api/questions/${q.id}/image` : '');
    const imgDesc = q.image_description || q.stage_outcomes?.visual_stimulus?.description || '';
    const visualType = q.visual_type || (imgUrl || q.image_svg ? 'Visual' : 'None');

    return [
      idx + 1,
      escapeCsv(q.id),
      escapeCsv(q.section_label || q.section),
      escapeCsv(q.subtopic || ''),
      escapeCsv(q.difficulty || ''),
      escapeCsv(q.stimulus_text || ''),
      escapeCsv(q.question_stem || q.stem || ''),
      escapeCsv(visualType),
      escapeCsv(imgUrl),
      escapeCsv(imgDesc),
      escapeCsv(opts['A'] || ''),
      escapeCsv(opts['B'] || ''),
      escapeCsv(opts['C'] || ''),
      escapeCsv(opts['D'] || ''),
      escapeCsv(formatCorrectAnswers(q)),
      escapeCsv(q.explanation || ''),
      escapeCsv(q.primary_trap || ''),
      q.final_score || 0
    ].join(',');
  });

  return [headers.join(','), ...rows].join('\r\n');
}
