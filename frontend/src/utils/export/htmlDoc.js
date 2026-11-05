import { formatExamTime } from '../formatters';
import { PRINT_PAPER_CSS } from './printPaperCss';

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
        ${PRINT_PAPER_CSS}
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
