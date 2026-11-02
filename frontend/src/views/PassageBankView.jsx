import React, { useState, useRef, useEffect, useMemo, useCallback } from 'react';
import { BookOpen, Sparkles, Plus } from 'lucide-react';
import {
  fetchPassages,
  fetchSinglePassage,
  savePassage,
  deletePassage,
  approveQuestion
} from '../services/api';
import { PaginationBar } from '../components/common';
import { usePagination } from '../hooks';
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
 */
export default function PassageBankView({ onShowToast, onNavigateToWizard, resetSignal, onRefreshCounts }) {
  const [passages, setPassages] = useState([]);
  const [loading, setLoading] = useState(true);
  const [questionCounts, setQuestionCounts] = useState({});
  const [passageToDelete, setPassageToDelete] = useState(null);

  // Filter & Search State
  const [searchQuery, setSearchQuery] = useState('');
  const [debouncedSearch, setDebouncedSearch] = useState('');
  const [sectionFilter, setSectionFilter] = useState('');
  const [sortBy, setSortBy] = useState('newest');
  const searchInputRef = useRef(null);

  // Debounce search query by 250ms to prevent rapid API polling
  useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedSearch(searchQuery);
    }, 250);
    return () => clearTimeout(handler);
  }, [searchQuery]);

  // Master-Detail Selected State
  const [selectedPassage, setSelectedPassage] = useState(null);
  const [selectedPassageQuestions, setSelectedPassageQuestions] = useState([]);
  const [isLoadingDetail, setIsLoadingDetail] = useState(false);

  // Return to master catalog whenever resetSignal changes (e.g. clicking Passages tab in Navbar)
  const [prevResetSignal, setPrevResetSignal] = useState(resetSignal);
  if (resetSignal !== prevResetSignal) {
    setPrevResetSignal(resetSignal);
    setSelectedPassage(null);
    setSelectedPassageQuestions([]);
  }

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

  // Fetch all passages and build question counts directly from server aggregation
  const performFetchPassages = useCallback(async (isSilent = false, signal = null) => {
    if (!isSilent) setLoading(true);
    try {
      const passageRes = await fetchPassages(
        {
          section: sectionFilter || undefined,
          search: debouncedSearch || undefined
        },
        signal
      );

      const fetchedPassages = passageRes?.passages || [];

      // Map question counts by passage_id from server-aggregated count
      const counts = {};
      fetchedPassages.forEach((p) => {
        counts[p.id] = p.question_count || 0;
      });
      setQuestionCounts(counts);
      setPassages(fetchedPassages);
    } catch (err) {
      if (err.name === 'AbortError') return;
      console.error('Failed to load passages:', err);
      if (onShowToast) {
        onShowToast({
          type: 'error',
          title: 'Load Failed',
          message: 'Could not retrieve reading passages from database.'
        });
      }
    } finally {
      setLoading(false);
    }
  }, [sectionFilter, debouncedSearch, onShowToast]);

  const loadPassages = useCallback(async (isSilent = false, signal = null) => {
    return performFetchPassages(isSilent, signal);
  }, [performFetchPassages]);

  useEffect(() => {
    let ignore = false;
    const controller = new AbortController();

    async function init() {
      if (!ignore) {
        try {
          await performFetchPassages(true, controller.signal);
        } catch (err) {
          if (err.name !== 'AbortError' && !ignore) {
            console.error('Failed to initialize passages:', err);
          }
        }
      }
    }
    init();

    return () => {
      ignore = true;
      controller.abort();
    };
  }, [performFetchPassages]);

  // Sort passages locally
  const sortedPassages = useMemo(() => {
    const list = [...passages];
    if (sortBy === 'newest') {
      list.sort((a, b) => new Date(b.created_at || 0) - new Date(a.created_at || 0));
    } else if (sortBy === 'oldest') {
      list.sort((a, b) => new Date(a.created_at || 0) - new Date(b.created_at || 0));
    } else if (sortBy === 'words_desc') {
      list.sort((a, b) => (b.word_count || 0) - (a.word_count || 0));
    } else if (sortBy === 'words_asc') {
      list.sort((a, b) => (a.word_count || 0) - (b.word_count || 0));
    } else if (sortBy === 'title_asc') {
      list.sort((a, b) => (a.title || '').localeCompare(b.title || ''));
    }
    return list;
  }, [passages, sortBy]);

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

  // Total word count & metrics
  const totalWordCount = useMemo(() => {
    return passages.reduce((acc, p) => acc + (p.word_count || 0), 0);
  }, [passages]);

  const avgWordCount = passages.length > 0 ? Math.round(totalWordCount / passages.length) : 0;

  const hasActiveFilters = Boolean(searchQuery.trim() || sectionFilter);

  const handleClearAllFilters = () => {
    setSearchQuery('');
    setSectionFilter('');
  };

  // Open Passage Editorial Desk
  const handleSelectPassage = async (passage) => {
    setIsLoadingDetail(true);
    setSelectedPassage(passage);
    try {
      const res = await fetchSinglePassage(passage.id);
      if (res?.passage) {
        setSelectedPassage(res.passage);
        setSelectedPassageQuestions(res.questions || []);
      }
    } catch (err) {
      console.error('Failed to load passage detail:', err);
      // Fallback: keep existing passage and questions if available
      setSelectedPassageQuestions(passage.questions || []);
    } finally {
      setIsLoadingDetail(false);
    }
  };

  // Manual New Passage Creation
  const handleCreateNewPassage = () => {
    const newId = `passage-${crypto.randomUUID().slice(0, 8)}`;
    const blankPassage = {
      id: newId,
      title: 'New Reading Passage',
      section: sectionFilter || 'cars',
      subtopic: '',
      text: '',
      word_count: 0,
      image_url: null,
      image_svg: null,
      image_description: null,
      created_at: new Date().toISOString()
    };
    setSelectedPassage(blankPassage);
    setSelectedPassageQuestions([]);
  };

  // Save Passage Handler
  const handleSavePassage = async (updatedPassage) => {
    try {
      const res = await savePassage(updatedPassage);
      const saved = res.passage || updatedPassage;
      setSelectedPassage(saved);

      // Also update stimulus_text in local questions state
      setSelectedPassageQuestions(prev =>
        prev.map(q => ({ ...q, stimulus_text: saved.text }))
      );

      // Refresh passages list
      await loadPassages();

      if (onShowToast) {
        onShowToast({
          type: 'success',
          title: 'Passage Saved',
          message: 'Reading passage and linked question stimuli updated successfully.'
        });
      }
    } catch (err) {
      console.error('Failed to save passage:', err);
      if (onShowToast) {
        onShowToast({
          type: 'error',
          title: 'Save Failed',
          message: err.message || 'Could not save passage updates to database.'
        });
      }
      throw err;
    }
  };

  // Delete Passage Request (Opens Cascade Delete Modal)
  const handleRequestDeletePassage = (passage) => {
    if (!passage) return;
    const qCount = (selectedPassage && selectedPassage.id === passage.id)
      ? selectedPassageQuestions.length
      : (typeof passage.question_count === 'number' ? passage.question_count : 0);
    setPassageToDelete({
      ...passage,
      question_count: qCount
    });
  };

  // Confirm Cascade Delete Handler
  const handleConfirmCascadeDelete = async (passage) => {
    try {
      const res = await deletePassage(passage.id);
      const deletedQuestionsCount = res?.deleted_questions_count ?? passage.question_count ?? 0;

      if (selectedPassage?.id === passage.id) {
        setSelectedPassage(null);
        setSelectedPassageQuestions([]);
      }

      await loadPassages();

      if (onRefreshCounts) {
        onRefreshCounts();
      }

      if (onShowToast) {
        onShowToast({
          type: 'success',
          title: 'Passage Deleted',
          message: deletedQuestionsCount > 0
            ? `Passage and ${deletedQuestionsCount} associated question${deletedQuestionsCount === 1 ? '' : 's'} permanently removed.`
            : 'Passage removed successfully.'
        });
      }
    } catch (err) {
      console.error('Failed to cascade delete passage:', err);
      if (onShowToast) {
        onShowToast({
          type: 'error',
          title: 'Delete Failed',
          message: err.message || 'Could not remove passage from database.'
        });
      }
      throw err;
    }
  };

  // Update Individual Question inside Desk
  const handleUpdateQuestion = async (updatedQ) => {
    try {
      await approveQuestion(updatedQ);
      setSelectedPassageQuestions(prev =>
        prev.map(q => q.id === updatedQ.id ? updatedQ : q)
      );
      if (onShowToast) {
        onShowToast({
          type: 'success',
          title: 'Question Updated',
          message: 'Question changes saved to Question Bank.'
        });
      }
    } catch (err) {
      console.error('Failed to update question:', err);
      if (onShowToast) {
        onShowToast({
          type: 'error',
          title: 'Update Failed',
          message: err.message || 'Could not update question.'
        });
      }
    }
  };

  // ── Render View ────────────────────────────────────────────────────────────
  return (
    <>
      {selectedPassage ? (
        isLoadingDetail ? (
          <div className="view-loading-box">
            <div className="view-loading-spinner" />
            <span className="view-loading-text">Loading Passage Editorial Desk &amp; Questions...</span>
          </div>
        ) : (
          <PassageEditorialDesk
            key={selectedPassage.id}
            passage={selectedPassage}
            questions={selectedPassageQuestions}
            onBack={() => {
              setSelectedPassage(null);
              setSelectedPassageQuestions([]);
            }}
            onSavePassage={handleSavePassage}
            onDeletePassage={handleRequestDeletePassage}
            onUpdateQuestion={handleUpdateQuestion}
          />
        )
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
      {/* ── Header & Stats Strip ─────────────────────────────────────────── */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          flexWrap: 'wrap',
          gap: '16px',
          paddingBottom: '4px'
        }}
      >
        <div>
          <h2 style={{ fontSize: '1.15rem', fontWeight: 700, color: 'var(--text-primary)', letterSpacing: '-0.02em', margin: 0 }}>
            Passage Bank
          </h2>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flexWrap: 'wrap' }}>
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '10px',
              padding: '5px 12px',
              background: 'var(--bg-surface)',
              border: '1px solid var(--border-light)',
              borderRadius: 'var(--radius-sm)',
              fontSize: '0.78rem',
              color: 'var(--text-secondary)'
            }}
          >
            <span>
              <strong style={{ color: 'var(--text-primary)', fontWeight: 600 }}>{passages.length}</strong> {passages.length === 1 ? 'passage' : 'passages'}
            </span>
            <span style={{ color: 'var(--border-light)' }}>•</span>
            <span>
              <strong style={{ color: 'var(--brand-primary)', fontWeight: 600 }}>{avgWordCount}</strong>
              <span style={{ color: 'var(--text-muted)', fontSize: '0.72rem' }}> words avg</span>
            </span>
          </div>

          <button
            type="button"
            id="btn-new-passage-header"
            onClick={handleCreateNewPassage}
            className="btn-primary"
            style={{ padding: '6px 12px', fontSize: '0.78rem', gap: '6px' }}
          >
            <Plus size={13} />
            <span>Create New Passage</span>
          </button>
        </div>
      </div>

      {/* ── Filter / Search Bar ──────────────────────────────────────────── */}
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
        onCreateNewPassage={handleCreateNewPassage}
      />

      {/* ── Passage List Content ─────────────────────────────────────────── */}
      {loading ? (
        <div className="view-loading-box">
          <div className="view-loading-spinner" />
          <span className="view-loading-text">Loading Passages Bank...</span>
        </div>
      ) : passages.length === 0 ? (
        <div className="view-empty-state">
          <div className="view-empty-icon-box">
            <BookOpen size={28} />
          </div>
          <div>
            <h3 className="view-empty-title">
              No Passages Found
            </h3>
            <p className="view-empty-desc">
              {hasActiveFilters
                ? 'No reading passages match your search query or section filter. Clear filters to see more.'
                : 'Your Passages Bank is currently empty. Generate a passage set in the Generator Studio or create one manually!'}
            </p>
          </div>

          <div className="view-empty-actions">
            <button
              type="button"
              onClick={handleCreateNewPassage}
              className="btn-primary"
              style={{ padding: '8px 18px', fontSize: '0.825rem', display: 'inline-flex', alignItems: 'center', gap: '6px' }}
            >
              <Plus size={14} />
              <span>Create New Passage</span>
            </button>

            {onNavigateToWizard && (
              <button
                type="button"
                onClick={onNavigateToWizard}
                className="btn-secondary"
                style={{ padding: '8px 18px', fontSize: '0.825rem', display: 'inline-flex', alignItems: 'center', gap: '6px' }}
              >
                <Sparkles size={14} />
                <span>Generate Questions Set</span>
              </button>
            )}
          </div>
        </div>
      ) : (
        <PassageBankTable
          passages={paginatedPassages}
          questionCounts={questionCounts}
          onSelectPassage={handleSelectPassage}
          onDeletePassage={handleRequestDeletePassage}
          onCopyPassageId={(id) => {
            if (onShowToast) {
              onShowToast({
                type: 'info',
                title: 'ID Copied',
                message: `Passage ID "${id}" copied to clipboard.`
              });
            }
          }}
        />
      )}

      {/* ── Pagination Bar ────────────────────────────────────────────────── */}
      {!loading && passages.length > 0 && (
        <PaginationBar
          currentPage={currentPage}
          totalPages={totalPages}
          pageSize={pageSize}
          totalItems={passages.length}
          itemLabel="passages"
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

        </div>
      )}

      {/* ── Cascade Delete Passage Modal (Single Hoisted Instance) ────────── */}
      <DeletePassageModal
        isOpen={Boolean(passageToDelete)}
        onClose={() => setPassageToDelete(null)}
        passage={passageToDelete}
        onConfirmDelete={handleConfirmCascadeDelete}
      />
    </>
  );
}
