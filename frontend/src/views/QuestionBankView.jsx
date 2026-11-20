import { useState, useRef, useCallback } from 'react';
import { Database, Sparkles, Eye } from 'lucide-react';
import { batchDeleteQuestions, saveEditedQuestion } from '../services';
import {
  useQuestionBank,
  usePagination,
  useConfirmModal,
  useKeyboardShortcuts,
  useBankDeletion,
  useDuplicateOverride
} from '../hooks';
import { PaginationBar, Modal, LoadError, EmptyState } from '../components/common';
import { QuestionCard } from '../components/question';
import { ExportPrintModal, ConfirmationModal } from '../components/modals';
import { QuestionBankFilters, QuestionBankTable } from '../components/bank';
import { DuplicateCompareModal } from '../components/duplicates';
import { toggleId } from '../utils';
import { confirmModalProps } from '../components/modals/confirmModalProps';

/**
 * QuestionBankView - Primary view for browsing, searching, and managing questions in the bank.
 *
 * Provides multi-facet filtering (section, difficulty, search query), pagination,
 * bulk operations (delete, export, status transitions), and detailed modal audit inspects.
 *
 * @param {Object} props
 * @param {(toast: { type?: string, title: string, message?: string }) => void} props.onShowToast - Toast trigger callback.
 * @param {(step?: number) => void} props.onNavigateToWizard - Navigation callback to wizard view.
 * @returns {JSX.Element}
 */
