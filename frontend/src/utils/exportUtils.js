import { formatExamTime } from './formatters';

/**
 * Escapes a cell value for standard comma-separated values (CSV) export.
 * @param {any} val - Value to escape
 * @returns {string} Escaped string wrapped in double quotes if needed
 */
function escapeCsv(val) {
  if (val === null || val === undefined) return '""';
  const str = String(val).replace(/"/g, '""');
  return `"${str}"`;
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
      escapeCsv(
        Array.isArray(q.correct_answer_ids) && q.correct_answer_ids.length > 0
          ? q.correct_answer_ids.join(', ')
          : (q.correct_answer_id || '')
      ),
      escapeCsv(q.explanation || ''),
      escapeCsv(q.primary_trap || ''),
      q.final_score || 0
    ].join(',');
  });

  return [headers.join(','), ...rows].join('\r\n');
}

/**
 * Serializes an array of questions into formatted JSON.
 * @param {Array<object>} questions - Questions dataset
 * @returns {string} Formatted JSON string with 2-space indentation
 */
export function generateExamJson(questions = []) {
  return JSON.stringify(questions || [], null, 2);
}

/**
 * Builds a standalone, print-ready HTML document string formatted for A4 examination papers.
 * @param {Array<object>} questions - Questions to render
 * @param {object} options - Configuration options
 * @param {string} options.paperMode - 'student' (exam only) or 'studypack' (includes answer key and rationales)
 * @returns {string} Full HTML document string with styles and print orchestration script
 */
