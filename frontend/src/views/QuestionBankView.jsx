import { useState, useRef, useCallback, useMemo } from 'react';
import { Database, Sparkles, Eye } from 'lucide-react';
import { batchDeleteQuestions, saveEditedQuestion } from '../services/api';
import { useQuestionBank, usePagination, useConfirmModal, useKeyboardShortcuts } from '../hooks';
import { PaginationBar, Modal, LoadError, EmptyState } from '../components/common';
import { QuestionCard } from '../components/question';
import { ExportPrintModal, ConfirmationModal } from '../components/modals';
import QuestionBankFilters from '../components/bank/QuestionBankFilters';
import QuestionBankTable from '../components/bank/QuestionBankTable';
import { toggleAll, toggleId } from '../utils';
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
    loading,
    loadError,
    sectionFilter,
    setSectionFilter,
    diffFilter,
    setDiffFilter,
    searchQuery,
    setSearchQuery,
    sortBy,
    setSortBy,
    copiedId,
    loadQuestions,
    handleDelete,
    handleCopy,
    handleUpdate,
    avgScore
  } = useQuestionBank();

  const searchInputRef = useRef(null);
  const [expandedId, setExpandedId] = useState(null);
  const [selectedRaw, setSelectedIds] = useState([]);
  const [isDeletingBulk, setIsDeletingBulk] = useState(false);
  const [showExportModal, setShowExportModal] = useState(false);
  const [inspectingQuestion, setInspectingQuestion] = useState(null);

  // Standardized accessible confirmation modal state hook
  const { confirmModal, openConfirmModal, closeConfirmModal } = useConfirmModal('question');

  // Selection only counts items still in the loaded list: after a filter change or reload, ids
  // the user can no longer see must not be bulk-deleted or exported.
  const selectedIds = useMemo(() => {
    const loaded = new Set(questions.map((q) => q.id));
    return selectedRaw.filter((id) => loaded.has(id));
  }, [selectedRaw, questions]);

  const handleUpdateInspectedQuestion = async (updated) => {
    try {
      await saveEditedQuestion(updated);
      setInspectingQuestion(updated);
      if (handleUpdate) handleUpdate(updated);
      if (onShowToast) {
        onShowToast({
          type: 'success',
          title: 'Changes Applied',
          message: 'Question updated in Question Bank.'
        });
      }
    } catch (err) {
      console.error('Failed to update question in bank:', err);
      if (onShowToast) {
        onShowToast({
          type: 'error',
          title: 'Update Failed',
          message: 'Could not save question updates to database.'
        });
      }
      throw err; // lets the editor stay open with the user's changes
    }
  };

  const hasActiveFilters = Boolean(searchQuery.trim() || sectionFilter || diffFilter);

  // ─── Pagination ────────────────────────────────────────────────────────────
  const {
    setCurrentPage,
    pageSize,
    setPageSize,
    totalPages,
    safeCurrentPage,
    paginatedItems: paginatedQuestions
  } = usePagination({
    items: questions,
    initialPageSize: 15,
    resetDeps: [searchQuery, sectionFilter, diffFilter, sortBy]
  });

  const handleClearAllFilters = () => {
    setSearchQuery('');
    setSectionFilter('');
    setDiffFilter('');
  };

  // Focus search on '/'
  useKeyboardShortcuts({
    onFocusSearch: () => searchInputRef.current?.focus()
  });

  // ─── Selection Handlers ────────────────────────────────────────────────────
  const handleToggleSelect = useCallback((id, e) => {
    e.stopPropagation();
    setSelectedIds((prev) => toggleId(prev, id));
  }, []);

  const handleSelectAll = () => {
    const currentIds = paginatedQuestions.map((q) => q.id);
    setSelectedIds((prev) => toggleAll(prev, currentIds));
  };

  // ─── Single Item Delete via Confirmation Modal ────────────────────────────
  const handleConfirmSingleDelete = (id, e) => {
    if (e) e.stopPropagation();
    openConfirmModal({
      title: 'Delete Question',
      description: 'Are you sure you want to remove this question from your Question Bank? It will remain safely preserved and viewable in Batch Progress history.',
      confirmLabel: 'Delete Question',
      variant: 'danger',
      itemCount: 1,
      itemLabel: 'question',
      onConfirm: async () => {
        setIsDeletingBulk(true);
        try {
          await handleDelete(id);
          if (onShowToast) {
            onShowToast({
              type: 'success',
              title: 'Question Deleted',
              message: 'Successfully removed question from the Question Bank.'
            });
          }
          closeConfirmModal();
        } catch (err) {
          console.error('Failed to delete question:', err);
          if (onShowToast) {
            onShowToast({ type: 'error', title: 'Deletion Failed', message: err.message || 'Could not delete question.' });
          }
        } finally {
          setIsDeletingBulk(false);
        }
      }
    });
  };

  // ─── Bulk Delete via Confirmation Modal ───────────────────────────────────
  const handleBulkDelete = () => {
    if (selectedIds.length === 0) return;
    const countToDelete = selectedIds.length;
    openConfirmModal({
      title: 'Delete Selected Questions',
      description: `Are you sure you want to remove ${countToDelete} selected question${countToDelete !== 1 ? 's' : ''} from the Question Bank? They will remain safely preserved and viewable in Batch Progress history.`,
      confirmLabel: `Delete ${countToDelete} Question${countToDelete !== 1 ? 's' : ''}`,
      variant: 'danger',
      itemCount: countToDelete,
      itemLabel: 'question',
      onConfirm: async () => {
        setIsDeletingBulk(true);
        try {
          await batchDeleteQuestions(selectedIds);
          setSelectedIds([]);
          await loadQuestions();
          if (onShowToast) {
            onShowToast({
              type: 'success',
              title: 'Questions Deleted',
              message: `Successfully removed ${countToDelete} question(s) from the Question Bank.`
            });
          }
          closeConfirmModal();
        } catch (err) {
          console.error('Failed to bulk delete questions:', err);
          if (onShowToast) {
            onShowToast({ type: 'error', title: 'Deletion Failed', message: err.message || 'Could not delete selected questions.' });
          }
        } finally {
          setIsDeletingBulk(false);
        }
      }
    });
  };

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
            <span><strong className="qbank-header-stat-num">{questions.length}</strong> {questions.length === 1 ? 'question' : 'questions'}</span>
            <span className="view-header-divider">•</span>
            <span>
              <strong className="qbank-header-avg-num">{avgScore}</strong>
              <span className="qbank-header-avg-unit">/100 avg</span>
            </span>
          </div>

          <button
            type="button"
            id="btn-open-export-studio"
            onClick={() => setShowExportModal(true)}
            className="btn-secondary qbank-export-trigger-btn"
            disabled={questions.length === 0}
            title={questions.length > 0 ? 'Export & Print' : 'No questions to export'}
          >
            <span>Export &amp; Print</span>
          </button>
        </div>
      </div>

      {/* ── Filters / Search / Bulk Bar ──────────────────────────────────── */}
      <QuestionBankFilters
        searchQuery={searchQuery}
        setSearchQuery={setSearchQuery}
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
        onBulkDelete={handleBulkDelete}
        onClearAllFilters={handleClearAllFilters}
        onNavigateToWizard={onNavigateToWizard}
        onOpenExportModal={() => setShowExportModal(true)}
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
              : 'Your Question Bank is currently empty. Create your first practice set to get started!'
          }
        >
          {!hasActiveFilters && onNavigateToWizard && (
            <button
              type="button"
              id="btn-bank-empty-create"
              onClick={onNavigateToWizard}
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
        />
      )}

      {/* ── Pagination Bar ────────────────────────────────────────────────── */}
      {!loading && questions.length > 0 && (
        <PaginationBar
          currentPage={safeCurrentPage}
          totalPages={totalPages}
          pageSize={pageSize}
          totalItems={questions.length}
          itemLabel="questions"
          onPageChange={setCurrentPage}
          onPageSizeChange={setPageSize}
          pageSizeOptions={[
            { value: 10, label: '10' },
            { value: 15, label: '15' },
            { value: 25, label: '25' },
            { value: 50, label: '50' },
            { value: -1, label: 'All' }
          ]}
        />
      )}

      {/* ── Export Modal ──────────────────────────────────────────────────── */}
      {showExportModal && (
        <ExportPrintModal
          isOpen={showExportModal}
          onClose={() => setShowExportModal(false)}
          allQuestions={questions}
          selectedIds={selectedIds}
          filteredQuestions={questions}
          hasActiveFilters={hasActiveFilters}
          onShowToast={onShowToast}
        />
      )}

      {/* ── In-Place Question Inspection & Edit Dialog (WCAG AA Focus Trapped) ── */}
      <Modal
        isOpen={Boolean(inspectingQuestion)}
        onClose={() => setInspectingQuestion(null)}
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
          />
        )}
      </Modal>

      {/* ── Reusable Accessible Confirmation Modal ──────────────────────── */}
      <ConfirmationModal {...confirmModalProps(confirmModal, closeConfirmModal, isDeletingBulk)} />
    </div>
  );
}
