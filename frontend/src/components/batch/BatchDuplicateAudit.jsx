import { useState, useCallback, memo } from 'react';
import { Copy, Loader2, Search } from 'lucide-react';
import { ConfirmationModal } from '../modals';
import { useBatchDuplicateAudit } from '../../hooks';

const plural = (n, word) => `${n} ${word}${n === 1 ? '' : 's'}`;

/**
 * BatchDuplicateAudit
 *
 * On-demand panel inside an expanded batch: "Check duplicates" lists groups of near-identical
 * questions and "Resolve duplicates" archives all but the best question of each group (after a
 * confirmation). It never runs on its own.
 *
 * @param {Object} props
 * @param {string} props.batchId
 * @param {(toast: Object) => void} [props.onShowToast]
 * @param {(batchId: string) => void | Promise<void>} [props.onResolved] - Refreshes the batch after a resolve.
 */
function BatchDuplicateAudit({ batchId, onShowToast, onResolved }) {
  const { report, resolution, error, isChecking, isResolving, check, resolve } = useBatchDuplicateAudit({
    batchId,
    onShowToast,
    onResolved
  });
  const [confirmOpen, setConfirmOpen] = useState(false);

  const handleCloseConfirm = useCallback(() => setConfirmOpen(false), []);
  const handleConfirm = useCallback(async () => {
    const ok = await resolve();
    if (ok) setConfirmOpen(false);
  }, [resolve]);

  const clusters = report?.clusters || [];
  const repeated = report?.total_duplicate_questions ?? 0;

  return (
    <div className="batch-dup-audit">
      <div className="batch-dup-audit-head">
        <div className="batch-dup-audit-title">
          <Copy size={14} aria-hidden="true" />
          <span>Duplicate check</span>
        </div>
        <button
          type="button"
          className="btn-secondary batch-dup-audit-btn"
          onClick={check}
          disabled={isChecking || isResolving}
        >
          {isChecking ? <Loader2 size={12} className="spin-animate" aria-hidden="true" /> : <Search size={12} aria-hidden="true" />}
          <span>{isChecking ? 'Checking...' : 'Check duplicates'}</span>
        </button>
      </div>

      <div aria-live="polite">
        {error && <p className="batch-dup-audit-error">{error}</p>}

        {resolution && (
          <p className="batch-dup-audit-note">
            Archived {plural(resolution.archived_count ?? 0, 'duplicate question')}.{' '}
            {resolution.remaining_active_questions} of {resolution.target_count} questions remain
            {resolution.deficit > 0 ? `, ${plural(resolution.deficit, 'question')} short of the target.` : '.'}
          </p>
        )}

        {report && clusters.length === 0 && (
          <p className="batch-dup-audit-note">
            No duplicates found among {plural(report.total_active_questions ?? 0, 'question')}.
            {report.archived_duplicates_count > 0
              ? ` ${plural(report.archived_duplicates_count, 'duplicate')} already archived.`
              : ''}
          </p>
        )}

        {report && clusters.length > 0 && (
          <>
            <p className="batch-dup-audit-note">
              Found {plural(clusters.length, 'group')} of similar questions ({plural(repeated, 'repeated question')} out
              of {report.total_active_questions}).
            </p>
            <ul className="batch-dup-audit-list">
              {clusters.map((cluster, i) => (
                <li key={cluster.cluster_id} className="batch-dup-audit-item">
                  <span className="batch-dup-audit-item-head">
                    Group {i + 1}: {cluster.size} questions, up to {Math.round((cluster.highest_similarity || 0) * 100)}% similar
                  </span>
                  {cluster.leader_question?.question_stem && (
                    <span className="batch-dup-audit-item-stem">{cluster.leader_question.question_stem}</span>
                  )}
                </li>
              ))}
            </ul>
            <div className="batch-dup-audit-actions">
              <button
                type="button"
                className="btn-primary batch-dup-audit-btn"
                onClick={() => setConfirmOpen(true)}
                disabled={isResolving}
              >
                Resolve duplicates
              </button>
            </div>
          </>
        )}
      </div>

      <ConfirmationModal
        isOpen={confirmOpen}
        onClose={handleCloseConfirm}
        onConfirm={handleConfirm}
        title="Resolve duplicates"
        description="We will keep the best question in each group and archive the rest. Archived questions can be restored later. This batch may end up with fewer questions than its target."
        confirmLabel="Archive duplicates"
        variant="warning"
        itemCount={repeated}
        itemLabel="question"
        isProcessing={isResolving}
      />
    </div>
  );
}

export default memo(BatchDuplicateAudit);
