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

const SORT_OPTIONS = [
  { id: 'newest', label: 'Newest First' },
  { id: 'score_desc', label: 'Highest Score' },
  { id: 'score_asc', label: 'Lowest Score' },
  { id: 'difficulty', label: 'Difficulty Level' }
];

const SECTION_FILTER_OPTIONS = [
  { id: '', label: 'All Sections' },
  { id: 'chem_phys', label: 'Chem / Phys' },
  { id: 'cars', label: 'CARS' },
  { id: 'bio_biochem', label: 'Bio / Biochem' },
  { id: 'psych_soc', label: 'Psych / Soc' }
];

const DIFFICULTY_FILTER_OPTIONS = [
  { id: '', label: 'All Levels' },
  { id: 'low', label: 'Low' },
  { id: 'medium', label: 'Medium' },
  { id: 'high', label: 'High' }
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
        {/* Search Input */}
        <div className="qbank-search">
          <Search size={13} color="var(--text-muted)" />
          <input
            ref={searchInputRef}
            id="input-bank-search"
            aria-label="Search questions by question, passage, topic, or trap"
            type="text"
            placeholder="Search questions (Press /)..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="qbank-search-input"
          />
          <span className="kbd-hint qbank-filters-kbd">/</span>
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
              >
                <span>{sec.label}</span>
              </button>
            );
          })}
        </div>

        {/* Difficulty Filter Chips */}
        <div className="pill-track qbank-filters-track-wrap">
          {DIFFICULTY_FILTER_OPTIONS.map(d => {
            const isActive = diffFilter === d.id ||
              (d.id === 'low' && diffFilter === 'easy') ||
              (d.id === 'high' && diffFilter === 'hard');
            return (
              <button
                key={d.id}
                type="button"
                onClick={() => setDiffFilter(d.id)}
                className={`pill-track-btn qbank-filters-pill-btn ${isActive ? 'active' : ''}`}
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
            searchable={false}
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
              onClick={onSelectAll}
              className="btn-secondary qbank-filters-clear-btn"
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
                onClick={onBulkDelete}
                disabled={isDeletingBulk}
                className="btn-danger qbank-filters-bulk-btn"
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
