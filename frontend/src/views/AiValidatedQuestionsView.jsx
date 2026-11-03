import React, { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import {
  CheckCircle2,
  ArrowRight
} from 'lucide-react';
import { PaginationBar } from '../components/common';
import { ConfirmationModal } from '../components/modals';
import { usePagination } from '../hooks';
import {
  fetchQuestions,
  fetchQuestionCounts,
  updateQuestionStatus,
  batchUpdateQuestionStatus,
  purgeQuestion,
  purgeQuestionsBatch
} from '../services/api';
import {
  AiValidatedStatsBar,
  AiValidatedFiltersBar,
  AiValidatedQuestionCard
} from '../components/validated';

export default function AiValidatedQuestionsView({
  onOpenAudit,
  onNavigateToBank,
  onNavigateToBatches,
  onNavigateToWizard,
  onShowToast,
  onRefreshCounts
}) {
  const [questions, setQuestions] = useState([]);
  const [counts, setCounts] = useState({ ai_validated: 0, in_bank: 0, discarded: 0, below_threshold: 0 });
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [actionInProgress, setActionInProgress] = useState(false);

  // Standardized confirmation modal state
  const [confirmModal, setConfirmModal] = useState({
    isOpen: false,
    title: '',
    description: '',
    confirmLabel: 'Confirm',
    variant: 'danger',
    itemCount: null,
    itemLabel: 'question',
    onConfirm: null
  });

  // Filters
  const [searchQuery, setSearchQuery] = useState('');
  const [debouncedSearch, setDebouncedSearch] = useState('');
  const [sectionFilter, setSectionFilter] = useState('');
  const [expandedPassageIds, setExpandedPassageIds] = useState({});
  const searchInputRef = useRef(null);

  // Debounce search query by 250ms to ensure responsive filtering
  useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedSearch(searchQuery);
    }, 250);
    return () => clearTimeout(handler);
  }, [searchQuery]);

  // Focus search on '/'
  useEffect(() => {
    const handleSlash = (e) => {
      if (e.key === '/' && document.activeElement?.tagName.toLowerCase() !== 'input' && document.activeElement?.tagName.toLowerCase() !== 'textarea') {
        e.preventDefault();
        searchInputRef.current?.focus();
      }
    };
    window.addEventListener('keydown', handleSlash);
    return () => window.removeEventListener('keydown', handleSlash);
  }, []);

  // Multi-selection state
  const [selectedIds, setSelectedIds] = useState([]);

  // Load questions and counts asynchronously without synchronous pre-render state mutations
  const performFetchValidated = useCallback(async (isSilent = false) => {
    try {
      const [qsRes, countsRes] = await Promise.all([
        fetchQuestions({ status: 'ai_validated', section: sectionFilter || undefined, slim: true }),
        fetchQuestionCounts()
      ]);
      const loadedQs = (qsRes.questions || []).filter(q => (q.final_score || 0) > 90);
      setQuestions(loadedQs);
      setCounts(countsRes || {});
      if (onRefreshCounts) onRefreshCounts();
    } catch (err) {
      console.error('Failed to load AI validated questions:', err);
      if (!isSilent && onShowToast) {
        onShowToast({
          type: 'error',
          title: 'Load Failed',
          message: 'Could not fetch validated questions from database.'
        });
      }
    } finally {
      setLoading(false);
      if (!isSilent) setRefreshing(false);
    }
  }, [sectionFilter, onRefreshCounts, onShowToast]);

  const loadData = useCallback(async (isSilent = false) => {
    if (!isSilent) setRefreshing(true);
    return performFetchValidated(isSilent);
  }, [performFetchValidated]);

  // Initial load on mount and when filter changes
  useEffect(() => {
    let ignore = false;
    async function init() {
      if (!ignore) {
        await performFetchValidated(true);
      }
    }
    init();
    return () => {
      ignore = true;
    };
  }, [performFetchValidated]);

  // Filtered in-memory questions by search query (strictly preserving score > 90 benchmark)
  const filteredQuestions = useMemo(() => {
    const validQuestions = questions.filter(item => (item.final_score || 0) > 90);
    if (!debouncedSearch.trim()) return validQuestions;
    const q = debouncedSearch.toLowerCase().trim();
    return validQuestions.filter(item =>
      (item.question_stem && item.question_stem.toLowerCase().includes(q)) ||
      (item.subtopic && item.subtopic.toLowerCase().includes(q)) ||
      (item.explanation && item.explanation.toLowerCase().includes(q)) ||
      (item.stimulus_text && item.stimulus_text.toLowerCase().includes(q))
    );
  }, [questions, debouncedSearch]);

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

  // Toggle single selection
  const handleToggleSelect = (id) => {
    setSelectedIds(prev =>
      prev.includes(id) ? prev.filter(x => x !== id) : [...prev, id]
    );
  };

  // Toggle select all
  const handleSelectAll = () => {
    const currentIds = filteredQuestions.map(q => q.id);
    const allSelected = currentIds.length > 0 && currentIds.every(id => selectedIds.includes(id));
    if (allSelected) {
      setSelectedIds(prev => prev.filter(id => !currentIds.includes(id)));
    } else {
      setSelectedIds(prev => Array.from(new Set([...prev, ...currentIds])));
    }
  };

  // Single question actions
  const handleMoveToBankSingle = async (q) => {
    setActionInProgress(true);
    try {
      await updateQuestionStatus(q.id, 'in_bank');
      setQuestions(prev => prev.filter(item => item.id !== q.id));
      setSelectedIds(prev => prev.filter(id => id !== q.id));
      if (onShowToast) {
        onShowToast({
          type: 'success',
          title: 'Success - Question Saved to Bank',
          message: 'Question is now available in your Question Bank.',
          action: onNavigateToBank ? { label: 'View in Bank', onClick: onNavigateToBank } : undefined
        });
      }
      if (onRefreshCounts) onRefreshCounts();
      loadData(true);
    } catch (err) {
      console.error('Error promoting question:', err);
      if (onShowToast) {
        onShowToast({ type: 'error', title: 'Action Failed', message: err.message || 'Could not move question.' });
      }
    } finally {
      setActionInProgress(false);
    }
  };

  const handleDiscardSingle = async (q) => {
    setActionInProgress(true);
    try {
      await purgeQuestion(q.id);
      setQuestions(prev => prev.filter(item => item.id !== q.id));
      setSelectedIds(prev => prev.filter(id => id !== q.id));
      if (onShowToast) {
        onShowToast({
          type: 'info',
          title: 'Question Discarded',
          message: 'Question has been permanently removed.'
        });
      }
      if (onRefreshCounts) onRefreshCounts();
      loadData(true);
    } catch (err) {
      console.error('Error discarding question:', err);
      if (onShowToast) {
        onShowToast({ type: 'error', title: 'Action Failed', message: err.message || 'Could not discard question.' });
      }
    } finally {
      setActionInProgress(false);
    }
  };

  // Bulk actions
  const handleBulkMoveToBank = async () => {
    if (selectedIds.length === 0) return;
    const count = selectedIds.length;
    setActionInProgress(true);
    try {
      await batchUpdateQuestionStatus(selectedIds, 'in_bank');
      setQuestions(prev => prev.filter(item => !selectedIds.includes(item.id)));
      if (onShowToast) {
        onShowToast({
          type: 'success',
          title: 'Success - Saved to Bank',
          message: `Successfully placed ${count} question(s) into Question Bank.`,
          action: onNavigateToBank ? { label: 'View in Bank', onClick: onNavigateToBank } : undefined
        });
      }
      setSelectedIds([]);
      if (onRefreshCounts) onRefreshCounts();
      loadData(true);
    } catch (err) {
      console.error('Bulk move failed:', err);
      if (onShowToast) {
        onShowToast({ type: 'error', title: 'Bulk Move Failed', message: err.message || 'Error updating questions.' });
      }
    } finally {
      setActionInProgress(false);
    }
  };

  const handleBulkDiscard = () => {
    if (selectedIds.length === 0) return;
    const count = selectedIds.length;
    setConfirmModal({
      isOpen: true,
      title: 'Discard Selected Questions',
      description: `Are you sure you want to discard ${count} selected question${count !== 1 ? 's' : ''}? They will be permanently removed from the system.`,
      confirmLabel: `Discard ${count} Question${count !== 1 ? 's' : ''}`,
      variant: 'danger',
      itemCount: count,
      itemLabel: 'question',
      onConfirm: async () => {
        setActionInProgress(true);
        try {
          await purgeQuestionsBatch(selectedIds);
          setQuestions(prev => prev.filter(item => !selectedIds.includes(item.id)));
          if (onShowToast) {
            onShowToast({
              type: 'info',
              title: 'Questions Discarded',
              message: `${count} question(s) permanently removed.`
            });
          }
          setSelectedIds([]);
          if (onRefreshCounts) onRefreshCounts();
          loadData(true);
          setConfirmModal(prev => ({ ...prev, isOpen: false }));
        } catch (err) {
          console.error('Bulk discard failed:', err);
          if (onShowToast) {
            onShowToast({ type: 'error', title: 'Bulk Discard Failed', message: err.message || 'Error deleting questions.' });
          }
        } finally {
          setActionInProgress(false);
        }
      }
    });
  };

  const handleApproveAllValidated = async () => {
    const allIds = filteredQuestions.map(q => q.id);
    if (allIds.length === 0) return;
    const count = allIds.length;
    setActionInProgress(true);
    try {
      await batchUpdateQuestionStatus(allIds, 'in_bank');
      setQuestions(prev => prev.filter(item => !allIds.includes(item.id)));
      setSelectedIds([]);
      if (onShowToast) {
        onShowToast({
          type: 'success',
          title: 'All Questions Saved to Bank',
          message: `${count} question(s) saved to Question Bank.`,
          action: onNavigateToBank ? { label: 'View in Bank', onClick: onNavigateToBank } : undefined
        });
      }
      if (onRefreshCounts) onRefreshCounts();
      loadData(true);
    } catch (err) {
      console.error('Save all questions failed:', err);
      if (onShowToast) {
        onShowToast({ type: 'error', title: 'Action Failed', message: err.message || 'Error updating questions.' });
      }
    } finally {
      setActionInProgress(false);
    }
  };

  const togglePassage = (id) => {
    setExpandedPassageIds(prev => ({ ...prev, [id]: !prev[id] }));
  };

  const allFilteredSelected =
    filteredQuestions.length > 0 && filteredQuestions.every(q => selectedIds.includes(q.id));

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
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
          <span className="view-loading-text">Loading Questions Ready for Review...</span>
        </div>
      ) : filteredQuestions.length === 0 ? (
        /* Empty State */
        <div className="view-empty-state">
          <div className="view-empty-icon-box">
            <CheckCircle2 size={28} />
          </div>
          <div>
            <h3 className="view-empty-title">
              No Pending Questions to Review
            </h3>
            <p className="view-empty-desc">
              {searchQuery || sectionFilter
                ? 'No questions matched your current filter criteria. Try clearing filters.'
                : 'All high-quality questions have been saved to your Question Bank or reviewed. Generate a new practice set to create more questions.'}
            </p>
          </div>
          <div className="view-empty-actions">
            {onNavigateToBatches && (
              <button
                type="button"
                className="btn-primary"
                onClick={onNavigateToBatches}
                style={{ padding: '8px 18px', fontSize: '0.825rem', display: 'inline-flex', alignItems: 'center', gap: '6px' }}
              >
                <span>View Progress & History</span>
                <ArrowRight size={14} />
              </button>
            )}
            {onNavigateToWizard && (
              <button
                type="button"
                className="btn-secondary"
                onClick={onNavigateToWizard}
                style={{ padding: '8px 18px', fontSize: '0.825rem' }}
              >
                Create Questions
              </button>
            )}
          </div>
        </div>
      ) : (
        /* Questions List */
        <>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
            {paginatedQuestions.map((q, idx) => (
              <AiValidatedQuestionCard
                key={q.id}
                question={q}
                index={(safeCurrentPage - 1) * pageSize + idx}
                isSelected={selectedIds.includes(q.id)}
                onToggleSelect={handleToggleSelect}
                isPassageExpanded={Boolean(expandedPassageIds[q.id])}
                onTogglePassage={togglePassage}
                onOpenAudit={onOpenAudit}
                onMoveToBank={handleMoveToBankSingle}
                onDiscard={handleDiscardSingle}
                actionInProgress={actionInProgress}
              />
            ))}
          </div>

          {/* Pagination Bar */}
          {filteredQuestions.length > 0 && (
            <PaginationBar
              currentPage={currentPage}
              totalPages={totalPages}
              pageSize={pageSize}
              totalItems={filteredQuestions.length}
              itemLabel="validated questions"
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
        </>
      )}

      {/* ── Standardized Accessible Confirmation Modal ───────────────────── */}
      <ConfirmationModal
        isOpen={confirmModal.isOpen}
        onClose={() => setConfirmModal(prev => ({ ...prev, isOpen: false }))}
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
