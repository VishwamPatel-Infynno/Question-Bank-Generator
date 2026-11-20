import { useCallback } from 'react';
import { CheckCircle2, Sparkles } from 'lucide-react';
import { PaginationBar, LoadError, EmptyState } from '../components/common';
import { ConfirmationModal } from '../components/modals';
import { DuplicateCompareModal } from '../components/duplicates';
import { usePagination, useAiValidated } from '../hooks';
import {
  AiValidatedStatsBar,
  AiValidatedFiltersBar,
  AiValidatedQuestionCard
} from '../components/validated';
import { confirmModalProps } from '../components/modals/confirmModalProps';

/**
 * AiValidatedQuestionsView
 *
 * Dedicated view for inspecting questions that met or exceeded the 80/100
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
    loadError,
    refreshing,
    actionInProgress,
    loadData,
    searchQuery,
    setSearchQuery,
    debouncedSearch,
    sectionFilter,
    setSectionFilter,
    searchInputRef,
    setPage,
    pageSize,
    setPageSize,
    totalCount,
    selectedIds,
    allFilteredSelected,
    handleToggleSelect,
    handleSelectAll,
    activeId,
    handleActivate,
    compareQuestion,
    isOverriding,
    openCompare,
    closeCompare,
    handleOverride,
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

  const effectiveTotalCount = totalCount || counts.ai_validated || filteredQuestions.length;

  // ─── Server-Driven Pagination ───────────────────────────────────────────────
  const {
    setCurrentPage,
    totalPages,
    safeCurrentPage,
    paginatedItems: paginatedQuestions
  } = usePagination({
    items: filteredQuestions,
    initialPageSize: pageSize,
    totalCount: effectiveTotalCount,
    onPageChange: setPage,
    onPageSizeChange: setPageSize,
    resetDeps: [debouncedSearch, sectionFilter]
  });

  const handleRefresh = useCallback(() => loadData(false), [loadData]);
  const handleCreateNewQuestions = useCallback(() => onNavigateToWizard?.(1), [onNavigateToWizard]);

  return (
    <div className="validated-questions-stack">
      {/* Header and Metrics */}
      <AiValidatedStatsBar
        counts={counts}
        questionsCount={questions.length}
        refreshing={refreshing}
        onRefresh={handleRefresh}
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
      ) : loadError && questions.length === 0 ? (
        <LoadError
          title="Could not load validated questions"
          message={loadError}
          onRetry={handleRefresh}
        />
      ) : filteredQuestions.length === 0 ? (
        <EmptyState
          icon={<CheckCircle2 size={28} />}
          iconTone="success"
          title="No Questions Awaiting Review"
          description={
            debouncedSearch || sectionFilter
              ? 'No questions matched your current search filters.'
              : 'All generated questions have been reviewed and moved to the Question Bank. Start a new generation run to create more.'
          }
        >
          {onNavigateToBatches && (
            <button type="button" onClick={onNavigateToBatches} className="btn-secondary">
              View Batch Progress
            </button>
          )}
          {onNavigateToWizard && (
            <button
              type="button"
              id="btn-validated-empty-create"
              onClick={handleCreateNewQuestions}
              className="btn-primary"
            >
              <Sparkles size={14} />
              <span>Create New Questions</span>
            </button>
          )}
        </EmptyState>
      ) : (
        <>
          <div className="ai-validated-list-container">
            {paginatedQuestions.map((question, idx) => (
              <AiValidatedQuestionCard
                key={question.id}
                question={question}
                index={(safeCurrentPage - 1) * pageSize + idx}
                isSelected={selectedIds.includes(question.id)}
                isPassageExpanded={Boolean(expandedPassageIds[question.id])}
                actionInProgress={actionInProgress}
                onToggleSelect={handleToggleSelect}
                onTogglePassage={togglePassage}
                onMoveToBank={handleMoveToBankSingle}
                onDiscard={handleDiscardSingle}
                onOpenAudit={onOpenAudit}
                onCompareDuplicate={openCompare}
                isActive={question.id === activeId}
                onActivate={handleActivate}
              />
            ))}
          </div>

          <PaginationBar
            currentPage={safeCurrentPage}
            totalPages={totalPages}
            totalItems={effectiveTotalCount}
            pageSize={pageSize}
            itemLabel="questions"
            onPageChange={setCurrentPage}
            onPageSizeChange={setPageSize}
          />
        </>
      )}

      <DuplicateCompareModal
        question={compareQuestion}
        onClose={closeCompare}
        onOverride={handleOverride}
        isOverriding={isOverriding}
      />

      {/* ── Standardized Accessible Confirmation Modal ───────────────────── */}
      <ConfirmationModal {...confirmModalProps(confirmModal, closeConfirmModal, actionInProgress)} />
    </div>
  );
}
