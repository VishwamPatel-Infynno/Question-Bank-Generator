import { SECTION_FILTER_OPTIONS } from '../../constants';
import {
  Search,
  ArrowUpDown,
  RotateCcw,
  Plus
} from 'lucide-react';
import CustomSelect from '../common/CustomSelect';

const SORT_OPTIONS = [
  { id: 'newest', label: 'Newest First' },
  { id: 'oldest', label: 'Oldest First' },
  { id: 'words_desc', label: 'Word Count (High)' },
  { id: 'words_asc', label: 'Word Count (Low)' },
  { id: 'title_asc', label: 'Title (A-Z)' }
];

/**
 * PassageBankFilters
 *
 * Controls search query, section category pills, sort ordering,
 * and the "+ New Passage" action trigger.
 */
export default function PassageBankFilters({
  searchQuery,
  setSearchQuery,
  searchInputRef,
  sectionFilter,
  setSectionFilter,
  sortBy,
  setSortBy,
  hasActiveFilters,
  onClearAllFilters,
  onCreateNewPassage
}) {
  return (
    <div className="passage-bank-filters">
      <div className="passage-bank-filters-row">
        {/* Search Input */}
        <div className="passage-bank-search">
          <Search size={13} color="var(--text-muted)" />
          <input
            ref={searchInputRef}
            id="input-passage-search"
            aria-label="Search passages by title, text, subtopic, or ID"
            type="text"
            placeholder="Search passages (Press /)..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="passage-bank-search-input"
          />
          <span className="kbd-hint passage-bank-filters-kbd">/</span>
        </div>

        {/* Section Filter Pills */}
        <div className="pill-track passage-bank-track-wrap">
          {SECTION_FILTER_OPTIONS.map(sec => {
            const isActive = sectionFilter === sec.id;
            return (
              <button
                key={sec.id}
                type="button"
                className={`pill-track-btn passage-bank-pill-btn ${isActive ? 'active' : ''}`}
                onClick={() => setSectionFilter(sec.id)}
              >
                <span>{sec.label}</span>
              </button>
            );
          })}
        </div>

        {/* Sort Selector */}
        <div className="passage-bank-sort-wrap">
          <span className="passage-bank-sort-label">
            <ArrowUpDown size={11} /> Sort:
          </span>
          <CustomSelect
            id="select-passage-sort"
            label="Sort Passages"
            size="sm"
            value={sortBy}
            onChange={(newSort) => setSortBy(newSort)}
            options={SORT_OPTIONS.map((opt) => ({ value: opt.id, label: opt.label }))}
            align="right"
            className="passage-bank-sort-select"
          />

          {hasActiveFilters && (
            <button
              type="button"
              onClick={onClearAllFilters}
              className="btn-ghost passage-bank-reset-btn"
              title="Reset all search queries and section filters"
            >
              <RotateCcw size={11} />
              <span>Reset</span>
            </button>
          )}

          {onCreateNewPassage && (
            <button
              type="button"
              id="btn-create-new-passage"
              onClick={onCreateNewPassage}
              className="btn-primary passage-bank-create-btn"
              title="Manually create a new reading passage"
            >
              <Plus size={13} />
              <span>New Passage</span>
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
