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
      {/* Primary Toolbar Row */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
        {/* Search Input */}
        <div
          style={{
            flex: '1 1 200px',
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
            id="input-bank-search"
            aria-label="Search questions by question, passage, topic, or trap"
            type="text"
            placeholder="Search questions (Press /)..."
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

        {/* Difficulty Filter Chips */}
        <div className="pill-track" style={{ flexShrink: 0 }}>
          {DIFFICULTY_FILTER_OPTIONS.map(d => {
            const isActive = diffFilter === d.id ||
              (d.id === 'low' && diffFilter === 'easy') ||
              (d.id === 'high' && diffFilter === 'hard');
            return (
              <button
                key={d.id}
                type="button"
                onClick={() => setDiffFilter(d.id)}
                className={`pill-track-btn ${isActive ? 'active' : ''}`}
                style={{ padding: '4px 8px', fontSize: '0.72rem' }}
              >
                {d.label}
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
            id="select-bank-sort"
            label="Sort Questions"
            size="sm"
            value={sortBy}
            onChange={(newSort) => setSortBy(newSort)}
            options={SORT_OPTIONS.map((opt) => ({ value: opt.id, label: opt.label }))}
            searchable={false}
            align="right"
            style={{ width: '135px' }}
          />
        </div>
      </div>

      {/* Bulk Action Bar (When items are selected) */}
      {questions.length > 0 && (
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            paddingTop: '8px',
            borderTop: '1px solid var(--border-subtle)',
            fontSize: '0.78rem',
            color: 'var(--text-secondary)'
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <button
              onClick={onSelectAll}
              className="btn-secondary"
              style={{ padding: '6px 10px', fontSize: '0.75rem', gap: '6px' }}
            >
              {selectedIds.length === questions.length ? (
                <CheckSquare size={13} color="var(--brand-primary)" />
              ) : (
                <Square size={13} />
              )}
              <span>{selectedIds.length === questions.length ? 'Deselect All' : 'Select All'}</span>
            </button>

            {selectedIds.length > 0 && (
              <span style={{ fontWeight: 600, color: 'var(--text-primary)' }}>
                {selectedIds.length} of {questions.length} selected
              </span>
            )}
          </div>

          {selectedIds.length > 0 && (
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <button
                type="button"
                id="btn-bulk-export-studio"
                onClick={onOpenExportModal}
                className="btn-secondary"
                style={{ padding: '6px 12px', fontSize: '0.75rem', gap: '6px' }}
                title="Export &amp; Print selected questions"
              >
                <FileDown size={13} />
                <span>Export Selected ({selectedIds.length})</span>
              </button>

              <button
                onClick={onBulkDelete}
                disabled={isDeletingBulk}
                className="btn-danger"
                style={{ padding: '6px 12px', fontSize: '0.75rem', gap: '6px' }}
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
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginTop: '4px', flexWrap: 'wrap' }}>
          <button
            type="button"
            id="btn-bank-clear-filters"
            onClick={onClearAllFilters}
            className="btn-secondary"
            style={{ padding: '6px 12px', fontSize: '0.78rem', gap: '6px' }}
          >
            <RotateCcw size={13} />
            <span>Clear Active Filters</span>
          </button>
          {onNavigateToWizard && (
            <button
              type="button"
              id="btn-bank-empty-create"
              onClick={onNavigateToWizard}
              className="btn-primary"
              style={{ padding: '6px 14px', fontSize: '0.78rem', gap: '6px' }}
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
