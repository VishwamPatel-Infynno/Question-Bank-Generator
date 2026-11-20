import { Database, Sparkles, RotateCcw, GitCompare, ShieldCheck } from 'lucide-react';
import { QUESTION_STATUS } from '../../constants';
import { hasDuplicateAlert } from '../../utils';

/**
 * BatchQuestionActions - Bottom action bar for question items (Restore, Save to Bank, Review, Audit).
 */
export default function BatchQuestionActions({
  question,
  status,
  onNavigateToBank,
  onNavigateToValidated,
  onOpenAudit,
  onSaveToBank,
  onRestoreQuestion,
  onCompareDuplicate,
  onOverrideDuplicate
}) {
  const isDeleted = Boolean(question.is_deleted && question.status !== QUESTION_STATUS.DISCARDED);
  const showDuplicateActions =
    !isDeleted && status !== QUESTION_STATUS.DISCARDED && hasDuplicateAlert(question);

  return (
    <div className="batch-qitem-actions-bar">
      <div className="batch-qitem-actions-group">
        {isDeleted && onRestoreQuestion && (
          <button
            type="button"
            onClick={() => onRestoreQuestion(question)}
            className="btn-primary batch-qitem-btn-restore"
            title="Restore this question back to Question Bank"
          >
            <RotateCcw size={10} />
            <span>Restore to Bank</span>
          </button>
        )}

        {!isDeleted && status === QUESTION_STATUS.BATCH_ONLY && onSaveToBank && (
          <button
            type="button"
            onClick={() => onSaveToBank(question)}
            className="btn-primary batch-qitem-btn-action"
            title="Save question directly to Question Bank"
          >
            <Database size={10} />
            <span>Save to Question Bank</span>
          </button>
        )}

        {!isDeleted && status === QUESTION_STATUS.AI_VALIDATED && onNavigateToValidated && (
          <button
            type="button"
            onClick={onNavigateToValidated}
            className="btn-primary batch-qitem-btn-sm"
            title="Review in Ready for Review screen"
          >
            <Sparkles size={10} />
            <span>Review Question</span>
          </button>
        )}

        {!isDeleted && status === QUESTION_STATUS.IN_BANK && onNavigateToBank && (
          <button
            type="button"
            onClick={onNavigateToBank}
            className="btn-secondary batch-qitem-btn-sm"
            title="View in Question Bank"
          >
            <Database size={10} />
            <span>In Question Bank</span>
          </button>
        )}

        {showDuplicateActions && onCompareDuplicate && (
          <button
            type="button"
            onClick={() => onCompareDuplicate(question)}
            className="btn-secondary batch-qitem-btn-sm"
            title="Compare with the original question"
          >
            <GitCompare size={10} />
            <span>Compare</span>
          </button>
        )}

        {showDuplicateActions && onOverrideDuplicate && (
          <button
            type="button"
            onClick={() => onOverrideDuplicate(question)}
            className="btn-secondary batch-qitem-btn-sm"
            title="Approve this question even though it looks like another one"
          >
            <ShieldCheck size={10} />
            <span>Override and approve</span>
          </button>
        )}

        {onOpenAudit && (
          <button
            type="button"
            onClick={() => onOpenAudit(question)}
            className="btn-secondary batch-qitem-btn-sm"
          >
            Quality Review
          </button>
        )}
      </div>
    </div>
  );
}
