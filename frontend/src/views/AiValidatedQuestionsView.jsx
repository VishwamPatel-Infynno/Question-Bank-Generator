import { CheckCircle2, ArrowRight } from 'lucide-react';
import { PaginationBar } from '../components/common';
import { ConfirmationModal } from '../components/modals';
import { usePagination, useAiValidated } from '../hooks';
import {
  AiValidatedStatsBar,
  AiValidatedFiltersBar,
  AiValidatedQuestionCard
} from '../components/validated';

/**
 * AiValidatedQuestionsView
 *
 * Dedicated view for inspecting questions that met or exceeded the 90/100
 * quality benchmark, allowing pre-med authors to audit psychometric rationale,
 * edit inline, and approve questions into the permanent Question Bank.
 *
 * @param {Object} props
 * @param {(question: Object) => void} props.onOpenAudit - Callback to open psychometric audit modal.
 * @param {() => void} props.onNavigateToBank - Callback to navigate to Question Bank view.
 * @param {() => void} props.onNavigateToBatches - Callback to navigate to Batch Activity view.
 * @param {(step?: number) => void} props.onNavigateToWizard - Callback to navigate to generation wizard.
 * @param {(toast: Object) => void} props.onShowToast - Callback to trigger toast notifications.
 * @param {() => void} props.onRefreshCounts - Global counts refresh callback.
 * @returns {JSX.Element}
 */
export default function AiValidatedQuestionsView({
  onOpenAudit,
  onNavigateToBank,
  onNavigateToBatches,
  onNavigateToWizard,
  onShowToast,
  onRefreshCounts
}) {
  const {
    questions,
    filteredQuestions,
    counts,
    loading,
    refreshing,
    actionInProgress,
    loadData,
    searchQuery,
    setSearchQuery,
    debouncedSearch,
    sectionFilter,
    setSectionFilter,
    searchInputRef,
    selectedIds,
    allFilteredSelected,
    handleToggleSelect,
    handleSelectAll,
    expandedPassageIds,
    togglePassage,
    handleMoveToBankSingle,
    handleDiscardSingle,
    handleBulkMoveToBank,
    handleBulkDiscard,
    handleApproveAllValidated,
    confirmModal,
    closeConfirmModal
  } = useAiValidated({ onShowToast, onNavigateToBank, onRefreshCounts });

  // ─── Pagination ────────────────────────────────────────────────────────────
  const {
    currentPage,
    setCurrentPage,
    pageSize,
    setPageSize,
    totalPages,
    safeCurrentPage,
    paginatedItems: paginatedQuestions
  } = usePagination({
    items: filteredQuestions,
    initialPageSize: 15,
    resetDeps: [debouncedSearch, sectionFilter]
  });

  return (
    <div className="validated-questions-stack">
      {/* Header and Metrics */}
      <AiValidatedStatsBar
        counts={counts}
        questionsCount={questions.length}
        refreshing={refreshing}
        onRefresh={() => loadData(false)}
        onNavigateToBank={onNavigateToBank}
      />

      {/* Filter and Bulk Action Toolbar */}
      <AiValidatedFiltersBar
        searchQuery={searchQuery}
        onSearchChange={setSearchQuery}
        searchInputRef={searchInputRef}
        sectionFilter={sectionFilter}
        onSectionFilterChange={setSectionFilter}
        totalFiltered={filteredQuestions.length}
        allFilteredSelected={allFilteredSelected}
        onSelectAll={handleSelectAll}
        selectedCount={selectedIds.length}
        actionInProgress={actionInProgress}
        onBulkMoveToBank={handleBulkMoveToBank}
        onBulkDiscard={handleBulkDiscard}
        onApproveAllValidated={handleApproveAllValidated}
      />

      {/* Main Content Area */}
      {loading ? (
        <div className="view-loading-box">
          <div className="view-loading-spinner" />
          <span className="view-loading-text">Loading validated questions...</span>
        </div>
      ) : filteredQuestions.length === 0 ? (
        <div className="empty-state-card" style={{ padding: '60px 20px', textAlign: 'center' }}>
          <div
            style={{
              width: '56px',
              height: '56px',
              borderRadius: '50%',
              background: 'rgba(16, 185, 129, 0.08)',
              color: 'var(--status-success)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              margin: '0 auto 16px'
            }}
          >
            <CheckCircle2 size={28} />
          </div>
          <h3 style={{ fontSize: '1.15rem', fontWeight: 800, color: 'var(--text-primary)', marginBottom: '8px' }}>
            No Questions Awaiting Review
          </h3>
          <p style={{ fontSize: '0.875rem', color: 'var(--text-secondary)', maxWidth: '460px', margin: '0 auto 24px', lineHeight: 1.5 }}>
            {debouncedSearch || sectionFilter
              ? 'No questions matched your current search filters.'
              : 'All generated questions have been reviewed and moved to the Question Bank. Start a new generation run to create more.'}
          </p>
          <div style={{ display: 'flex', gap: '12px', justifyContent: 'center' }}>
            {onNavigateToBatches && (
              <button
                type="button"
                onClick={onNavigateToBatches}
                className="btn-secondary"
                style={{ padding: '8px 18px' }}
              >
                View Batch Activity
              </button>
            )}
            {onNavigateToWizard && (
              <button
                type="button"
                onClick={() => onNavigateToWizard(1)}
                className="btn-primary"
                style={{ padding: '8px 18px', display: 'inline-flex', alignItems: 'center', gap: '8px' }}
              >
                <span>Generate Questions</span>
                <ArrowRight size={15} />
              </button>
            )}
          </div>
        </div>
      ) : (
        <>
          <div className="ai-validated-list" style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
            {paginatedQuestions.map((question) => (
              <AiValidatedQuestionCard
                key={question.id}
                question={question}
                isSelected={selectedIds.includes(question.id)}
                isPassageExpanded={Boolean(expandedPassageIds[question.passage_id])}
                actionInProgress={actionInProgress}
                onToggleSelect={handleToggleSelect}
                onTogglePassage={togglePassage}
                onMoveToBank={handleMoveToBankSingle}
                onDiscard={handleDiscardSingle}
                onOpenAudit={onOpenAudit}
              />
            ))}
          </div>

          <PaginationBar
            currentPage={safeCurrentPage || currentPage}
            totalPages={totalPages}
            totalItems={filteredQuestions.length}
            pageSize={pageSize}
            itemLabel="questions"
            onPageChange={setCurrentPage}
            onPageSizeChange={(newSize) => {
              setPageSize(newSize);
              setCurrentPage(1);
            }}
            pageSizeOptions={[15, 30, 50]}
          />
        </>
      )}

      {/* ── Standardized Accessible Confirmation Modal ───────────────────── */}
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
        isProcessing={actionInProgress}
      />
    </div>
  );
}
