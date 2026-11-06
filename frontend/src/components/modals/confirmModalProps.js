/**
 * The props every view passes to ConfirmationModal from a useConfirmModal() state object.
 * Spread it: `<ConfirmationModal {...confirmModalProps(confirmModal, closeConfirmModal, busy)} />`.
 */
export function confirmModalProps(confirmModal, onClose, isProcessing = false) {
  return {
    isOpen: confirmModal.isOpen,
    onClose,
    onConfirm: confirmModal.onConfirm,
    title: confirmModal.title,
    description: confirmModal.description,
    confirmLabel: confirmModal.confirmLabel,
    variant: confirmModal.variant,
    itemCount: confirmModal.itemCount,
    itemLabel: confirmModal.itemLabel,
    isProcessing
  };
}
