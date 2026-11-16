import { useState, useEffect } from 'react';
import { Layers, ChevronLeft, ChevronRight } from 'lucide-react';
import { EMPTY_ARRAY } from '../../constants';
import PassageLinkedQuestionCard from './PassageLinkedQuestionCard';

/**
 * PassageQuestionsCarousel
 *
 * Encapsulated right-column carousel for linked questions in the Passage Editorial Desk:
 * - Stepper header (Prev / Next buttons, "Question X of N" indicator)
 * - Keyboard navigation (Left / Right arrow keys when form inputs are not focused)
 * - Active question editing state and save delegation
 * - Empty state illustration when no questions are linked
 *
 * @param {Object} props
 * @param {Array<Object>} [props.questions] - List of questions linked to the current passage.
 * @param {(question: Object) => Promise<void>} [props.onUpdateQuestion] - Update callback when a question is edited.
 * @returns {JSX.Element}
 */
export default function PassageQuestionsCarousel({
  questions = EMPTY_ARRAY,
  onUpdateQuestion
}) {
  const [activeQuestionIndex, setActiveQuestionIndex] = useState(0);
  const [editingQuestionId, setEditingQuestionId] = useState(null);

  const totalQuestions = questions.length;
  const safeIndex =
    totalQuestions > 0 ? Math.min(Math.max(0, activeQuestionIndex), totalQuestions - 1) : 0;
  const activeQuestion = totalQuestions > 0 ? questions[safeIndex] : null;

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

  const handleSaveQuestion = async (updatedQ) => {
    if (!onUpdateQuestion) {
      setEditingQuestionId(null);
      return;
    }
    try {
      await onUpdateQuestion(updatedQ);
      setEditingQuestionId(null);
    } catch (err) {
      // the parent/hook toasts the failure; leave the editor open with the user's changes
      console.error('Linked question save failed:', err);
    }
  };

  return (
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
  );
}
