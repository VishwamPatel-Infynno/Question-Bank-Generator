import { memo } from 'react';

/**
 * ExportScopeSelector
 *
 * Renders the question dataset scope selector pill track within the Export & Print Modal.
 * Supports switching between Selected Questions, Filtered Questions, and All Bank.
 */
function ExportScopeSelector({
  scope = 'all',
  onScopeChange,
  exportCount = 0,
  selectedCount = 0,
  filteredCount = 0,
  allCount = 0,
  hasActiveFilters = false
}) {
  return (
    <div className="exam-export-group" data-testid="export-scope-selector">
      <span className="exam-export-group-label">
        Questions ({exportCount})
      </span>
      <div className="pill-track" role="tablist" aria-label="Export Question Scope">
        {selectedCount > 0 && (
          <button
            type="button"
            role="tab"
            aria-selected={scope === 'selected'}
            className={`pill-track-btn ${scope === 'selected' ? 'active' : ''}`}
            onClick={() => onScopeChange?.('selected')}
          >
            <span>Selected ({selectedCount})</span>
          </button>
        )}
        {hasActiveFilters && (
          <button
            type="button"
            role="tab"
            aria-selected={scope === 'filtered'}
            className={`pill-track-btn ${scope === 'filtered' ? 'active' : ''}`}
            onClick={() => onScopeChange?.('filtered')}
          >
            <span>Filtered ({filteredCount})</span>
          </button>
        )}
        <button
          type="button"
          role="tab"
          aria-selected={scope === 'all'}
          className={`pill-track-btn ${scope === 'all' ? 'active' : ''}`}
          onClick={() => onScopeChange?.('all')}
        >
          <span>All ({allCount})</span>
        </button>
      </div>
    </div>
  );
}

export default memo(ExportScopeSelector);
