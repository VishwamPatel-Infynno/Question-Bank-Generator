import { Sparkles, Loader2, Download, FileText } from 'lucide-react';
import { EMPTY_ARRAY } from '../../constants';

export default function StudyGuideExportPane({
  studyGuide = null,
  isSynthesizingGuide = false,
  exportQuestions = EMPTY_ARRAY,
  handleSynthesizeGuide
}) {
  const handleDownloadAnkiDeck = () => {
    if (!studyGuide) return;
    const cards = studyGuide.flashcards || [];
    if (cards.length === 0) return;

    const header = '#separator:tab\n#html:true\n#tags column:3\n';
    const rows = cards.map((c) => {
      const front = (c.front || '').replace(/\t/g, ' ').replace(/\n/g, '<br>');
      const back = (c.back || '').replace(/\t/g, ' ').replace(/\n/g, '<br>');
      const tags = 'MCAT QuestionStudio HighYield';
      return `${front}\t${back}\t${tags}`;
    });

    const tsvContent = header + rows.join('\n');
    const blob = new Blob([tsvContent], { type: 'text/tab-separated-values;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `Anki_${(studyGuide.title || 'MCAT_Deck').replace(/[^a-zA-Z0-9_-]/g, '_')}.tsv`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  const handleDownloadMarkdown = () => {
    if (!studyGuide?.markdown_guide) return;
    const blob = new Blob([studyGuide.markdown_guide], { type: 'text/markdown;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `${(studyGuide.title || 'MCAT_Study_Guide').replace(/[^a-zA-Z0-9_-]/g, '_')}.md`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  return (
    <div className="exam-export-tab-pane study-guide-tab-pane">
      <div className="exam-export-callout study-guide-callout">
        <div>
          <strong>AI-Powered Study Guide &amp; Flashcard Synthesis:</strong> Transforms the
          selected {exportQuestions.length} questions into an integrated high-yield cheat
          sheet with trap checklists and active-recall cards.
        </div>
        {!studyGuide && (
          <button
            type="button"
            onClick={handleSynthesizeGuide}
            disabled={isSynthesizingGuide || exportQuestions.length === 0}
            className="btn-primary study-guide-btn-synthesize"
          >
            {isSynthesizingGuide ? (
              <>
                <Loader2 size={13} className="animate-spin" />
                <span>Synthesizing Guide...</span>
              </>
            ) : (
              <>
                <Sparkles size={13} />
                <span>Generate Study Guide</span>
              </>
            )}
          </button>
        )}
      </div>

      {studyGuide ? (
        <div className="study-guide-body">
          <div className="study-guide-header-card">
            <div className="study-guide-header-top">
              <div>
                <h4 className="study-guide-title">{studyGuide.title}</h4>
                <p className="study-guide-summary">{studyGuide.summary}</p>
              </div>
              <div className="study-guide-actions">
                <button
                  type="button"
                  onClick={handleDownloadAnkiDeck}
                  className="study-guide-action-btn"
                  title="Download Anki-compatible tab-separated flashcard deck"
                >
                  <Download size={13} />
                  <span>Download Anki Deck (.tsv)</span>
                </button>
                <button
                  type="button"
                  onClick={handleDownloadMarkdown}
                  className="study-guide-action-btn"
                  title="Download Markdown summary document"
                >
                  <FileText size={13} />
                  <span>Download Markdown (.md)</span>
                </button>
              </div>
            </div>
          </div>

          {studyGuide.top_traps?.length > 0 && (
            <div className="study-guide-traps-card">
              <strong className="study-guide-traps-title">Top Misconceptions &amp; Traps Tested:</strong>
              <ul className="study-guide-traps-list">
                {studyGuide.top_traps.map((trap, idx) => (
                  <li key={idx}>{trap}</li>
                ))}
              </ul>
            </div>
          )}

          <div className="exam-export-code-preview study-guide-code-preview">
            {studyGuide.markdown_guide}
          </div>
        </div>
      ) : !isSynthesizingGuide ? (
        <div className="study-guide-empty-state">
          Click <strong>&quot;Generate Study Guide&quot;</strong> to synthesize an active-recall cheat sheet for these {exportQuestions.length} questions.
        </div>
      ) : null}
    </div>
  );
}
