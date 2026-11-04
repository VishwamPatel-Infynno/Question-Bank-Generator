import { Search } from 'lucide-react';

export default function BatchFiltersBar({
  searchQuery = '',
  onSearchChange,
  searchInputRef,
  scopeFilter = 'all',
  onScopeFilterChange,
  sectionFilter = 'all',
  onSectionFilterChange,
  statusFilter = 'all',
  onStatusFilterChange,
  autoRefresh = true,
  onAutoRefreshChange
}) {
  return (
    <div className="batch-filters-bar">
      <div className="batch-filters-left">
        {/* Search */}
        <div className="batch-search-box">
          <Search size={14} className="batch-search-icon" />
          <input
            ref={searchInputRef}
            type="text"
            placeholder="Search batches (Press /)..."
            value={searchQuery}
            onChange={(e) => onSearchChange(e.target.value)}
            className="input-field batch-search-input"
          />
          <span className="kbd-hint batch-search-kbd">/</span>
        </div>

        {/* Scope Tabs */}
        <div className="pill-track batch-filter-pill-track">
          {[
            { id: 'all', label: 'All Practice Sets' },
            { id: 'mini', label: 'Quick Sets (5 Questions)' },
            { id: 'full', label: 'Full Sets (50 Questions)' }
          ].map((scope) => (
            <button
              key={scope.id}
              type="button"
              onClick={() => onScopeFilterChange?.(scope.id)}
              className={`pill-track-btn batch-filter-pill-btn ${scopeFilter === scope.id ? 'active' : ''}`}
            >
              {scope.label}
            </button>
          ))}
        </div>

        {/* Section Filter */}
        <select
          value={sectionFilter}
          onChange={(e) => onSectionFilterChange(e.target.value)}
          className="input-field batch-filter-select"
        >
          <option value="all">All Sections</option>
          <option value="CP">Chemical & Physical (CP)</option>
          <option value="CARS">Critical Analysis (CARS)</option>
          <option value="BB">Biological & Biochemical (BB)</option>
          <option value="PS">Psychological & Social (PS)</option>
        </select>

        {/* Status Tabs */}
        <div className="pill-track batch-filter-pill-track">
          {['all', 'in_progress', 'completed', 'failed'].map((st) => (
            <button
              key={st}
              type="button"
              onClick={() => onStatusFilterChange(st)}
              className={`pill-track-btn batch-filter-pill-btn ${statusFilter === st ? 'active' : ''}`}
            >
              {st === 'in_progress' ? 'Running' : st.replace('_', ' ')}
            </button>
          ))}
        </div>
      </div>

      {/* Live Polling Toggle */}
      <div className="batch-autorefresh-toggle">
        <label className="batch-autorefresh-toggle">
          <input
            type="checkbox"
            checked={autoRefresh}
            onChange={(e) => onAutoRefreshChange(e.target.checked)}
            className="form-checkbox"
          />
          {autoRefresh && <span className="batch-autorefresh-dot" />}
          <span>Live Auto-Sync</span>
        </label>
      </div>
    </div>
  );
}
