import { useState, useMemo } from 'react';
import {
  ArrowLeft,
  Save,
  Trash2,
  BookOpen,
  Layers
} from 'lucide-react';
import { EMPTY_ARRAY, getSectionBadgeClass, getSectionShortLabel, SECTION_IDS } from '../../constants';
import { countWords } from '../../utils';
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
  onUpdateQuestion
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
            title="Return to Passages table"
          >
            <ArrowLeft size={14} />
            <span>Back to Passages</span>
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

            <div className="passage-desk-word-count">
              Live Word Count: <strong>{liveWordCount}</strong>
            </div>
          </div>

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
