import { useState, useCallback } from 'react';

const DEFAULT_STATE = {
  isOpen: false,
  title: '',
  description: '',
  confirmLabel: 'Confirm',
  variant: 'danger',
  itemCount: null,
  itemLabel: 'item',
  onConfirm: null,
};

/**
 * useConfirmModal – Shared state manager for the ConfirmationModal primitive.
 * @param {string} itemLabelDefault - Default singular noun for target items (e.g. 'question', 'batch').
 * @returns {{
 *   confirmModal: typeof DEFAULT_STATE,
 *   openConfirmModal: (opts: Partial<typeof DEFAULT_STATE>) => void,
 *   closeConfirmModal: () => void
 * }}
 */
export function useConfirmModal(itemLabelDefault = 'item') {
  const [confirmModal, setConfirmModal] = useState({
    ...DEFAULT_STATE,
    itemLabel: itemLabelDefault,
  });

  const openConfirmModal = useCallback((opts = {}) => {
    setConfirmModal({
      ...DEFAULT_STATE,
      itemLabel: itemLabelDefault,
      isOpen: true,
      ...opts,
    });
  }, [itemLabelDefault]);

  const closeConfirmModal = useCallback(() => {
    setConfirmModal((prev) => ({ ...prev, isOpen: false }));
  }, []);

  return { confirmModal, openConfirmModal, closeConfirmModal };
}

