const EMPTY_QUESTIONS = [];

export default function ExportPaperPreview({
  previewRef,
  paperMode = 'student',
  exportQuestions = EMPTY_QUESTIONS,
  timeAllowed = ''
}) {
  return (
    <div 
      ref={previewRef}
      className="exam-paper-sheet"
    >
      {/* Simulated Paper Header */}
      <div className="exam-paper-header">
        <div className="exam-paper-header-top">
          <div>
            <h3 className="exam-paper-title">
              Infynno MCAT Practice Examination
            </h3>
            <p className="exam-paper-subtitle">
              {paperMode === 'student' ? 'Practice Test (Student Mode - Unsolved Questions)' : 'Complete Study Pack (With Explanations & Answer Key)'}
            </p>
          </div>
          <div className="exam-paper-score-box">
            <div className="exam-paper-score-label">Score</div>
            <div className="exam-paper-score-val">___ / {exportQuestions.length}</div>
          </div>
        </div>

        <div className="exam-paper-meta-grid">
          <div className="exam-paper-meta-item">
            <span className="exam-paper-meta-label">Student Name:</span>
            <span className="exam-paper-meta-line"></span>
          </div>
          <div className="exam-paper-meta-item">
            <span className="exam-paper-meta-label">Date:</span>
            <span className="exam-paper-meta-val">Today</span>
          </div>
          <div className="exam-paper-meta-item">
            <span className="exam-paper-meta-label">Estimated Time:</span>
            <span className="exam-paper-meta-val-highlight">{timeAllowed}</span>
          </div>
        </div>
      </div>

      {/* Simulated Question Items */}
      <div className="exam-paper-questions-list">
        {exportQuestions.map((q, idx) => {
          const qNum = idx + 1;
          const svgDiagram = q.image_svg || q.stage_outcomes?.visual_stimulus?.image_svg || '';
          const imgUrl = q.image_url || q.stage_outcomes?.visual_stimulus?.image_url || '';
          const imgDesc = q.image_description || q.stage_outcomes?.visual_stimulus?.description || '';

          return (
            <div key={q.id || idx} className="exam-paper-question-block">
              <div className="exam-paper-question-header">
                <span className="exam-paper-question-num">
                  Question {qNum}
                </span>
                <span className="exam-paper-question-tag">
                  {q.section_label || q.section} &bull; {q.subtopic || ''}
                </span>
              </div>

              {q.stimulus_text && (
                <div className="exam-paper-stimulus">
                  {q.stimulus_text}
                </div>
              )}

              {svgDiagram ? (
                <div className="exam-paper-diagram-box">
                  <div dangerouslySetInnerHTML={{ __html: svgDiagram }} />
                  {imgDesc && (
                    <div className="exam-paper-diagram-caption">
                      {imgDesc}
                    </div>
                  )}
                </div>
              ) : imgUrl ? (
                <div className="exam-paper-diagram-box">
                  <img 
                    src={imgUrl} 
                    alt="Stimulus Diagram" 
                    className="exam-paper-diagram-img" 
                  />
                  {imgDesc && (
                    <div className="exam-paper-diagram-caption">
                      {imgDesc}
                    </div>
                  )}
                </div>
              ) : null}

              <div className="exam-paper-stem">
                {q.question_stem || q.stem || ''}
              </div>

              <div className="exam-paper-options-list">
                {(q.options || []).map(opt => (
                  <div key={opt.id} className="exam-paper-option-row">
                    <span className="exam-paper-option-bubble">[ &nbsp; ]</span>
                    <strong className="exam-paper-option-letter">{opt.id}.</strong>
                    <span className="exam-paper-option-text">{opt.text}</span>
                  </div>
                ))}
              </div>
            </div>
          );
        })}

        {paperMode === 'studypack' && (
          <div className="exam-paper-answer-key">
            <h4 className="exam-paper-key-title">
              Answer Key &amp; Diagnostic Rationales
            </h4>
            <div className="exam-paper-key-list">
              {exportQuestions.map((q, idx) => (
                <div key={q.id || idx} className="exam-paper-key-card">
                  <div className="exam-paper-key-meta">
                    <strong className="exam-paper-score-val">Q{idx + 1}:</strong>
                    <span className="exam-paper-key-badge">
                      Correct: {Array.isArray(q.correct_answer_ids) && q.correct_answer_ids.length > 0 ? q.correct_answer_ids.join(', ') : (q.correct_answer_id || 'A')}
                    </span>
                    {q.primary_trap && (
                      <span className="exam-paper-key-trap">Trap: {q.primary_trap}</span>
                    )}
                  </div>
                  <div className="exam-paper-key-explanation">{q.explanation}</div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
