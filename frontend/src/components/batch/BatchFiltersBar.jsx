import React from 'react';
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
    <div
      style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        flexWrap: 'wrap',
        gap: '12px',
        background: 'var(--bg-surface)',
        border: '1px solid var(--border-light)',
        borderRadius: 'var(--radius-sm)',
        padding: '10px 14px'
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flexWrap: 'wrap', flex: 1 }}>
        {/* Search */}
        <div style={{ position: 'relative', minWidth: '180px', flex: 1, maxWidth: '280px' }}>
          <Search
            size={14}
            style={{
              position: 'absolute',
              left: '10px',
              top: '50%',
              transform: 'translateY(-50%)',
              color: 'var(--text-muted)'
            }}
          />
          <input
            ref={searchInputRef}
            type="text"
            placeholder="Search batches (Press /)..."
            value={searchQuery}
            onChange={(e) => onSearchChange(e.target.value)}
            className="input-field"
            style={{
              width: '100%',
              paddingLeft: '32px',
              paddingRight: '30px',
              fontSize: '0.78rem',
              height: '32px'
            }}
          />
          <span className="kbd-hint" style={{ fontSize: '0.6rem', position: 'absolute', right: '10px', top: '50%', transform: 'translateY(-50%)' }}>/</span>
        </div>

        {/* Scope Tabs */}
        <div className="pill-track" style={{ padding: '2px' }}>
          {[
            { id: 'all', label: 'All Practice Sets' },
            { id: 'mini', label: 'Quick Sets (5 Questions)' },
            { id: 'full', label: 'Full Sets (50 Questions)' }
          ].map((scope) => (
            <button
              key={scope.id}
              type="button"
              onClick={() => onScopeFilterChange?.(scope.id)}
              className={`pill-track-btn ${scopeFilter === scope.id ? 'active' : ''}`}
              style={{ padding: '4px 10px', fontSize: '0.75rem' }}
            >
              {scope.label}
            </button>
          ))}
        </div>

        {/* Section Filter */}
        <select
          value={sectionFilter}
          onChange={(e) => onSectionFilterChange(e.target.value)}
          className="input-field"
          style={{
            fontSize: '0.78rem',
            height: '32px'
          }}
        >
          <option value="all">All Sections</option>
          <option value="CP">Chemical & Physical (CP)</option>
          <option value="CARS">Critical Analysis (CARS)</option>
          <option value="BB">Biological & Biochemical (BB)</option>
          <option value="PS">Psychological & Social (PS)</option>
        </select>

        {/* Status Tabs */}
        <div className="pill-track" style={{ padding: '2px' }}>
          {['all', 'in_progress', 'completed', 'failed'].map((st) => (
            <button
              key={st}
              type="button"
              onClick={() => onStatusFilterChange(st)}
              className={`pill-track-btn ${statusFilter === st ? 'active' : ''}`}
              style={{ padding: '4px 10px', fontSize: '0.75rem', textTransform: 'capitalize' }}
            >
              {st === 'in_progress' ? 'Running' : st}
            </button>
          ))}
        </div>
      </div>

      {/* Live Polling Toggle */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
        <label
          style={{
            fontSize: '0.75rem',
            color: 'var(--text-secondary)',
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
            cursor: 'pointer'
          }}
        >
          <input
            type="checkbox"
            checked={autoRefresh}
            onChange={(e) => onAutoRefreshChange(e.target.checked)}
            style={{ accentColor: 'var(--brand-primary)', cursor: 'pointer' }}
          />
          <span>Live Auto-Sync</span>
        </label>
      </div>
    </div>
  );
}
