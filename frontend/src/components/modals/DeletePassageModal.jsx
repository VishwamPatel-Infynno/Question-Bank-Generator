import React, { useState } from 'react';
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
    <div
      style={{
        width: '34px',
        height: '34px',
        borderRadius: 'var(--radius-sm, 8px)',
        backgroundColor: 'rgba(244, 63, 94, 0.18)',
        color: 'var(--status-danger, #f43f5e)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center'
      }}
    >
      <AlertTriangle size={18} />
    </div>
  );

  const footer = (
    <>
      <button
        type="button"
        onClick={onClose}
        disabled={isDeleting}
        className="btn-secondary"
        style={{
          padding: '7px 14px',
          fontSize: '0.82rem',
          cursor: isDeleting ? 'not-allowed' : 'pointer'
        }}
      >
        Cancel
      </button>

      <button
        type="button"
        id="btn-confirm-delete-passage"
        onClick={handleConfirm}
        disabled={isDeleting}
        style={{
          display: 'inline-flex',
          alignItems: 'center',
          gap: '6px',
          padding: '7px 16px',
          fontSize: '0.82rem',
          fontWeight: 600,
          color: '#ffffff',
          backgroundColor: isDeleting ? 'rgba(244, 63, 94, 0.6)' : 'var(--status-danger, #f43f5e)',
          border: 'none',
          borderRadius: 'var(--radius-sm, 8px)',
          cursor: isDeleting ? 'not-allowed' : 'pointer',
          transition: 'background-color 0.15s ease'
        }}
      >
        {isDeleting ? (
          <>
            <div
              className="lazy-spinner-ring"
              style={{ width: '13px', height: '13px', borderWidth: '2px', marginRight: '4px' }}
            />
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
      ariaLabelledBy="delete-passage-title"
    >
      <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
        {/* Passage Overview Card */}
        <div
          style={{
            padding: '12px 14px',
            borderRadius: 'var(--radius-md, 12px)',
            backgroundColor: 'var(--bg-surface-subtle)',
            border: '1px solid var(--border-light)',
            display: 'flex',
            flexDirection: 'column',
            gap: '8px'
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '10px', flexWrap: 'wrap' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <BookOpen size={14} style={{ color: 'var(--brand-primary)' }} />
              <strong
                style={{
                  fontSize: '0.9rem',
                  color: 'var(--text-primary)',
                  wordBreak: 'break-word'
                }}
              >
                {titleOrId}
              </strong>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              {passage.section && (
                <span
                  style={{
                    fontSize: '0.68rem',
                    fontWeight: 600,
                    textTransform: 'uppercase',
                    padding: '2px 6px',
                    borderRadius: 'var(--radius-xs, 4px)',
                    backgroundColor: 'var(--brand-light)',
                    color: 'var(--brand-primary)'
                  }}
                >
                  {passage.section}
                </span>
              )}
              {typeof passage.word_count === 'number' && passage.word_count > 0 && (
                <span
                  style={{
                    fontSize: '0.68rem',
                    color: 'var(--text-muted)',
                    padding: '2px 6px',
                    borderRadius: 'var(--radius-xs, 4px)',
                    backgroundColor: 'var(--bg-surface-elevated)',
                    border: '1px solid var(--border-light)'
                  }}
                >
                  {passage.word_count} words
                </span>
              )}
            </div>
          </div>

          {passage.text && (
            <p
              style={{
                margin: 0,
                fontSize: '0.78rem',
                fontFamily: 'var(--font-serif, serif)',
                fontStyle: 'italic',
                color: 'var(--text-secondary)',
                lineHeight: 1.45,
                display: '-webkit-box',
                WebkitLineClamp: 2,
                WebkitBoxOrient: 'vertical',
                overflow: 'hidden'
              }}
            >
              "{passage.text.slice(0, 160).trim()}..."
            </p>
          )}

          <div style={{ fontSize: '0.68rem', color: 'var(--text-dim)', fontFamily: 'var(--font-mono)' }}>
            ID: {passage.id}
          </div>
        </div>

        {/* Cascade Warning Callout */}
        <div
          id="delete-passage-desc"
          style={{
            padding: '12px 14px',
            borderRadius: 'var(--radius-md, 12px)',
            backgroundColor: 'var(--status-danger-bg, rgba(244, 63, 94, 0.08))',
            border: '1px solid var(--status-danger-border, rgba(244, 63, 94, 0.22))',
            display: 'flex',
            flexDirection: 'column',
            gap: '6px'
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: 'var(--status-danger, #f43f5e)' }}>
            <Layers size={16} />
            <strong style={{ fontSize: '0.85rem' }}>
              {questionCount > 0
                ? `Linked Questions Will Be Deleted (${questionCount} Question${questionCount === 1 ? '' : 's'})`
                : 'Delete Confirmation'}
            </strong>
          </div>

          <p
            style={{
              margin: 0,
              fontSize: '0.8rem',
              lineHeight: 1.5,
              color: 'var(--text-secondary)'
            }}
          >
            {questionCount > 0 ? (
              <>
                Deleting this passage will <strong>remove it from the Passage Bank and remove its {questionCount} associated question{questionCount === 1 ? '' : 's'}</strong> from your Question Bank and Review queue. Don't worry — your questions and generation records will <strong>remain safely preserved in your Batch Progress</strong> history.
              </>
            ) : (
              <>
                Deleting this passage will remove it from the Passage Bank. It will remain preserved in your Batch Progress history.
              </>
            )}
          </p>

          <span
            style={{
              fontSize: '0.72rem',
              fontWeight: 600,
              color: 'var(--text-muted)',
              marginTop: '2px'
            }}
          >
            You can view and restore deleted questions anytime from the Batch Progress tab.
          </span>
        </div>

        {/* Error Message if deletion failed */}
        {errorMessage && (
          <div
            style={{
              padding: '10px 12px',
              borderRadius: 'var(--radius-sm, 8px)',
              backgroundColor: 'var(--status-danger-bg, rgba(244, 63, 94, 0.15))',
              border: '1px solid var(--status-danger-border, #f43f5e)',
              color: 'var(--status-danger, #f43f5e)',
              fontSize: '0.8rem'
            }}
          >
            {errorMessage}
          </div>
        )}
      </div>
    </Modal>
  );
}
