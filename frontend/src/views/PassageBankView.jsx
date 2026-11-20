import { useCallback } from 'react';
import { BookOpen, Sparkles, Plus } from 'lucide-react';
import { PaginationBar, EmptyState } from '../components/common';
import { usePagination, usePassageBank } from '../hooks';
import { PassageBankFilters, PassageBankTable, PassageEditorialDesk } from '../components/passage';
import { DeletePassageModal } from '../components/modals';

/**
 * PassageBankView
 *
 * Dedicated screen for reading passages in the question bank.
 * Provides a master catalog list with filters and an in-depth
 * side-by-side MCAT editorial desk with full linked question support.
 *
 * @param {Object} props
 * @param {(toast: Object) => void} props.onShowToast - Toast trigger callback.
 * @param {(step?: number) => void} props.onNavigateToWizard - Navigation to generation wizard.
 * @param {any} props.resetSignal - Signal to reset selection to master catalog.
 * @param {() => void} props.onRefreshCounts - Global counts refresh callback.
 * @returns {JSX.Element}
 */
export default function PassageBankView({
  onShowToast,
  onNavigateToWizard,
  resetSignal,
  onRefreshCounts
}) {
  const {
    passages,
    page: hookPage,
    pageSize: hookPageSize,
    totalCount,
    setPage,
    setPageSize: setHookPageSize,
    loading,
    questionCounts,
    searchQuery,
    setSearchQuery,
    sectionFilter,
    setSectionFilter,
    sortBy,
    setSortBy,
    searchInputRef,
    hasActiveFilters,
    handleClearAllFilters,
    selectedPassage,
    setSelectedPassage,
    selectedPassageQuestions,
    handleSelectPassage,
    handleCreateNewPassage,
    handleSavePassage,
    handleRequestDeletePassage,
    handleConfirmDeletePassage,
    handleUpdateQuestion,
    passageToDelete,
    setPassageToDelete
  } = usePassageBank({ onShowToast, resetSignal, onRefreshCounts });

  // ─── Pagination ────────────────────────────────────────────────────────────
  const handlePageChange = useCallback((p) => {
    setPage(p);
  }, [setPage]);

  const handlePageSizeChange = useCallback((size) => {
    setHookPageSize(size);
    setPage(1);
  }, [setHookPageSize, setPage]);

  const {
    safeCurrentPage,
    setCurrentPage,
    pageSize,
    setPageSize,
    totalPages
  } = usePagination({
    currentPage: hookPage,
    pageSize: hookPageSize,
    totalCount,
    onPageChange: handlePageChange,
    onPageSizeChange: handlePageSizeChange
  });

  const handleBackFromDesk = useCallback(() => setSelectedPassage(null), [setSelectedPassage]);
  const handleCloseDeleteModal = useCallback(() => setPassageToDelete(null), [setPassageToDelete]);
  const handleCreatePassageSet = useCallback(() => onNavigateToWizard?.(1), [onNavigateToWizard]);

  return (
    <div className="passage-bank-container">
      {/* ── View Header ────────────────────────────────────────────────────────── */}
      <header className="passage-bank-header">
        <div className="passage-header-left">
          <div className="passage-header-icon-wrap">
            <BookOpen size={20} />
          </div>
          <div>
            <h1 className="passage-header-title">Passage Bank</h1>
            <p className="passage-header-subtitle">
              Manage clinical research passages, humanities essays, and their linked MCAT question sets.
            </p>
          </div>
        </div>

        <div className="passage-header-actions">
          <button
            type="button"
            className="btn-secondary"
            onClick={handleCreateNewPassage}
            title="Create a new standalone reading passage"
          >
            <Plus size={15} />
            <span>Create Passage</span>
          </button>
          {onNavigateToWizard && (
            <button
              type="button"
              className="btn-primary"
              onClick={handleCreatePassageSet}
              title="Create a new passage set with the question wizard"
            >
              <Sparkles size={15} />
              <span>Create Passage Set</span>
            </button>
          )}
        </div>
      </header>

      {/* ── Editorial Desk (When a passage is selected) ─────────────────────────── */}
      {selectedPassage ? (
        <PassageEditorialDesk
          passage={selectedPassage}
          questions={selectedPassageQuestions}
          onBack={handleBackFromDesk}
          onSavePassage={handleSavePassage}
          onDeletePassage={handleRequestDeletePassage}
          onUpdateQuestion={handleUpdateQuestion}
          onNavigateToWizard={onNavigateToWizard}
        />
      ) : (
        /* ── Master Catalog List ──────────────────────────────────────────────── */
        <div>
          {/* Filters & Telemetry Bar */}
          <PassageBankFilters
            searchQuery={searchQuery}
            setSearchQuery={setSearchQuery}
            searchInputRef={searchInputRef}
            sectionFilter={sectionFilter}
            setSectionFilter={setSectionFilter}
            sortBy={sortBy}
            setSortBy={setSortBy}
            hasActiveFilters={hasActiveFilters}
            onClearAllFilters={handleClearAllFilters}
          />

          {/* Table Container */}
          {loading ? (
            <div className="view-loading-box">
              <div className="view-loading-spinner" />
              <span className="view-loading-text">Loading reading passages...</span>
            </div>
          ) : passages.length === 0 ? (
            <EmptyState
              icon={<BookOpen size={28} />}
              title="No Passages Found"
              description={
                hasActiveFilters
                  ? 'No passages matched your current search or section filter.'
                  : 'Create a passage by hand or generate a passage set with the wizard.'
              }
            >
              {hasActiveFilters && (
                <button type="button" onClick={handleClearAllFilters} className="btn-secondary">
                  Clear Filters
                </button>
              )}
            </EmptyState>
          ) : (
            <PassageBankTable
              passages={passages}
              questionCounts={questionCounts}
              onSelectPassage={handleSelectPassage}
              onDeletePassage={handleRequestDeletePassage}
            />
          )}

          {/* Pagination */}
          {!loading && passages.length > 0 && (
            <PaginationBar
              currentPage={safeCurrentPage}
              totalPages={totalPages}
              totalItems={totalCount}
              pageSize={pageSize}
              itemLabel="passages"
              onPageChange={setCurrentPage}
              onPageSizeChange={setPageSize}
            />
          )}
        </div>
      )}

      {/* ── Delete Confirmation Modal ────────────────────────────────────────── */}
      <DeletePassageModal
        isOpen={Boolean(passageToDelete)}
        passage={passageToDelete}
        onClose={handleCloseDeleteModal}
        onConfirmDelete={handleConfirmDeletePassage}
      />
    </div>
  );
}
