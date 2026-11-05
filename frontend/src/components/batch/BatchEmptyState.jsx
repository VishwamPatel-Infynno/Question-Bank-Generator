import { Layers, Sparkles } from 'lucide-react';
import { BATCH_FILTER } from '../../constants';
import EmptyState from '../common/EmptyState';

/**
 * BatchEmptyState
 *
 * Rendered when no batches match the current filter query or when no batches have been created yet.
 */
export default function BatchEmptyState({
  searchQuery = '',
  statusFilter = BATCH_FILTER.ALL,
  sectionFilter = 'all',
  onNavigateToWizard
}) {
  const isFiltered = Boolean(searchQuery || statusFilter !== BATCH_FILTER.ALL || sectionFilter !== 'all');

  return (
    <EmptyState
      icon={<Layers size={26} />}
      title="No Batches Found"
      description={
        isFiltered
          ? 'No generation batches match your active filters. Try clearing your search.'
          : 'You have not generated any question batches yet. Click below to start your first batch in the Question Studio.'
      }
    >
      {onNavigateToWizard && (
        <button type="button" className="btn-primary batch-empty-btn" onClick={onNavigateToWizard}>
          <Sparkles size={14} />
          <span>Start Question Batch</span>
        </button>
      )}
    </EmptyState>
  );
}
