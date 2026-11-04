import React from 'react';
import { Database, Sparkles, RotateCcw } from 'lucide-react';

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
  const isDeleted = Boolean(question.is_deleted && question.status !== 'discarded');

  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        paddingTop: '6px',
        borderTop: '1px dashed var(--border-light)'
      }}
    >
      <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>
        {question.aamc_skill || question.primary_trap || 'MCAT Standard'}
      </div>
      <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
        {isDeleted && onRestoreQuestion && (
          <button
            type="button"
            onClick={() => onRestoreQuestion(question)}
            className="btn-primary"
            style={{
              padding: '3px 9px',
              fontSize: '0.7rem',
              display: 'inline-flex',
              alignItems: 'center',
              gap: '4px',
              background: 'rgba(16, 185, 129, 0.15)',
              color: 'var(--status-success, #10b981)',
              border: '1px solid rgba(16, 185, 129, 0.3)'
            }}
            title="Restore this question back to Question Bank"
          >
            <RotateCcw size={10} />
            <span>Restore to Bank</span>
          </button>
        )}

        {!isDeleted && status === 'batch_only' && onSaveToBank && (
          <button
            type="button"
            onClick={() => onSaveToBank(question)}
            className="btn-primary"
            style={{
              padding: '3px 9px',
              fontSize: '0.7rem',
              display: 'inline-flex',
              alignItems: 'center',
              gap: '4px'
            }}
            title="Save question directly to Question Bank"
          >
            <Database size={10} />
            <span>Save to Question Bank</span>
          </button>
        )}

        {!isDeleted && status === 'ai_validated' && onNavigateToValidated && (
          <button
            type="button"
            onClick={onNavigateToValidated}
            className="btn-primary"
            style={{ padding: '2px 8px', fontSize: '0.7rem', display: 'inline-flex', alignItems: 'center', gap: '4px' }}
            title="Review in Ready for Review screen"
          >
            <Sparkles size={10} />
            <span>Review Question</span>
          </button>
        )}

        {!isDeleted && status === 'in_bank' && onNavigateToBank && (
          <button
            type="button"
            onClick={onNavigateToBank}
            className="btn-secondary"
            style={{ padding: '2px 8px', fontSize: '0.7rem', display: 'inline-flex', alignItems: 'center', gap: '4px' }}
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
            className="btn-secondary"
            style={{ padding: '2px 8px', fontSize: '0.7rem' }}
          >
            Quality Review
          </button>
        )}
      </div>
    </div>
  );
}

