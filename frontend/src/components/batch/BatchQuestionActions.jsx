import { Database, Sparkles, RotateCcw } from 'lucide-react';
import { QUESTION_STATUS } from '../../constants';

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
  onRestoreQuestion
}) {
  const isDeleted = Boolean(question.is_deleted && question.status !== QUESTION_STATUS.DISCARDED);

  return (
    <div className="batch-qitem-actions-bar">
      <div className="batch-qitem-actions-meta">
        {question.aamc_skill || question.primary_trap || 'MCAT Standard'}
      </div>
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
