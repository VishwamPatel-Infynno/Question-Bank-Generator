import { Search, Database, Trash2 } from 'lucide-react';
import { MCAT_SECTIONS_FALLBACK } from '../../constants/mcat';

export default function AiValidatedFiltersBar({
  searchQuery = '',
  onSearchChange,
  searchInputRef,
  sectionFilter = '',
  onSectionFilterChange,
  totalFiltered = 0,
  allFilteredSelected = false,
  onSelectAll,
  selectedCount = 0,
  actionInProgress = false,
  onBulkMoveToBank,
  onBulkDiscard,
  onApproveAllValidated
}) {
  return (
    <div className="validated-filters-bar">
      {/* Left: Search & Section Filter */}
      <div className="validated-filters-search-group">
        <div className="validated-filters-search-wrap">
          <Search size={14} className="validated-filters-search-icon" />
          <input
            ref={searchInputRef}
            type="text"
            placeholder="Search questions (Press /)..."
            value={searchQuery}
            onChange={(e) => onSearchChange(e.target.value)}
            className="input-field validated-filters-search-input"
          />
          <span className="kbd-hint validated-filters-search-kbd">/</span>
        </div>

        <select
          value={sectionFilter}
          onChange={(e) => onSectionFilterChange(e.target.value)}
          className="input-field validated-filters-select"
        >
          <option value="">All Sections</option>
          {MCAT_SECTIONS_FALLBACK.map((sec) => (
            <option key={sec.id} value={sec.id}>
              {sec.label}
            </option>
          ))}
        </select>
      </div>

      {/* Right: Selection & Bulk Actions */}
      <div className="validated-filters-actions">
        {totalFiltered > 0 && (
          <label className="validated-filters-select-all-btn">
            <input
              type="checkbox"
              checked={allFilteredSelected}
              onChange={onSelectAll}
              className="form-checkbox"
            />
            <span>Select All ({totalFiltered})</span>
          </label>
        )}

        {selectedCount === 0 && totalFiltered > 0 && onApproveAllValidated && (
          <button
            type="button"
            onClick={onApproveAllValidated}
            disabled={actionInProgress}
            className="btn-primary validated-save-btn validated-btn-approve-all"
            title="Save all questions on this page to the Question Bank"
          >
            <Database size={13} />
            <span>Save All to Question Bank ({totalFiltered})</span>
          </button>
        )}

        {selectedCount > 0 && (
          <>
            <span className="validated-filters-selected-badge">
              {selectedCount} selected
            </span>

            <button
              type="button"
              onClick={onBulkMoveToBank}
              disabled={actionInProgress}
              className="btn-primary validated-save-btn validated-btn-approve-all"
            >
              <Database size={13} />
              <span>Save Selected to Question Bank</span>
            </button>

            <button
              type="button"
              onClick={onBulkDiscard}
              disabled={actionInProgress}
              className="btn-secondary validated-btn-discard-all"
            >
              <Trash2 size={13} />
              <span>Discard Selected</span>
            </button>
          </>
        )}
      </div>
    </div>
  );
}
