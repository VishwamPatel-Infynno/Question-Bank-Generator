import { useState } from 'react';

/**
 * The Question Bank's two delete flows (one question, the selection) behind one confirm dialog:
 * same toasts, same busy flag, different action and wording.
 *
 * @param {Object} options
 * @param {(opts: object) => void} options.openConfirmModal - Confirmation modal trigger.
 * @param {() => void} options.closeConfirmModal - Confirmation modal closer.
 * @param {(toast: { type?: string, title: string, message?: string }) => void} [options.onShowToast] - Toast notification dispatcher.
 * @returns {{
 *   isDeleting: boolean,
 *   confirmDeletion: (args: { count: number, action: () => Promise<any>, successMessage: string }) => void
 * }} Bank deletion status and trigger method.
 */
export function useBankDeletion({ openConfirmModal, closeConfirmModal, onShowToast }) {
  const [isDeleting, setIsDeleting] = useState(false);

  const confirmDeletion = ({ count, action, successMessage }) => {
    const plural = count !== 1 ? 's' : '';
    openConfirmModal({
      title: count === 1 ? 'Delete Question' : 'Delete Selected Questions',
      description: `Are you sure you want to remove ${count === 1 ? 'this question' : `${count} selected question${plural}`} from the Question Bank? ${count === 1 ? 'It' : 'They'} will remain safely preserved and viewable in Batch Progress history.`,
      confirmLabel: count === 1 ? 'Delete Question' : `Delete ${count} Question${plural}`,
      variant: 'danger',
      itemCount: count,
      itemLabel: 'question',
      onConfirm: async () => {
        setIsDeleting(true);
        try {
          await action();
          onShowToast?.({
            type: 'success',
            title: count === 1 ? 'Question Deleted' : 'Questions Deleted',
            message: successMessage
          });
          closeConfirmModal();
        } catch (err) {
          console.error('Failed to delete question(s):', err);
          onShowToast?.({
            type: 'error',
            title: 'Deletion Failed',
            message: err.message || 'Could not delete the question(s).'
          });
        } finally {
          setIsDeleting(false);
        }
      }
    });
  };

  return { isDeleting, confirmDeletion };
}
