import {
  Search,
  ArrowUpDown,
  Trash2,
  FileDown,
  CheckSquare,
  Square,
  RotateCcw,
  Sparkles
} from 'lucide-react';
import CustomSelect from '../common/CustomSelect';
import { SECTION_FILTER_OPTIONS, DIFFICULTY, normalizeDifficulty } from '../../constants';

const SORT_OPTIONS = [
  { id: 'newest', label: 'Newest First' },
  { id: 'score_desc', label: 'Highest Score' },
  { id: 'score_asc', label: 'Lowest Score' },
  { id: 'difficulty', label: 'Difficulty Level' }
];

const DIFFICULTY_FILTER_OPTIONS = [
  { id: '', label: 'All Levels' },
  { id: DIFFICULTY.LOW, label: 'Low' },
  { id: DIFFICULTY.MEDIUM, label: 'Medium' },
  { id: DIFFICULTY.HIGH, label: 'High' }
];

/**
 * QuestionBankFilters
 *
 * Renders the search bar, difficulty chips, status filter, section pills, sort selector,
 * and bulk-selection action bar.
 */
export default function QuestionBankFilters({
  searchQuery,
  setSearchQuery,
  searchMode = 'keyword',
  setSearchMode,
  isSearchingSemantic = false,
  searchInputRef,
  sectionFilter,
  setSectionFilter,
  diffFilter,
  setDiffFilter,
  sortBy,
  setSortBy,
  questions,
  selectedIds,
  isDeletingBulk,
  hasActiveFilters,
  onSelectAll,
  onBulkDelete,
  onClearAllFilters,
  onNavigateToWizard,
  onOpenExportModal,
}) {
  return (
    <div className="qbank-filters">
      {/* Primary Toolbar Row */}
      <div className="qbank-filters-row">
        {/* Search Input & AI Mode Toggle */}
        <div className="qbank-search-group">
          <div className="qbank-search">
            <Search size={13} color="var(--text-muted)" />
            <input
              ref={searchInputRef}
              id="input-bank-search"
              aria-label="Search questions by question, passage, topic, or trap"
              type="text"
              placeholder={
                searchMode === 'semantic'
                  ? 'AI Semantic Search by concept (e.g. enzyme kinetics)...'
                  : 'Search questions (Press /)...'
              }
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="qbank-search-input"
            />
            {searchMode === 'keyword' && <span className="kbd-hint qbank-filters-kbd">/</span>}
          </div>

          {setSearchMode && (
            <div className="qbank-search-mode-toggle" role="group" aria-label="Search mode toggle">
              <button
                type="button"
                className={`qbank-search-mode-btn ${searchMode === 'keyword' ? 'active' : ''}`}
                onClick={() => setSearchMode('keyword')}
                title="Exact keyword substring search"
                aria-pressed={searchMode === 'keyword'}
              >
                <span>Exact</span>
              </button>
              <button
                type="button"
                className={`qbank-search-mode-btn ${searchMode === 'semantic' ? 'active' : ''}`}
                onClick={() => setSearchMode('semantic')}
                title="AI Semantic vector search via pgvector"
                aria-pressed={searchMode === 'semantic'}
              >
                <Sparkles size={11} className={isSearchingSemantic ? 'animate-spin' : ''} />
                <span>AI Semantic</span>
              </button>
            </div>
          )}
        </div>

        {/* Section Filter Pills */}
        <div className="pill-track qbank-filters-track-wrap">
          {SECTION_FILTER_OPTIONS.map(sec => {
            const isActive = sectionFilter === sec.id;
            return (
              <button
                key={sec.id}
                type="button"
                className={`pill-track-btn qbank-filters-pill-btn ${isActive ? 'active' : ''}`}
                onClick={() => setSectionFilter(sec.id)}
                aria-pressed={isActive}
              >
                <span>{sec.label}</span>
              </button>
            );
          })}
        </div>

        {/* Difficulty Filter Chips */}
        <div className="pill-track qbank-filters-track-wrap">
          {DIFFICULTY_FILTER_OPTIONS.map(d => {
            const isActive = diffFilter === d.id || normalizeDifficulty(diffFilter) === d.id;
            return (
              <button
                key={d.id}
                type="button"
                onClick={() => setDiffFilter(d.id)}
                className={`pill-track-btn qbank-filters-pill-btn ${isActive ? 'active' : ''}`}
                aria-pressed={isActive}
              >
                {d.label}
              </button>
            );
          })}
        </div>

        {/* Sort Selector */}
        <div className="qbank-filters-sort-wrap">
          <span className="qbank-filters-sort-label">
            <ArrowUpDown size={11} /> Sort:
          </span>
          <CustomSelect
            id="select-bank-sort"
            label="Sort Questions"
            size="sm"
            value={sortBy}
            onChange={(newSort) => setSortBy(newSort)}
            options={SORT_OPTIONS.map((opt) => ({ value: opt.id, label: opt.label }))}
            align="right"
            className="qbank-filters-sort-select"
          />
        </div>
      </div>

      {/* Bulk Action Bar (When items are selected) */}
      {questions.length > 0 && (
        <div className="qbank-bulk-bar">
          <div className="qbank-bulk-group">
            <button
              type="button"
              onClick={onSelectAll}
              className="btn-secondary qbank-filters-clear-btn"
              aria-pressed={selectedIds.length === questions.length}
              aria-label={selectedIds.length === questions.length ? 'Deselect all questions' : 'Select all questions'}
            >
              {selectedIds.length === questions.length ? (
                <CheckSquare size={13} color="var(--brand-primary)" />
              ) : (
                <Square size={13} />
              )}
              <span>{selectedIds.length === questions.length ? 'Deselect All' : 'Select All'}</span>
            </button>

            {selectedIds.length > 0 && (
              <span className="qbank-bulk-count">
                {selectedIds.length} of {questions.length} selected
              </span>
            )}
          </div>

          {selectedIds.length > 0 && (
            <div className="qbank-bulk-group">
              <button
                type="button"
                id="btn-bulk-export-studio"
                onClick={onOpenExportModal}
                className="btn-secondary qbank-filters-bulk-btn"
                title="Export &amp; Print selected questions"
              >
                <FileDown size={13} />
                <span>Export Selected ({selectedIds.length})</span>
              </button>

              <button
                type="button"
                onClick={onBulkDelete}
                disabled={isDeletingBulk}
                className="btn-danger qbank-filters-bulk-btn"
                aria-label={`Delete ${selectedIds.length} selected question(s)`}
              >
                <Trash2 size={13} />
                <span>{isDeletingBulk ? 'Deleting...' : `Delete Selected (${selectedIds.length})`}</span>
              </button>
            </div>
          )}
        </div>
      )}

      {/* Empty-state filter clear / wizard CTA (shown when filtered to 0 results) */}
      {questions.length === 0 && hasActiveFilters && (
        <div className="qbank-filters-bulk-bar">
          <button
            type="button"
            id="btn-bank-clear-filters"
            onClick={onClearAllFilters}
            className="btn-secondary qbank-filters-bulk-btn"
          >
            <RotateCcw size={13} />
            <span>Clear Active Filters</span>
          </button>
          {onNavigateToWizard && (
            <button
              type="button"
              id="btn-bank-empty-create"
              onClick={onNavigateToWizard}
              className="btn-primary qbank-filters-export-btn"
            >
              <Sparkles size={13} />
              <span>Create New Questions</span>
            </button>
          )}
        </div>
      )}
    </div>
  );
}