export function generateExamHtmlDoc(questions = [], { paperMode = 'student' } = {}) {
  if (!questions || questions.length === 0) return '';

  const isStudyPack = paperMode === 'studypack';
  const examDate = new Date().toLocaleDateString('en-GB', {
    day: 'numeric',
    month: 'long',
    year: 'numeric'
  });
  const timeAllowed = formatExamTime(questions);

  const questionsHtml = questions.map((q, idx) => {
    const qNum = idx + 1;
    const svgDiagram = q.image_svg || q.stage_outcomes?.visual_stimulus?.image_svg || '';
    const imgUrl = q.image_url || q.stage_outcomes?.visual_stimulus?.image_url || '';
    const imgDesc = q.image_description || q.stage_outcomes?.visual_stimulus?.description || '';

    const optionsHtml = (q.options || []).map(opt => `
      <div class="option-row">
        <span class="option-bubble">[ &nbsp; ]</span>
        <span class="option-letter"><strong>${opt.id}.</strong></span>
        <span class="option-text">${opt.text || ''}</span>
      </div>
    `).join('');

    return `
      <div class="question-block">
        <div class="question-header">
          <span class="question-number">Question ${qNum}</span>
          <span class="question-meta">${q.section_label || q.section} &bull; ${q.subtopic || ''}</span>
        </div>

        ${q.stimulus_text ? `
          <div class="stimulus-box">
            <div class="stimulus-title">Reading Passage</div>
            <p class="stimulus-content">${q.stimulus_text.replace(/\n\n/g, '</p><p class="stimulus-content">')}</p>
          </div>
        ` : ''}

        ${svgDiagram ? `
          <div class="diagram-box">
            ${svgDiagram}
            ${imgDesc ? `<div class="diagram-caption">${imgDesc}</div>` : ''}
          </div>
        ` : imgUrl ? `
          <div class="diagram-box">
            <img src="${imgUrl}" alt="Stimulus Diagram" />
            ${imgDesc ? `<div class="diagram-caption">${imgDesc}</div>` : ''}
          </div>
        ` : ''}

        <div class="question-stem">${q.question_stem || q.stem || ''}</div>
        <div class="options-grid">${optionsHtml}</div>
      </div>
    `;
  }).join('');

  const answerKeyHtml = isStudyPack ? `
    <div class="page-break"></div>
    <div class="answer-key-section">
      <div class="answer-key-header">
        <h2>Official Answer Key &amp; Diagnostic Rationales</h2>
        <p>AAMC MCAT Examination Standards &bull; Full Psychometric Breakdown</p>
      </div>

      <table class="key-table">
        <thead>
          <tr>
            <th style="width: 60px;">Q#</th>
            <th style="width: 100px;">Key</th>
            <th style="width: 130px;">Trap Defended</th>
            <th>Detailed Explanation</th>
          </tr>
        </thead>
        <tbody>
          ${questions.map((q, idx) => `
            <tr>
              <td style="text-align: center; font-weight: 700;">Q${idx + 1}</td>
              <td style="text-align: center;">
                <span class="correct-badge">${
                  Array.isArray(q.correct_answer_ids) && q.correct_answer_ids.length > 0
                    ? q.correct_answer_ids.join(', ')
                    : (q.correct_answer_id || 'A')
                }</span>
              </td>
              <td style="font-size: 11px; color: #475569;">${q.primary_trap || 'None'}</td>
              <td style="font-size: 11.5px; line-height: 1.5;">${q.explanation || 'No explanation recorded.'}</td>
            </tr>
          `).join('')}
        </tbody>
      </table>
    </div>
  ` : '';

  return `
    <!DOCTYPE html>
    <html lang="en">
    <head>
      <meta charset="utf-8">
      <title>Infynno MCAT Practice Paper (${questions.length} Questions)</title>
      <style>
        @page {
          size: A4 portrait;
          margin: 15mm 16mm;
        }
        * {
          box-sizing: border-box;
        }
        body {
          font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
          color: #0f172a;
          background: #ffffff;
          margin: 0;
          padding: 0;
          font-size: 13px;
          line-height: 1.5;
        }
        .exam-header {
          border-bottom: 2px solid #0f172a;
          padding-bottom: 12px;
          margin-bottom: 20px;
        }
        .header-top {
          display: flex;
          justify-content: space-between;
          align-items: flex-start;
          margin-bottom: 12px;
        }
        .brand-title {
          font-size: 18px;
          font-weight: 800;
          letter-spacing: -0.01em;
          color: #0f172a;
          margin: 0 0 2px 0;
        }
        .brand-subtitle {
          font-size: 12px;
          color: #475569;
          font-weight: 500;
          margin: 0;
        }
        .marks-box {
          border: 1.5px solid #0f172a;
          border-radius: 4px;
          padding: 6px 14px;
          text-align: center;
        }
        .marks-label {
          font-size: 10px;
          text-transform: uppercase;
          font-weight: 700;
          color: #64748b;
        }
        .marks-value {
          font-size: 15px;
          font-weight: 800;
          color: #0f172a;
        }
        .candidate-fields {
          display: grid;
          grid-template-columns: 2fr 1fr 1fr;
          gap: 16px;
          background: #f8fafc;
          border: 1px solid #e2e8f0;
          border-radius: 6px;
          padding: 10px 14px;
          font-size: 12px;
        }
        .field-item {
          display: flex;
          align-items: center;
          gap: 6px;
        }
        .field-label {
          font-weight: 700;
          color: #334155;
          white-space: nowrap;
        }
        .field-line {
          flex: 1;
          border-bottom: 1px dotted #94a3b8;
          height: 14px;
        }
        .instructions-bar {
          margin: 12px 0 20px 0;
          padding: 8px 12px;
          background: #eff6ff;
          border-left: 3px solid #3b82f6;
          font-size: 11px;
          color: #1e3a8a;
          border-radius: 0 4px 4px 0;
        }
        .question-block {
          margin-bottom: 24px;
          page-break-inside: avoid;
          border-bottom: 1px solid #e2e8f0;
          padding-bottom: 18px;
        }
        .question-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 8px;
        }
        .question-number {
          font-size: 14px;
          font-weight: 800;
          color: #0f172a;
        }
        .question-meta {
          font-size: 11px;
          color: #64748b;
          font-weight: 600;
        }
        .stimulus-box {
          background: #f8fafc;
          border: 1px solid #e2e8f0;
          border-radius: 6px;
          padding: 12px 14px;
          margin-bottom: 12px;
        }
        .stimulus-title {
          font-size: 11px;
          font-weight: 700;
          text-transform: uppercase;
          letter-spacing: 0.04em;
          color: #475569;
          margin-bottom: 6px;
        }
        .stimulus-content {
          font-family: Georgia, serif;
          font-size: 12.5px;
          line-height: 1.6;
          color: #1e293b;
          margin: 0 0 8px 0;
        }
        .diagram-box {
          margin: 12px auto;
          text-align: center;
          padding: 10px;
          background: #f8fafc;
          border: 1px solid #e2e8f0;
          border-radius: 6px;
          max-width: 500px;
          page-break-inside: avoid;
        }
        .diagram-box svg, .diagram-box img {
          max-height: 280px;
          max-width: 100%;
          height: auto;
          object-fit: contain;
          display: inline-block;
        }
        .diagram-caption {
          font-size: 11px;
          font-style: italic;
          color: #64748b;
          margin-top: 6px;
          line-height: 1.35;
        }
        .question-stem {
          font-size: 13.5px;
          font-weight: 600;
          color: #0f172a;
          margin: 8px 0 12px 0;
          line-height: 1.45;
        }
        .options-grid {
          display: flex;
          flex-direction: column;
          gap: 6px;
        }
        .option-row {
          display: flex;
          align-items: flex-start;
          gap: 10px;
          padding: 4px 6px;
          border-radius: 4px;
          line-height: 1.45;
        }
        .option-bubble {
          font-family: monospace;
          font-weight: 700;
          color: #94a3b8;
          font-size: 12px;
          white-space: nowrap;
          flex-shrink: 0;
          line-height: 1.45;
        }
        .option-letter {
          font-size: 13px;
          color: #0f172a;
          white-space: nowrap;
          flex-shrink: 0;
          line-height: 1.45;
          min-width: 18px;
        }
        .option-text {
          font-size: 13px;
          color: #1e293b;
          flex: 1;
          line-height: 1.45;
        }
        .page-break {
          page-break-before: always;
          break-before: page;
        }
        .answer-key-section {
          padding-top: 20px;
        }
        .answer-key-header {
          border-bottom: 2px solid #0f172a;
          padding-bottom: 8px;
          margin-bottom: 16px;
        }
        .answer-key-header h2 {
          margin: 0 0 4px 0;
          font-size: 18px;
          font-weight: 800;
        }
        .answer-key-header p {
          margin: 0;
          font-size: 11px;
          color: #64748b;
        }
        .key-table {
          width: 100%;
          border-collapse: collapse;
        }
        .key-table th {
          background: #f1f5f9;
          border: 1px solid #cbd5e1;
          padding: 8px 10px;
          text-align: left;
          font-size: 11px;
          font-weight: 700;
          color: #334155;
          text-transform: uppercase;
        }
        .key-table td {
          border: 1px solid #e2e8f0;
          padding: 8px 10px;
          vertical-align: top;
        }
        .correct-badge {
          display: inline-block;
          background: #10b981;
          color: #ffffff;
          font-weight: 800;
          font-size: 12px;
          padding: 2px 8px;
          border-radius: 4px;
        }
      </style>
    </head>
    <body>
      <div class="exam-header">
        <div class="header-top">
          <div>
            <h1 class="brand-title">Infynno MCAT Practice Examination</h1>
            <p class="brand-subtitle">${paperMode === 'student' ? 'Student Exam Paper (Practice Mode)' : 'Complete Study Pack with Diagnostic Rationales'}</p>
          </div>
          <div class="marks-box">
            <div class="marks-label">Total Marks</div>
            <div class="marks-value">___ / ${questions.length}</div>
          </div>
        </div>

        <div class="candidate-fields">
          <div class="field-item">
            <span class="field-label">Candidate Name:</span>
            <span class="field-line"></span>
          </div>
          <div class="field-item">
            <span class="field-label">Date:</span>
            <span>${examDate}</span>
          </div>
          <div class="field-item">
            <span class="field-label">Time Allowed:</span>
            <span><strong>${timeAllowed}</strong></span>
          </div>
        </div>

        <div class="instructions-bar">
          <strong>Instructions to Candidates:</strong> Answer all ${questions.length} questions under timed exam conditions. Mark your chosen answer choice [A&ndash;E] clearly. Calculators are permitted only for Quantitative Reasoning.
        </div>
      </div>

      <div class="questions-container">
        ${questionsHtml}
      </div>

      ${answerKeyHtml}

      <script>
        window.addEventListener('load', () => {
          const imgs = Array.from(document.images);
          Promise.all(imgs.map(img => {
            if (img.complete) return Promise.resolve();
            return new Promise(resolve => {
              img.onload = resolve;
              img.onerror = resolve;
            });
          })).then(() => {
            setTimeout(() => {
              window.focus();
              window.print();
            }, 250);
          });
        });
      </script>
    </body>
    </html>
  `;
}
