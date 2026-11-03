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

const SECTION_FILTER_OPTIONS = [
  { id: '', label: 'All Sections' },
  { id: 'chem_phys', label: 'Chem / Phys' },
  { id: 'cars', label: 'CARS' },
  { id: 'bio_biochem', label: 'Bio / Biochem' },
  { id: 'psych_soc', label: 'Psych / Soc' }
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
    <div
      style={{
        background: 'var(--bg-surface)',
        border: '1px solid var(--border-light)',
        borderRadius: 'var(--radius-md)',
        padding: '10px 14px',
        display: 'flex',
        flexDirection: 'column',
        gap: '8px'
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
        {/* Search Input */}
        <div
          style={{
            flex: '1 1 220px',
            minWidth: '180px',
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            background: 'var(--bg-surface)',
            padding: '0 10px',
            borderRadius: 'var(--radius-sm)',
            border: '1px solid var(--border-light)',
            height: '32px'
          }}
        >
          <Search size={13} color="var(--text-muted)" />
          <input
            ref={searchInputRef}
            id="input-passage-search"
            aria-label="Search passages by title, text, subtopic, or ID"
            type="text"
            placeholder="Search passages (Press /)..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            style={{
              border: 'none',
              background: 'transparent',
              padding: '6px 0',
              width: '100%',
              fontSize: '0.78rem',
              color: 'var(--text-primary)',
              outline: 'none'
            }}
          />
          <span className="kbd-hint" style={{ fontSize: '0.6rem' }}>/</span>
        </div>

        {/* Section Filter Pills */}
        <div className="pill-track" style={{ flexShrink: 0 }}>
          {SECTION_FILTER_OPTIONS.map(sec => {
            const isActive = sectionFilter === sec.id;
            return (
              <button
                key={sec.id}
                type="button"
                className={`pill-track-btn ${isActive ? 'active' : ''}`}
                onClick={() => setSectionFilter(sec.id)}
                style={{ fontSize: '0.72rem', padding: '4px 9px' }}
              >
                <span>{sec.label}</span>
              </button>
            );
          })}
        </div>

        {/* Sort Selector */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginLeft: 'auto', flexShrink: 0 }}>
          <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: '3px', whiteSpace: 'nowrap' }}>
            <ArrowUpDown size={11} /> Sort:
          </span>
          <CustomSelect
            id="select-passage-sort"
            label="Sort Passages"
            size="sm"
            value={sortBy}
            onChange={(newSort) => setSortBy(newSort)}
            options={SORT_OPTIONS.map((opt) => ({ value: opt.id, label: opt.label }))}
            searchable={false}
            align="right"
            style={{ width: '150px' }}
          />

          {hasActiveFilters && (
            <button
              type="button"
              onClick={onClearAllFilters}
              className="btn-ghost"
              style={{
                fontSize: '0.72rem',
                color: 'var(--text-muted)',
                padding: '4px 8px',
                height: '32px',
                display: 'flex',
                alignItems: 'center',
                gap: '4px'
              }}
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
              className="btn-primary"
              style={{
                fontSize: '0.75rem',
                padding: '6px 12px',
                gap: '5px',
                height: '32px'
              }}
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

