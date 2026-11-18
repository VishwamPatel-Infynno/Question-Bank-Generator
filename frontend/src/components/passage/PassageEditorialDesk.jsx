import { useState, useMemo } from 'react';
import {
  ArrowLeft,
  Save,
  Trash2,
  BookOpen,
  Layers,
  Sparkles,
  Activity
} from 'lucide-react';
import { EMPTY_ARRAY, getSectionBadgeClass, getSectionShortLabel, SECTION_IDS } from '../../constants';
import { countWords } from '../../utils';
import { fetchPassageAudit } from '../../services/api';
import PassageVisualStimulusEditor from './PassageVisualStimulusEditor';
import PassageQuestionsCarousel from './PassageQuestionsCarousel';

/**
 * PassageEditorialDesk
 *
 * Dedicated side-by-side MCAT editorial workspace:
 * - Left Pane: Passage typography, live word counter, and visual stimulus figure showcase (with Discard option)
 * - Right Pane: Interactive single-question carousel (<- Question 1 of N ->) with quick-jump pills and keyboard shortcuts
 */
export default function PassageEditorialDesk({
  passage,
  questions = EMPTY_ARRAY,
  onBack,
  onSavePassage,
  onDeletePassage,
  onUpdateQuestion,
  onNavigateToWizard,
  onExpandPassageSet
}) {
  // Immutable Passage Metadata
  const title = passage?.title || '';
  const section = passage?.section || SECTION_IDS.CARS;
  const subtopic = passage?.subtopic || '';

  // Editable Form State
  const [text, setText] = useState(passage?.text || '');
  const [imageUrl, setImageUrl] = useState(passage?.image_url || '');
  const [imageSvg, setImageSvg] = useState(passage?.image_svg || '');
  const [imageDescription, setImageDescription] = useState(passage?.image_description || '');

  // UI state
  const [isSaving, setIsSaving] = useState(false);
  const [auditData, setAuditData] = useState(null);
  const [isAuditing, setIsAuditing] = useState(false);
  const [showAudit, setShowAudit] = useState(false);

  const handleRunAudit = async () => {
    if (isAuditing || !text.trim()) return;
    setIsAuditing(true);
    try {
      const data = await fetchPassageAudit(text);
      setAuditData(data);
      setShowAudit(true);
    } catch (err) {
      console.error('Passage audit error:', err);
    } finally {
      setIsAuditing(false);
    }
  };

  // Dynamic Word Count
  const liveWordCount = useMemo(() => {
    return countWords(text);
  }, [text]);

  const totalQuestions = questions.length;

  const handleDiscardImage = () => {
    setImageUrl('');
    setImageSvg('');
    setImageDescription('');
  };

  const handleSave = async () => {
    if (isSaving) return;
    setIsSaving(true);
    try {
      const payload = {
        ...passage,
        id: passage.id,
        title: title.trim() || `${subtopic || 'MCAT'} Passage`,
        section,
        subtopic: subtopic.trim(),
        text: text.trim(),
        word_count: liveWordCount,
        image_url: imageUrl.trim() || null,
        image_svg: imageSvg.trim() || null,
        image_description: imageDescription.trim() || null
      };
      await onSavePassage(payload);
    } catch (err) {
      // usePassageBank has already shown the failure toast; the edits stay in the editor
      console.error('Passage save failed:', err);
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <div className="passage-desk-container">
      {/* ── Top Bar: Navigation & Action Controls ──────────────────────── */}
      <div className="passage-desk-topbar">
        <div className="passage-desk-topbar-meta">
          <button
            type="button"
            onClick={onBack}
            className="btn-secondary"
            title="Return to Passage Bank"
          >
            <ArrowLeft size={14} />
            <span>Back to Passage Bank</span>
          </button>

          <div className="passage-desk-divider" />

          <div className="passage-desk-title-group">
            <span className={`badge ${getSectionBadgeClass(section)}`}>
              {getSectionShortLabel(section)}
            </span>
            {subtopic && (
              <span className="passage-desk-pill-subtopic">
                {subtopic}
              </span>
            )}
            <span className="passage-desk-title">
              {title || `${subtopic || 'MCAT'} Passage`}
            </span>
          </div>

          <span className="passage-desk-pill-words">
            {liveWordCount} words
          </span>

          <span className="passage-desk-pill-linked">
            <Layers size={11} />
            <span>{totalQuestions} {totalQuestions === 1 ? 'question' : 'questions'} linked</span>
          </span>
        </div>

        <div className="passage-desk-topbar-actions">
          {(onExpandPassageSet || onNavigateToWizard) && (
            <button
              type="button"
              id="btn-expand-passage-set"
              onClick={() => {
                if (onExpandPassageSet) {
                  onExpandPassageSet(passage);
                } else if (onNavigateToWizard) {
                  onNavigateToWizard({
                    passage_id: passage?.id,
                    section,
                    subtopic,
                    shared_passage_text: text,
                    shared_stimulus: text,
                    passage_mode: 'existing_passage',
                    totalQuestions: 5,
                    step: 3
                  });
                }
              }}
              className="btn-secondary passage-desk-expand-btn"
              title="Generate a fresh, non-overlapping 5-question cognitive set for this passage"
            >
              <Sparkles size={13} color="var(--brand-primary)" />
              <span>Generate 5 More Questions</span>
            </button>
          )}

          {onDeletePassage && (
            <button
              type="button"
              onClick={() => onDeletePassage(passage)}
              className="btn-ghost passage-desk-delete-btn"
              title="Delete this passage and all linked questions"
            >
              <Trash2 size={13} />
              <span>Delete Passage</span>
            </button>
          )}

          <button
            type="button"
            id="btn-save-passage"
            onClick={handleSave}
            disabled={isSaving || !text.trim()}
            className="btn-primary"
          >
            <Save size={13} />
            <span>{isSaving ? 'Saving Changes...' : 'Save Passage Changes'}</span>
          </button>
        </div>
      </div>

      {/* ── Side-By-Side Editorial Desk Grid ─────────────────────────────── */}
      <div className="passage-editorial-grid">
        {/* ── LEFT COLUMN: Passage Editor ───────────────────────────────── */}
        <div className="passage-desk-left-col">
          <div className="passage-desk-header">
            <div className="passage-desk-header-title">
              <BookOpen size={16} color="var(--brand-primary)" />
              <h3>
                Passage Content &amp; Reading Text
              </h3>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <button
                type="button"
                onClick={handleRunAudit}
                disabled={isAuditing || !text.trim()}
                className="btn-secondary"
                style={{ padding: '3px 9px', fontSize: '0.74rem', gap: '5px', display: 'inline-flex', alignItems: 'center' }}
                title="Evaluate reading level, empirical density, and AAMC stylistic alignment"
              >
                <Sparkles size={12} color="var(--brand-primary)" />
                <span>{isAuditing ? 'Analyzing...' : 'AI Diagnostics'}</span>
              </button>

              <div className="passage-desk-word-count">
                Live Word Count: <strong>{liveWordCount}</strong>
              </div>
            </div>
          </div>

          {/* AI Passage Diagnostics Panel */}
          {showAudit && auditData && (
            <div
              style={{
                background: 'var(--bg-hover)',
                border: '1px solid var(--border-medium)',
                borderRadius: 'var(--radius-sm)',
                padding: '12px 14px',
                marginBottom: '14px',
                display: 'flex',
                flexDirection: 'column',
                gap: '8px'
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <span style={{ fontWeight: 600, fontSize: '0.8rem', display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <Activity size={13} color="var(--brand-primary)" />
                  <span>AAMC Passage Diagnostics</span>
                </span>
                <span className="badge-minimal" style={{ fontSize: '0.72rem' }}>
                  Score: {auditData.aamc_alignment_score}/100
                </span>
              </div>

              <div style={{ display: 'flex', gap: '14px', flexWrap: 'wrap', fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
                <span>Grade Level: <strong>{auditData.flesch_kincaid_grade}</strong></span>
                <span>Reading Ease: <strong>{auditData.reading_ease}</strong></span>
                <span>Empirical Anchors: <strong>{auditData.empirical_density_score}</strong></span>
                <span>Sentences: <strong>{auditData.sentence_count}</strong></span>
              </div>

              {auditData.diagnostics?.length > 0 && (
                <ul style={{ margin: '4px 0 0 16px', padding: 0, fontSize: '0.74rem', color: 'var(--text-primary)', lineHeight: 1.45 }}>
                  {auditData.diagnostics.map((d, i) => (
                    <li key={i}>{d}</li>
                  ))}
                </ul>
              )}
            </div>
          )}

          {/* Passage Textarea */}
          <div>
            <div className="passage-desk-label-row">
              <label className="passage-desk-label">
                Passage Content (Rendered in MCAT Newsreader Serif)
              </label>
              <span className="passage-desk-subhint">
                Supports standard academic paragraphs
              </span>
            </div>

            <textarea
              id="passage-editor-textarea"
              rows={16}
              value={text}
              onChange={(e) => setText(e.target.value)}
              placeholder="Paste or write the MCAT reading passage text here..."
              className="passage-desk-textarea"
            />
          </div>

          {/* ── Visual Stimulus Showcase & Discard Option ─────────────────── */}
          <PassageVisualStimulusEditor
            imageUrl={imageUrl}
            imageSvg={imageSvg}
            imageDescription={imageDescription}
            onDescriptionChange={setImageDescription}
            onDiscardImage={handleDiscardImage}
          />
        </div>

        {/* ── RIGHT COLUMN: Linked Questions Carousel ───────────────────── */}
        <PassageQuestionsCarousel
          questions={questions}
          onUpdateQuestion={onUpdateQuestion}
        />
      </div>
    </div>
  );
}
