import React from 'react';
import { Layers, Sparkles } from 'lucide-react';

/**
 * BatchEmptyState
 *
 * Rendered when no batches match the current filter query or when no batches have been created yet.
 */
export default function BatchEmptyState({
  searchQuery = '',
  statusFilter = 'all',
  sectionFilter = 'all',
  onNavigateToWizard
}) {
  const isFiltered = Boolean(searchQuery || statusFilter !== 'all' || sectionFilter !== 'all');

  return (
    <div className="view-empty-state">
      <div className="view-empty-icon-box">
        <Layers size={26} />
      </div>
      <div>
        <h3 className="view-empty-title">
          No Batches Found
        </h3>
        <p className="view-empty-desc">
          {isFiltered
            ? 'No generation batches match your active filters. Try clearing your search.'
            : 'You have not generated any question batches yet. Click below to start your first batch in the Question Studio.'}
        </p>
      </div>
      <div className="view-empty-actions">
        {onNavigateToWizard && (
          <button
            type="button"
            className="btn-primary"
            onClick={onNavigateToWizard}
            style={{
              padding: '8px 20px',
              fontSize: '0.85rem',
              display: 'inline-flex',
              alignItems: 'center',
              gap: '6px'
            }}
          >
            <Sparkles size={14} />
            <span>Start Question Batch</span>
          </button>
        )}
      </div>
    </div>
  );
}