export default function QuestionBankView({ onShowToast, onNavigateToWizard }) {
  const {
    questions,
    rawQuestions,
    loading,
    loadError,
    sectionFilter,
    setSectionFilter,
    diffFilter,
    setDiffFilter,
    searchQuery,
    setSearchQuery,
    searchMode,
    setSearchMode,
    isSearchingSemantic,
    sortBy,
    setSortBy,
    setPage,
    pageSize,
    setPageSize,
    totalCount,
    bankTotalCount,
    copiedId,
    loadQuestions,
    handleDelete,
    handleCopy,
    handleUpdate,
    avgScore
  } = useQuestionBank();

  const searchInputRef = useRef(null);
  const [expandedId, setExpandedId] = useState(null);
  const [selectedIds, setSelectedIds] = useState([]);
  const [showExportModal, setShowExportModal] = useState(false);
  const [inspectingQuestion, setInspectingQuestion] = useState(null);

  // Standardized accessible confirmation modal state hook
  const { confirmModal, openConfirmModal, closeConfirmModal } = useConfirmModal('question');

  const handleUpdateInspectedQuestion = useCallback(
    async (updated) => {
      try {
        await saveEditedQuestion(updated);
        setInspectingQuestion(updated);
        handleUpdate?.(updated);
        onShowToast?.({
          type: 'success',
          title: 'Changes Applied',
          message: 'Question updated in Question Bank.'
        });
      } catch (err) {
        console.error('Failed to update question in bank:', err);
        onShowToast?.({
          type: 'error',
          title: 'Update Failed',
          message: 'Could not save question updates to database.'
        });
        throw err;
      }
    },
    [handleUpdate, onShowToast]
  );

  // Duplicate compare dialog and "Override and approve" (the inspector shows the alert bar)
  const handleDuplicateOverridden = useCallback(
    (saved) => {
      handleUpdate?.(saved);
      setInspectingQuestion((prev) => (prev && prev.id === saved.id ? { ...prev, ...saved } : prev));
    },
    [handleUpdate]
  );
  const {
    compareQuestion,
    isOverriding,
    openCompare,
    closeCompare,
    handleOverride
  } = useDuplicateOverride({ onShowToast, onUpdated: handleDuplicateOverridden });

  // Reset selection when search or filters change
  const hasActiveFilters = Boolean(searchQuery.trim() || sectionFilter || diffFilter);

  // ─── Server-Driven Pagination ───────────────────────────────────────────────
  const {
    setCurrentPage,
    totalPages,
    safeCurrentPage,
    paginatedItems: paginatedQuestions
  } = usePagination({
    items: questions,
    initialPageSize: pageSize,
    totalCount: totalCount,
    onPageChange: setPage,
    onPageSizeChange: setPageSize,
    resetDeps: [searchQuery, sectionFilter, diffFilter, sortBy]
  });

  const handleClearAllFilters = useCallback(() => {
    setSearchQuery('');
    setSectionFilter('');
    setDiffFilter('');
  }, [setSearchQuery, setSectionFilter, setDiffFilter]);

  // Focus search on '/'
  useKeyboardShortcuts({
    onFocusSearch: () => searchInputRef.current?.focus()
  });

  // ─── Selection Handlers (Persistent Cross-Page Selection) ───────────────────
  const handleToggleSelect = useCallback((id, e) => {
    if (e) e.stopPropagation();
    setSelectedIds((prev) => toggleId(prev, id));
  }, []);

  const handleSelectAll = useCallback(() => {
    const currentIds = paginatedQuestions.map((q) => q.id);
    const allSelectedOnPage = currentIds.length > 0 && currentIds.every((id) => selectedIds.includes(id));
    if (allSelectedOnPage) {
      const set = new Set(currentIds);
      setSelectedIds((prev) => prev.filter((id) => !set.has(id)));
    } else {
      const set = new Set(selectedIds);
      currentIds.forEach((id) => set.add(id));
      setSelectedIds(Array.from(set));
    }
  }, [paginatedQuestions, selectedIds]);

  const handleClearSelection = useCallback(() => {
    setSelectedIds([]);
  }, []);

  const { isDeleting: isDeletingBulk, confirmDeletion } = useBankDeletion({
    openConfirmModal,
    closeConfirmModal,
    onShowToast
  });

  const handleConfirmSingleDelete = useCallback((id, e) => {
    if (e) e.stopPropagation();
    confirmDeletion({
      count: 1,
      action: () => handleDelete(id),
      successMessage: 'Successfully removed question from the Question Bank.'
    });
  }, [confirmDeletion, handleDelete]);

  const handleBulkDelete = useCallback(() => {
    if (selectedIds.length === 0) return;
    const ids = [...selectedIds];
    confirmDeletion({
      count: ids.length,
      action: async () => {
        await batchDeleteQuestions(ids);
        setSelectedIds([]);
        loadQuestions();
      },
      successMessage: `Successfully removed ${ids.length} question(s) from the Question Bank.`
    });
  }, [selectedIds, confirmDeletion, loadQuestions]);

  const handleOpenExportModal = useCallback(() => setShowExportModal(true), []);
  const handleCloseExportModal = useCallback(() => setShowExportModal(false), []);
  const handleCloseInspection = useCallback(() => setInspectingQuestion(null), []);
  const handleCreateFirstQuestions = useCallback(() => onNavigateToWizard?.(1), [onNavigateToWizard]);

  const displayTotalCount = totalCount || questions.length;

  return (
    <div className="question-bank-container">
      {/* ── Header & Stats Strip ─────────────────────────────────────────── */}
      <div className="view-header-strip">
        <div>
          <h2 className="view-header-title">
            Question Bank
          </h2>
        </div>

        <div className="view-header-actions">
          <div className="view-header-badge">
            <span><strong className="qbank-header-stat-num">{displayTotalCount}</strong> {displayTotalCount === 1 ? 'question' : 'questions'}</span>
            <span className="view-header-divider">•</span>
            <span>
              <strong className="qbank-header-avg-num">{avgScore}</strong>
              <span className="qbank-header-avg-unit">/100 avg</span>
            </span>
          </div>

          <button
            type="button"
            id="btn-open-export-studio"
            onClick={handleOpenExportModal}
            className="btn-secondary qbank-export-trigger-btn"
            disabled={displayTotalCount === 0}
            title={displayTotalCount > 0 ? 'Export & Print' : 'No questions to export'}
          >
            <span>Export &amp; Print</span>
          </button>
        </div>
      </div>

      {/* ── Filters / Search / Bulk Bar ──────────────────────────────────── */}
      <QuestionBankFilters
        searchQuery={searchQuery}
        setSearchQuery={setSearchQuery}
        searchMode={searchMode}
        setSearchMode={setSearchMode}
        isSearchingSemantic={isSearchingSemantic}
        searchInputRef={searchInputRef}
        sectionFilter={sectionFilter}
        setSectionFilter={setSectionFilter}
        diffFilter={diffFilter}
        setDiffFilter={setDiffFilter}
        sortBy={sortBy}
        setSortBy={setSortBy}
        questions={questions}
        selectedIds={selectedIds}
        isDeletingBulk={isDeletingBulk}
        hasActiveFilters={hasActiveFilters}
        onSelectAll={handleSelectAll}
        onClearSelection={handleClearSelection}
        onBulkDelete={handleBulkDelete}
        onClearAllFilters={handleClearAllFilters}
        onNavigateToWizard={onNavigateToWizard}
        onOpenExportModal={handleOpenExportModal}
      />

      {/* ── Question List ─────────────────────────────────────────────────── */}
      {loading ? (
        <div className="view-loading-box">
          <div className="view-loading-spinner" />
          <span className="view-loading-text">Loading Question Bank...</span>
        </div>
      ) : loadError && questions.length === 0 ? (
        <LoadError
          title="Could not load the Question Bank"
          message={loadError}
          onRetry={loadQuestions}
        />
      ) : questions.length === 0 ? (
        <EmptyState
          icon={<Database size={28} />}
          title="No Questions Found"
          description={
            hasActiveFilters
              ? 'No questions match your current search or filters. Clear your filters to see more, or create questions.'
              : 'Your Question Bank is currently empty. Create your first questions to get started!'
          }
        >
          {!hasActiveFilters && onNavigateToWizard && (
            <button
              type="button"
              id="btn-bank-empty-create"
              onClick={handleCreateFirstQuestions}
              className="btn-primary"
            >
              <Sparkles size={14} />
              <span>Create New Questions</span>
            </button>
          )}
        </EmptyState>
      ) : (
        <QuestionBankTable
          paginatedQuestions={paginatedQuestions}
          selectedIds={selectedIds}
          expandedId={expandedId}
          setExpandedId={setExpandedId}
          copiedId={copiedId}
          onToggleSelect={handleToggleSelect}
          onCopy={handleCopy}
          onDelete={handleConfirmSingleDelete}
          onSelectQuestion={setInspectingQuestion}
          onCompareDuplicate={openCompare}
        />
      )}

      {/* ── Pagination Bar ────────────────────────────────────────────────── */}
      {!loading && displayTotalCount > 0 && (
        <PaginationBar
          currentPage={safeCurrentPage}
          totalPages={totalPages}
          pageSize={pageSize}
          totalItems={displayTotalCount}
          itemLabel="questions"
          onPageChange={setCurrentPage}
          onPageSizeChange={setPageSize}
        />
      )}

      {/* ── Export Modal ──────────────────────────────────────────────────── */}
      {showExportModal && (
        <ExportPrintModal
          isOpen={showExportModal}
          onClose={handleCloseExportModal}
          allQuestions={rawQuestions}
          selectedIds={selectedIds}
          filteredQuestions={questions}
          hasActiveFilters={hasActiveFilters}
          bankTotalCount={bankTotalCount || totalCount}
          onShowToast={onShowToast}
        />
      )}

      {/* ── In-Place Question Inspection & Edit Dialog (WCAG AA Focus Trapped) ── */}
      <Modal
        isOpen={Boolean(inspectingQuestion)}
        onClose={handleCloseInspection}
        title="Question Inspector & Editorial Desk"
        icon={<Eye size={18} color="var(--brand-primary)" />}
        maxWidth="960px"
        cardStyle={{
          maxHeight: '90vh',
          background: 'var(--bg-canvas)'
        }}
      >
        {inspectingQuestion && (
          <QuestionCard
            question={inspectingQuestion}
            isSaved={true}
            onUpdateQuestion={handleUpdateInspectedQuestion}
            onShowToast={onShowToast}
            onCompareDuplicate={openCompare}
            onOverrideDuplicate={handleOverride}
            isOverridingDuplicate={isOverriding}
          />
        )}
      </Modal>

      <DuplicateCompareModal
        question={compareQuestion}
        onClose={closeCompare}
        onOverride={handleOverride}
        isOverriding={isOverriding}
      />

      {/* ── Reusable Accessible Confirmation Modal ──────────────────────── */}
      <ConfirmationModal {...confirmModalProps(confirmModal, closeConfirmModal, isDeletingBulk)} />
    </div>
  );
}
