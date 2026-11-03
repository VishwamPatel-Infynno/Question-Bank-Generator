import { useState, useRef, useCallback } from 'react';
import { Database, Sparkles, Eye } from 'lucide-react';
import { batchDeleteQuestions, approveQuestion } from '../services/api';
import { useQuestionBank, usePagination, useConfirmModal, useKeyboardShortcuts } from '../hooks';
import { PaginationBar, Modal } from '../components/common';
import { QuestionCard } from '../components/question';
import { ExportPrintModal, ConfirmationModal } from '../components/modals';
import QuestionBankFilters from '../components/bank/QuestionBankFilters';
import QuestionBankTable from '../components/bank/QuestionBankTable';


export default function QuestionBankView({ onShowToast, onNavigateToWizard }) {
  const {
    questions,
    loading,
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
  const [selectedIds, setSelectedIds] = useState([]);
  const [isDeletingBulk, setIsDeletingBulk] = useState(false);
  const [showExportModal, setShowExportModal] = useState(false);
  const [inspectingQuestion, setInspectingQuestion] = useState(null);

  // Standardized accessible confirmation modal state hook
  const { confirmModal, openConfirmModal, closeConfirmModal } = useConfirmModal('question');

  const handleUpdateInspectedQuestion = async (updated) => {
    try {
      await approveQuestion(updated);
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
    }
  };

  const hasActiveFilters = Boolean(searchQuery.trim() || sectionFilter || diffFilter);

  // ─── Pagination ────────────────────────────────────────────────────────────
  const {
    currentPage,
    setCurrentPage,
    pageSize,
    setPageSize,
    totalPages,
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

  const handleSearchChange = (val) => setSearchQuery(val);
  const handleSectionChange = (val) => setSectionFilter(val);
  const handleDiffChange = (val) => setDiffFilter(val);
  const handleSortChange = (val) => setSortBy(val);

  // Focus search on '/'
  useKeyboardShortcuts({
    onFocusSearch: () => searchInputRef.current?.focus()
  });

  // ─── Selection Handlers ────────────────────────────────────────────────────
  const handleToggleSelect = useCallback((id, e) => {
    e.stopPropagation();
    setSelectedIds(prev => prev.includes(id) ? prev.filter(x => x !== id) : [...prev, id]);
  }, []);

  const handleSelectAll = () => {
    const currentIds = paginatedQuestions.map(q => q.id);
    const allCurrentSelected = currentIds.length > 0 && currentIds.every(id => selectedIds.includes(id));
    if (allCurrentSelected) {
      setSelectedIds(prev => prev.filter(id => !currentIds.includes(id)));
    } else {
      setSelectedIds(prev => Array.from(new Set([...prev, ...currentIds])));
    }
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
            <span><strong style={{ color: 'var(--text-primary)', fontWeight: 600 }}>{questions.length}</strong> {questions.length === 1 ? 'question' : 'questions'}</span>
            <span className="view-header-divider">•</span>
            <span>
              <strong style={{ color: 'var(--status-success)', fontWeight: 600 }}>{avgScore}</strong>
              <span style={{ color: 'var(--text-muted)', fontSize: '0.72rem' }}>/100 avg</span>
            </span>
          </div>

          <button
            type="button"
            id="btn-open-export-studio"
            onClick={() => setShowExportModal(true)}
            className="btn-secondary"
            style={{
              padding: '6px 12px',
              fontSize: '0.78rem',
              gap: '6px',
              opacity: questions.length === 0 ? 0.5 : 1,
              cursor: questions.length === 0 ? 'not-allowed' : 'pointer'
            }}
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
        setSearchQuery={handleSearchChange}
        searchInputRef={searchInputRef}
        sectionFilter={sectionFilter}
        setSectionFilter={handleSectionChange}
        diffFilter={diffFilter}
        setDiffFilter={handleDiffChange}
        sortBy={sortBy}
        setSortBy={handleSortChange}
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
      ) : questions.length === 0 ? (
        <div className="view-empty-state">
          <div className="view-empty-icon-box">
            <Database size={28} />
          </div>
          <div>
            <h3 className="view-empty-title">No Questions Found</h3>
            <p className="view-empty-desc">
              {hasActiveFilters
                ? 'No questions match your current search or filters. Clear your filters to see more, or create questions.'
                : 'Your Question Bank is currently empty. Create your first practice set to get started!'}
            </p>
          </div>
          {!hasActiveFilters && onNavigateToWizard && (
            <div className="view-empty-actions">
              <button
                type="button"
                id="btn-bank-empty-create"
                onClick={onNavigateToWizard}
                className="btn-primary"
                style={{ padding: '8px 18px', fontSize: '0.825rem', display: 'inline-flex', alignItems: 'center', gap: '6px' }}
              >
                <Sparkles size={14} />
                <span>Create New Questions</span>
              </button>
            </div>
          )}
        </div>
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
          currentPage={currentPage}
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
      <ConfirmationModal
        isOpen={confirmModal.isOpen}
        onClose={closeConfirmModal}
        onConfirm={confirmModal.onConfirm}
        title={confirmModal.title}
        description={confirmModal.description}
        confirmLabel={confirmModal.confirmLabel}
        variant={confirmModal.variant}
        itemCount={confirmModal.itemCount}
        itemLabel={confirmModal.itemLabel}
        isProcessing={isDeletingBulk}
      />
    </div>
  );
}
