
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
      style={{
        background: '#ffffff',
        color: '#0f172a',
        borderRadius: 'var(--radius-sm)',
        border: '1px solid rgba(0,0,0,0.12)',
        padding: '24px 28px',
        boxShadow: '0 8px 24px rgba(0,0,0,0.15)',
        maxHeight: '440px',
        overflowY: 'auto',
        fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif'
      }}
    >
      {/* Simulated Paper Header */}
      <div style={{ borderBottom: '2px solid #0f172a', paddingBottom: '12px', marginBottom: '18px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '12px' }}>
          <div>
            <h3 style={{ margin: '0 0 2px 0', fontSize: '1.1rem', fontWeight: 800, color: '#0f172a' }}>
              Infynno MCAT Practice Examination
            </h3>
            <p style={{ margin: 0, fontSize: '0.78rem', color: '#64748b', fontWeight: 500 }}>
              {paperMode === 'student' ? 'Practice Test (Student Mode - Unsolved Questions)' : 'Complete Study Pack (With Explanations & Answer Key)'}
            </p>
          </div>
          <div style={{ border: '1.5px solid #0f172a', borderRadius: '4px', padding: '4px 10px', textAlign: 'center' }}>
            <div style={{ fontSize: '0.62rem', textTransform: 'uppercase', fontWeight: 700, color: '#64748b' }}>Score</div>
            <div style={{ fontSize: '0.9rem', fontWeight: 800, color: '#0f172a' }}>___ / {exportQuestions.length}</div>
          </div>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr 1fr', gap: '12px', background: '#f8fafc', border: '1px solid #e2e8f0', borderRadius: '6px', padding: '8px 12px', fontSize: '0.75rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <span style={{ fontWeight: 700, color: '#334155' }}>Student Name:</span>
            <span style={{ flex: 1, borderBottom: '1px dotted #94a3b8', height: '12px' }}></span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <span style={{ fontWeight: 700, color: '#334155' }}>Date:</span>
            <span style={{ color: '#475569' }}>Today</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <span style={{ fontWeight: 700, color: '#334155' }}>Estimated Time:</span>
            <span style={{ color: '#0f172a', fontWeight: 700 }}>{timeAllowed}</span>
          </div>
        </div>
      </div>

      {/* Simulated Question Items */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
        {exportQuestions.map((q, idx) => {
          const qNum = idx + 1;
          const svgDiagram = q.image_svg || q.stage_outcomes?.visual_stimulus?.image_svg || '';
          const imgUrl = q.image_url || q.stage_outcomes?.visual_stimulus?.image_url || '';
          const imgDesc = q.image_description || q.stage_outcomes?.visual_stimulus?.description || '';

          return (
            <div key={q.id || idx} style={{ borderBottom: '1px solid #e2e8f0', paddingBottom: '16px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '6px' }}>
                <span style={{ fontWeight: 800, fontSize: '0.88rem', color: '#0f172a' }}>
                  Question {qNum}
                </span>
                <span style={{ fontSize: '0.72rem', color: '#64748b', fontWeight: 600 }}>
                  {q.section_label || q.section} &bull; {q.subtopic || ''}
                </span>
              </div>

              {q.stimulus_text && (
                <div style={{ background: '#f8fafc', border: '1px solid #e2e8f0', borderRadius: '4px', padding: '10px 12px', marginBottom: '10px', fontSize: '0.8rem', fontFamily: 'Georgia, serif', lineHeight: 1.5, color: '#1e293b' }}>
                  {q.stimulus_text}
                </div>
              )}

              {svgDiagram ? (
                <div 
                  style={{ margin: '8px auto', textAlign: 'center', padding: '8px', background: '#f8fafc', border: '1px solid #e2e8f0', borderRadius: '4px', maxWidth: '380px' }}
                >
                  <div dangerouslySetInnerHTML={{ __html: svgDiagram }} />
                  {imgDesc && (
                    <div style={{ fontSize: '0.72rem', fontStyle: 'italic', color: '#64748b', marginTop: '6px' }}>
                      {imgDesc}
                    </div>
                  )}
                </div>
              ) : imgUrl ? (
                <div 
                  style={{ margin: '8px auto', textAlign: 'center', padding: '8px', background: '#f8fafc', border: '1px solid #e2e8f0', borderRadius: '4px', maxWidth: '380px' }}
                >
                  <img 
                    src={imgUrl} 
                    alt="Stimulus Diagram" 
                    style={{ maxHeight: '220px', maxWidth: '100%', objectFit: 'contain', borderRadius: '2px', display: 'inline-block' }} 
                  />
                  {imgDesc && (
                    <div style={{ fontSize: '0.72rem', fontStyle: 'italic', color: '#64748b', marginTop: '6px' }}>
                      {imgDesc}
                    </div>
                  )}
                </div>
              ) : null}

              <div style={{ fontWeight: 600, fontSize: '0.84rem', color: '#0f172a', marginBottom: '8px' }}>
                {q.question_stem || q.stem || ''}
              </div>

              <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                {(q.options || []).map(opt => (
                  <div key={opt.id} style={{ display: 'flex', alignItems: 'flex-start', gap: '8px', fontSize: '0.8rem', color: '#1e293b', lineHeight: 1.45 }}>
                    <span style={{ color: '#94a3b8', fontFamily: 'monospace', fontWeight: 700, flexShrink: 0, lineHeight: 1.45, userSelect: 'none' }}>[ &nbsp; ]</span>
                    <strong style={{ minWidth: '18px', flexShrink: 0, lineHeight: 1.45, color: '#0f172a' }}>{opt.id}.</strong>
                    <span style={{ flex: 1, lineHeight: 1.45 }}>{opt.text}</span>
                  </div>
                ))}
              </div>
            </div>
          );
        })}

        {paperMode === 'studypack' && (
          <div style={{ marginTop: '16px', paddingTop: '16px', borderTop: '2px solid #0f172a' }}>
            <h4 style={{ margin: '0 0 8px 0', fontSize: '0.95rem', fontWeight: 800, color: '#0f172a' }}>
              Answer Key &amp; Diagnostic Rationales
            </h4>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
              {exportQuestions.map((q, idx) => (
                <div key={q.id || idx} style={{ padding: '8px 10px', background: '#f8fafc', border: '1px solid #e2e8f0', borderRadius: '4px', fontSize: '0.78rem' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
                    <strong style={{ color: '#0f172a' }}>Q{idx + 1}:</strong>
                    <span style={{ background: '#10b981', color: '#ffffff', fontWeight: 700, padding: '1px 6px', borderRadius: '3px', fontSize: '0.7rem' }}>
                      Correct: {Array.isArray(q.correct_answer_ids) && q.correct_answer_ids.length > 0 ? q.correct_answer_ids.join(', ') : (q.correct_answer_id || 'A')}
                    </span>
                    {q.primary_trap && (
                      <span style={{ color: '#64748b', fontSize: '0.7rem' }}>Trap: {q.primary_trap}</span>
                    )}
                  </div>
                  <div style={{ color: '#334155', lineHeight: 1.4 }}>{q.explanation}</div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
