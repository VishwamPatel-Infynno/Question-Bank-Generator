import { PaginationBar } from '../components/common';
import { ConfirmationModal } from '../components/modals';
import { usePagination, useBatchActivity } from '../hooks';
import {
  BatchStatsHeader,
  BatchFiltersBar,
  BatchCard,
  ActiveMultiBatchMonitor,
  BatchEmptyState,
  BatchHeaderBanner
} from '../components/batch';

/**
 * BatchActivityView
 *
 * Dedicated view for monitoring parallel question generation batches,
 * inspecting active and historical runs, pausing/resuming jobs, and reviewing question sets.
 *
 * @param {Object} props
 * @param {(question: Object) => void} props.onOpenAudit - Callback to open psychometric audit modal.
 * @param {() => void} props.onNavigateToBank - Callback to navigate to Question Bank view.
 * @param {() => void} props.onNavigateToValidated - Callback to navigate to AI Validated view.
 * @param {(step?: number) => void} props.onNavigateToWizard - Callback to navigate to generation wizard.
 * @param {(toast: Object) => void} props.onShowToast - Callback to trigger toast notifications.
 * @returns {JSX.Element}
 */
export default function BatchActivityView({
  onOpenAudit,
  onNavigateToBank,
  onNavigateToValidated,
  onNavigateToWizard,
  onShowToast
}) {
  const {
    batches,
    filteredBatches,
    activeBatchesList,
    activeCount,
    loading,
    refreshing,
    loadBatches,
    scopeFilter,
    setScopeFilter,
    statusFilter,
    setStatusFilter,
    sectionFilter,
    setSectionFilter,
    searchQuery,
    setSearchQuery,
    searchInputRef,
    autoRefresh,
    setAutoRefresh,
    expandedBatchIds,
    batchDetails,
    loadingDetails,
    handleToggleExpandBatch,
    expandedJobIds,
    handleToggleJob,
    handleStopBatch,
    handleRetryBatch,
    handleCancelAllBatches,
    handleDeleteBatch,
    handleSaveQuestionToBank,
    handleRestoreQuestion,
    stoppingBatchIds,
    retryingBatchIds,
    isCancellingAll,
    isDeletingBatch,
    confirmModal,
    closeConfirmModal
  } = useBatchActivity({ onShowToast, onNavigateToBank });

  // ─── Pagination ────────────────────────────────────────────────────────────
  const {
    currentPage,
    setCurrentPage,
    pageSize,
    setPageSize,
    totalPages,
    paginatedItems: paginatedBatches
  } = usePagination({
    items: filteredBatches,
    initialPageSize: 10,
    resetDeps: [scopeFilter, statusFilter, sectionFilter, searchQuery]
  });

  return (
    <div className="batch-activity-container">
      {/* Header Bar */}
      <BatchHeaderBanner
        refreshing={refreshing}
        onRefresh={() => loadBatches(false)}
        onNavigateToWizard={onNavigateToWizard}
      />

      {/* Active Multi-Batch Monitor Hero (Visible when 1+ batches running) */}
      {activeBatchesList.length > 0 && (
        <ActiveMultiBatchMonitor
          activeBatches={activeBatchesList}
          onCancelAll={handleCancelAllBatches}
          isCancellingAll={isCancellingAll}
        />
      )}

      {/* Top Telemetry Stat Cards */}
      <BatchStatsHeader batches={batches} activeCount={activeCount} />

      {/* Filter and Search Bar */}
      <BatchFiltersBar
        searchQuery={searchQuery}
        onSearchChange={setSearchQuery}
        searchInputRef={searchInputRef}
        scopeFilter={scopeFilter}
        onScopeFilterChange={setScopeFilter}
        sectionFilter={sectionFilter}
        onSectionFilterChange={setSectionFilter}
        statusFilter={statusFilter}
        onStatusFilterChange={setStatusFilter}
        autoRefresh={autoRefresh}
        onAutoRefreshChange={setAutoRefresh}
      />

      {/* Batches List Container */}
      {loading ? (
        <div className="view-loading-box">
          <div className="view-loading-spinner" />
          <span className="view-loading-text">Loading batch records...</span>
        </div>
      ) : filteredBatches.length === 0 ? (
        <BatchEmptyState
          searchQuery={searchQuery}
          statusFilter={statusFilter}
          sectionFilter={sectionFilter}
          onNavigateToWizard={onNavigateToWizard}
        />
      ) : (
        <>
          <div className="batch-activity-list">
            {paginatedBatches.map((batch) => (
              <BatchCard
                key={batch.id}
                batch={batch}
                isExpanded={expandedBatchIds.has(batch.id)}
                onToggleExpand={handleToggleExpandBatch}
                onDeleteBatch={handleDeleteBatch}
                onStopBatch={handleStopBatch}
                onRetryBatch={handleRetryBatch}
                isStopping={stoppingBatchIds[batch.id]}
                isRetrying={retryingBatchIds[batch.id]}
                detail={batchDetails[batch.id] || null}
                loadingDetail={loadingDetails[batch.id]}
                expandedJobIds={expandedJobIds}
                onToggleJob={handleToggleJob}
                onNavigateToBank={onNavigateToBank}
                onNavigateToValidated={onNavigateToValidated}
                onOpenAudit={onOpenAudit}
                onSaveToBank={handleSaveQuestionToBank}
                onRestoreQuestion={handleRestoreQuestion}
              />
            ))}
          </div>

          {filteredBatches.length > 0 && (
            <PaginationBar
              currentPage={currentPage}
              totalPages={totalPages}
              totalItems={filteredBatches.length}
              pageSize={pageSize}
              itemLabel="batches"
              onPageChange={setCurrentPage}
              onPageSizeChange={(newSize) => {
                setPageSize(newSize);
                setCurrentPage(1);
              }}
              pageSizeOptions={[10, 25, 50]}
            />
          )}
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
        isProcessing={isDeletingBatch}
      />
    </div>
  );
}
