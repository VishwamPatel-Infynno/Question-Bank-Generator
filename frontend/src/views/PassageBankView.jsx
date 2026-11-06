import { BookOpen, Sparkles, Plus } from 'lucide-react';
import { PaginationBar, EmptyState } from '../components/common';
import { usePagination, usePassageBank } from '../hooks';
import PassageBankFilters from '../components/passage/PassageBankFilters';
import PassageBankTable from '../components/passage/PassageBankTable';
import PassageEditorialDesk from '../components/passage/PassageEditorialDesk';
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
    sortedPassages,
    loading,
    questionCounts,
    searchQuery,
    setSearchQuery,
    debouncedSearch,
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
  const {
    currentPage,
    setCurrentPage,
    pageSize,
    setPageSize,
    totalPages,
    paginatedItems: paginatedPassages
  } = usePagination({
    items: sortedPassages,
    initialPageSize: 15,
    resetDeps: [debouncedSearch, sectionFilter, sortBy]
  });

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
              onClick={() => onNavigateToWizard(1)}
              title="Generate a new passage set using AI"
            >
              <Sparkles size={15} />
              <span>Generate Passage Set</span>
            </button>
          )}
        </div>
      </header>

      {/* ── Editorial Desk (When a passage is selected) ─────────────────────────── */}
      {selectedPassage ? (
        <PassageEditorialDesk
          passage={selectedPassage}
          questions={selectedPassageQuestions}
          onBack={() => setSelectedPassage(null)}
          onSavePassage={handleSavePassage}
          onDeletePassage={handleRequestDeletePassage}
          onUpdateQuestion={handleUpdateQuestion}
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
          ) : sortedPassages.length === 0 ? (
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
              passages={paginatedPassages}
              questionCounts={questionCounts}
              onSelectPassage={handleSelectPassage}
              onDeletePassage={handleRequestDeletePassage}
            />
          )}

          {/* Pagination */}
          {!loading && sortedPassages.length > 0 && (
            <PaginationBar
              currentPage={currentPage}
              totalPages={totalPages}
              totalItems={sortedPassages.length}
              pageSize={pageSize}
              itemLabel="passages"
              onPageChange={setCurrentPage}
              onPageSizeChange={(newSize) => {
                setPageSize(newSize);
                setCurrentPage(1);
              }}
              pageSizeOptions={[15, 30, 50]}
            />
          )}
        </div>
      )}

      {/* ── Delete Confirmation Modal ────────────────────────────────────────── */}
      <DeletePassageModal
        isOpen={Boolean(passageToDelete)}
        passage={passageToDelete}
        onClose={() => setPassageToDelete(null)}
        onConfirmDelete={handleConfirmDeletePassage}
      />
    </div>
  );
}
