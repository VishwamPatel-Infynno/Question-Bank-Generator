import React, { useState, useMemo, useEffect } from 'react';
import {
  ArrowLeft,
  Save,
  Trash2,
  BookOpen,
  Layers,
  ChevronLeft,
  ChevronRight
} from 'lucide-react';
import { EMPTY_ARRAY, getSectionBadgeClass } from '../../constants';
import { countWords } from '../../utils';
import PassageVisualStimulusEditor from './PassageVisualStimulusEditor';
import PassageLinkedQuestionCard from './PassageLinkedQuestionCard';

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
  const section = passage?.section || 'cars';
  const subtopic = passage?.subtopic || '';

  // Editable Form State
  const [text, setText] = useState(passage?.text || '');
  const [imageUrl, setImageUrl] = useState(passage?.image_url || '');
  const [imageSvg, setImageSvg] = useState(passage?.image_svg || '');
  const [imageDescription, setImageDescription] = useState(passage?.image_description || '');

  // UI state
  const [isSaving, setIsSaving] = useState(false);
  const [activeQuestionIndex, setActiveQuestionIndex] = useState(0);
  const [editingQuestionId, setEditingQuestionId] = useState(null);

  // Dynamic Word Count
  const liveWordCount = useMemo(() => {
    return countWords(text);
  }, [text]);

  // Safe question index calculation
  const totalQuestions = questions.length;
  const safeIndex = totalQuestions > 0 ? Math.min(Math.max(0, activeQuestionIndex), totalQuestions - 1) : 0;
  const activeQuestion = totalQuestions > 0 ? questions[safeIndex] : null;

  // Question navigation handlers
  const goToPrev = () => {
    if (totalQuestions <= 1) return;
    setActiveQuestionIndex((prev) => (prev > 0 ? prev - 1 : totalQuestions - 1));
    setEditingQuestionId(null);
  };

  const goToNext = () => {
    if (totalQuestions <= 1) return;
    setActiveQuestionIndex((prev) => (prev < totalQuestions - 1 ? prev + 1 : 0));
    setEditingQuestionId(null);
  };

  // Keyboard navigation shortcuts (ArrowLeft / ArrowRight)
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (totalQuestions <= 1) return;
      const activeEl = document.activeElement;
      const isInput =
        activeEl &&
        (activeEl.tagName === 'INPUT' ||
          activeEl.tagName === 'TEXTAREA' ||
          activeEl.isContentEditable);
      if (isInput) return;

      if (e.key === 'ArrowLeft') {
        e.preventDefault();
        setActiveQuestionIndex((prev) => (prev > 0 ? prev - 1 : totalQuestions - 1));
        setEditingQuestionId(null);
      } else if (e.key === 'ArrowRight') {
        e.preventDefault();
        setActiveQuestionIndex((prev) => (prev < totalQuestions - 1 ? prev + 1 : 0));
        setEditingQuestionId(null);
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [totalQuestions]);

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

  const handleSaveQuestion = async (updatedQ) => {
    if (!onUpdateQuestion) {
      setEditingQuestionId(null);
      return;
    }
    try {
      await onUpdateQuestion(updatedQ);
      setEditingQuestionId(null);
    } catch (err) {
      // the hook toasts the failure; leave the editor open with the user's changes
      console.error('Linked question save failed:', err);
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
              {section.toUpperCase()}
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
        <div className="passage-desk-right-col">
          {/* Header with Stepper Carousel */}
          <div className="passage-desk-carousel-header">
            <div className="passage-desk-header-title">
              <Layers size={16} color="var(--brand-primary)" />
              <h3>
                Linked Questions ({totalQuestions})
              </h3>
            </div>

            {totalQuestions > 0 && (
              <div className="passage-desk-stepper">
                <button
                  type="button"
                  onClick={goToPrev}
                  disabled={totalQuestions <= 1}
                  className="btn-secondary passage-desk-stepper-btn"
                  title="Previous Question (Left Arrow ←)"
                >
                  <ChevronLeft size={14} />
                  <span>Prev</span>
                </button>

                <span className="passage-desk-stepper-badge">
                  Question {safeIndex + 1} of {totalQuestions}
                </span>

                <button
                  type="button"
                  onClick={goToNext}
                  disabled={totalQuestions <= 1}
                  className="btn-secondary passage-desk-stepper-btn"
                  title="Next Question (Right Arrow →)"
                >
                  <span>Next</span>
                  <ChevronRight size={14} />
                </button>
              </div>
            )}
          </div>

          {/* Active Question Card / Empty State */}
          {totalQuestions === 0 ? (
            <div className="passage-desk-empty-state">
              <Layers size={32} className="passage-desk-empty-icon" />
              <h4 className="passage-desk-empty-title">
                No Questions Linked Yet
              </h4>
              <p className="passage-desk-empty-desc">
                This reading passage currently has no questions linked to it in the Question Bank. You can generate passage-based questions in the Generator Studio.
              </p>
            </div>
          ) : (
            <PassageLinkedQuestionCard
              key={activeQuestion.id}
              question={activeQuestion}
              index={safeIndex}
              totalQuestions={totalQuestions}
              isEditing={editingQuestionId === activeQuestion.id}
              onToggleEdit={() =>
                setEditingQuestionId(editingQuestionId === activeQuestion.id ? null : activeQuestion.id)
              }
              onSaveQuestion={handleSaveQuestion}
            />
          )}
        </div>
      </div>
    </div>
  );
}
