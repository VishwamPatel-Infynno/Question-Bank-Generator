import { useState } from 'react';
import { AlertTriangle, Trash2, BookOpen, Layers } from 'lucide-react';
import { Modal } from '../common';

/**
 * DeletePassageModal
 *
 * Modal for confirming cascade deletion of reading passages and their associated questions.
 * Built on the unified Modal primitive with WCAG AA accessibility, focus trapping, and keyboard controls.
 */
export default function DeletePassageModal({
  isOpen,
  onClose,
  passage,
  onConfirmDelete
}) {
  const [isDeleting, setIsDeleting] = useState(false);
  const [errorMessage, setErrorMessage] = useState(null);

  if (!isOpen || !passage) return null;

  const titleOrId = passage.title || passage.id;
  const questionCount = typeof passage.question_count === 'number'
    ? passage.question_count
    : (Array.isArray(passage.questions) ? passage.questions.length : 0);

  const handleConfirm = async () => {
    if (isDeleting) return;
    setIsDeleting(true);
    setErrorMessage(null);
    try {
      await onConfirmDelete(passage);
      onClose();
    } catch (err) {
      console.error('Failed to cascade delete passage:', err);
      setErrorMessage(err.message || 'Failed to delete passage and associated questions.');
    } finally {
      setIsDeleting(false);
    }
  };

  const iconElement = (
    <div className="delete-passage-icon-wrap">
      <AlertTriangle size={18} />
    </div>
  );

  const footer = (
    <>
      <button
        type="button"
        onClick={onClose}
        disabled={isDeleting}
        className="btn-secondary delete-passage-cancel-btn"
      >
        Cancel
      </button>

      <button
        type="button"
        id="btn-confirm-delete-passage"
        onClick={handleConfirm}
        disabled={isDeleting}
        className={`delete-passage-confirm-btn ${isDeleting ? 'deleting' : ''}`}
      >
        {isDeleting ? (
          <>
            <div className="lazy-spinner-ring delete-passage-spinner" />
            <span>Deleting...</span>
          </>
        ) : (
          <>
            <Trash2 size={14} />
            <span>
              {questionCount > 0
                ? `Delete Passage & ${questionCount} Question${questionCount === 1 ? '' : 's'}`
                : 'Delete Passage'}
            </span>
          </>
        )}
      </button>
    </>
  );

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="Delete Reading Passage"
      subtitle="Delete passage and linked questions"
      icon={iconElement}
      maxWidth="520px"
      isProcessing={isDeleting}
      footer={footer}
    >
      <div className="delete-passage-stack">
        {/* Passage Overview Card */}
        <div className="delete-passage-card">
          <div className="delete-passage-card-header">
            <div className="delete-passage-title-row">
              <BookOpen size={14} color="var(--brand-primary)" />
              <strong className="delete-passage-title-text">
                {titleOrId}
              </strong>
            </div>
            <div className="delete-passage-badges-row">
              {passage.section && (
                <span className="delete-passage-section-chip">
                  {passage.section}
                </span>
              )}
              {typeof passage.word_count === 'number' && passage.word_count > 0 && (
                <span className="delete-passage-words-chip">
                  {passage.word_count} words
                </span>
              )}
            </div>
          </div>

          {passage.text && (
            <p className="delete-passage-excerpt">
              "{passage.text.slice(0, 160).trim()}..."
            </p>
          )}

          <div className="delete-passage-id-tag">
            ID: {passage.id}
          </div>
        </div>

        {/* Cascade Warning Callout */}
        <div
          id="delete-passage-desc"
          className="delete-passage-warning-box"
        >
          <div className="delete-passage-warning-content">
            <div className="delete-passage-warning-title-row">
              <Layers size={16} />
              <strong className="delete-passage-warning-heading">
                {questionCount > 0
                  ? `Linked Questions Will Be Deleted (${questionCount} Question${questionCount === 1 ? '' : 's'})`
                  : 'Delete Confirmation'}
              </strong>
            </div>

            <p className="delete-passage-warning-p">
              {questionCount > 0 ? (
                <>
                  Deleting this passage will <strong>remove it from the Passage Bank and remove its {questionCount} associated question{questionCount === 1 ? '' : 's'}</strong> from your Question Bank and Review queue. Don't worry, your questions and generation records will <strong>remain safely preserved in your Batch Progress</strong> history.
                </>
              ) : (
                <>
                  Deleting this passage will remove it from the Passage Bank. It will remain preserved in your Batch Progress history.
                </>
              )}
            </p>

            <span className="delete-passage-warning-note">
              You can view and restore deleted questions anytime from the Batch Progress tab.
            </span>
          </div>
        </div>

        {/* Error Message if deletion failed */}
        {errorMessage && (
          <div className="delete-passage-error-box">
            {errorMessage}
          </div>
        )}
      </div>
    </Modal>
  );
}
