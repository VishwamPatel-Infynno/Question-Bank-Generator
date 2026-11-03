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
    <div
      style={{
        background: 'var(--bg-surface)',
        border: '1px solid var(--border-light)',
        borderRadius: 'var(--radius-sm)',
        padding: '12px 16px',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        gap: '12px',
        flexWrap: 'wrap'
      }}
    >
      {/* Left: Search & Section Filter */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flex: 1, minWidth: '280px' }}>
        <div style={{ position: 'relative', flex: 1, maxWidth: '360px' }}>
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
            placeholder="Search questions (Press /)..."
            value={searchQuery}
            onChange={(e) => onSearchChange(e.target.value)}
            className="input-field"
            style={{
              paddingLeft: '32px',
              paddingRight: '30px',
              fontSize: '0.78rem',
              height: '34px',
              width: '100%'
            }}
          />
          <span className="kbd-hint" style={{ fontSize: '0.6rem', position: 'absolute', right: '10px', top: '50%', transform: 'translateY(-50%)' }}>/</span>
        </div>

        <select
          value={sectionFilter}
          onChange={(e) => onSectionFilterChange(e.target.value)}
          className="input-field"
          style={{ fontSize: '0.78rem', height: '34px', minWidth: '180px' }}
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
      <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
        {totalFiltered > 0 && (
          <label
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '6px',
              fontSize: '0.75rem',
              fontWeight: 600,
              color: 'var(--text-secondary)',
              cursor: 'pointer',
              marginRight: '6px',
              userSelect: 'none'
            }}
          >
            <input
              type="checkbox"
              checked={allFilteredSelected}
              onChange={onSelectAll}
              style={{ accentColor: 'var(--brand-primary)', cursor: 'pointer' }}
            />
            <span>Select All ({totalFiltered})</span>
          </label>
        )}

        {selectedCount === 0 && totalFiltered > 0 && onApproveAllValidated && (
          <button
            type="button"
            onClick={onApproveAllValidated}
            disabled={actionInProgress}
            className="btn-primary"
            style={{
              padding: '6px 14px',
              fontSize: '0.76rem',
              display: 'inline-flex',
              alignItems: 'center',
              gap: '6px',
              background: 'var(--status-success)',
              borderColor: 'var(--status-success)'
            }}
            title="Save all questions on this page to the Question Bank"
          >
            <Database size={13} />
            <span>Save All to Question Bank ({totalFiltered})</span>
          </button>
        )}

        {selectedCount > 0 && (
          <>
            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', fontWeight: 600 }}>
              {selectedCount} selected
            </span>

            <button
              type="button"
              onClick={onBulkMoveToBank}
              disabled={actionInProgress}
              className="btn-primary"
              style={{
                padding: '6px 14px',
                fontSize: '0.76rem',
                display: 'inline-flex',
                alignItems: 'center',
                gap: '6px',
                background: 'var(--status-success)',
                borderColor: 'var(--status-success)'
              }}
            >
              <Database size={13} />
              <span>Save Selected to Question Bank</span>
            </button>

            <button
              type="button"
              onClick={onBulkDiscard}
              disabled={actionInProgress}
              className="btn-secondary"
              style={{
                padding: '6px 12px',
                fontSize: '0.76rem',
                display: 'inline-flex',
                alignItems: 'center',
                gap: '6px',
                color: 'var(--status-danger)'
              }}
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
