import { useState } from 'react';
import { 
  AlertTriangle, 
  X, 
  ShieldCheck, 
  Trash2, 
  RotateCcw, 
  Check
} from 'lucide-react';
import { useFocusTrap } from '../../hooks';

export default function DuplicateComparisonModal({
  isOpen,
  onClose,
  candidateQuestion,
  onOverrideApprove,
  onRegenerate,
  onDiscard
}) {
  const modalRef = useFocusTrap({ isActive: Boolean(isOpen), onClose });
  const [isSubmitting, setIsSubmitting] = useState(false);

  if (!isOpen || !candidateQuestion) return null;

  const dupInfo = candidateQuestion.duplicate_info || {};
  const similarityPercent = Math.round((dupInfo.similarity_score || 0) * 100);

  const candidateOptions = candidateQuestion.options || [];
  const candidateCorrectKeys = Array.isArray(candidateQuestion.correct_answer_ids) && candidateQuestion.correct_answer_ids.length > 0
    ? candidateQuestion.correct_answer_ids.map(k => String(k).trim().toUpperCase())
    : (candidateQuestion.correct_answer_id || '').split(',').map(k => k.trim().toUpperCase()).filter(Boolean);

  const matchedOptions = dupInfo.matched_options || [];

  const handleOverride = async () => {
    if (isSubmitting || !onOverrideApprove) return;
    setIsSubmitting(true);
    try {
      await onOverrideApprove(candidateQuestion);
      onClose();
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleDiscard = () => {
    if (onDiscard) {
      onDiscard(candidateQuestion.id);
      onClose();
    }
  };

  const handleRegenerate = async () => {
    if (isSubmitting || !onRegenerate) return;
    setIsSubmitting(true);
    try {
      await onRegenerate(candidateQuestion);
      onClose();
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div
      style={{
        position: 'fixed',
        inset: 0,
        backgroundColor: 'rgba(15, 23, 42, 0.75)',
        backdropFilter: 'blur(4px)',
        zIndex: 9999,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '20px'
      }}
      role="dialog"
      aria-modal="true"
      aria-labelledby="dup-modal-title"
    >
      <div
        ref={modalRef}
        style={{
          background: 'var(--bg-surface)',
          borderRadius: 'var(--radius-md)',
          border: '1px solid var(--border-medium)',
          boxShadow: '0 20px 25px -5px rgba(0, 0, 0, 0.25), 0 10px 10px -5px rgba(0, 0, 0, 0.1)',
          width: '100%',
          maxWidth: '1020px',
          maxHeight: '90vh',
          display: 'flex',
          flexDirection: 'column',
          overflow: 'hidden',
          animation: 'modalSlideIn 0.2s cubic-bezier(0.16, 1, 0.3, 1)'
        }}
      >
        {/* Header */}
        <div
          style={{
            padding: '16px 20px',
            borderBottom: '1px solid var(--border-light)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            background: 'var(--bg-canvas)'
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <div
              style={{
                width: '32px',
                height: '32px',
                borderRadius: '8px',
                background: 'rgba(245, 158, 11, 0.12)',
                color: 'var(--status-warning, #f59e0b)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center'
              }}
            >
              <AlertTriangle size={18} />
            </div>
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <h3 id="dup-modal-title" style={{ margin: 0, fontSize: '1rem', fontWeight: 700, color: 'var(--text-primary)' }}>
                  Duplicate Collision Inspection
                </h3>
                <span
                  style={{
                    padding: '2px 8px',
                    borderRadius: '999px',
                    fontSize: '0.75rem',
                    fontWeight: 700,
                    background: similarityPercent >= 85 ? 'rgba(239, 68, 68, 0.12)' : 'rgba(245, 158, 11, 0.12)',
                    color: similarityPercent >= 85 ? 'var(--status-danger)' : 'var(--status-warning, #f59e0b)',
                    border: similarityPercent >= 85 ? '1px solid rgba(239, 68, 68, 0.25)' : '1px solid rgba(245, 158, 11, 0.25)'
                  }}
                >
                  {similarityPercent}% Similarity Match
                </span>
              </div>
              <p style={{ margin: '2px 0 0 0', fontSize: '0.775rem', color: 'var(--text-secondary)' }}>
                {dupInfo.match_reason || 'Candidate question exhibits substantial conceptual and textual overlap with an existing question in the bank.'}
              </p>
            </div>
          </div>

          <button
            onClick={onClose}
            aria-label="Close modal"
            style={{
              background: 'transparent',
              border: 'none',
              color: 'var(--text-muted)',
              cursor: 'pointer',
              padding: '6px',
              borderRadius: 'var(--radius-xs)',
              display: 'flex'
            }}
          >
            <X size={18} />
          </button>
        </div>

        {/* Side-by-side Diff Body */}
        <div
          style={{
            padding: '20px',
            overflowY: 'auto',
            flex: 1,
            display: 'grid',
            gridTemplateColumns: '1fr 1fr',
            gap: '16px',
            background: 'var(--bg-canvas)'
          }}
        >
          {/* Left Column: Candidate Question */}
          <div
            style={{
              background: 'var(--bg-surface)',
              borderRadius: 'var(--radius-sm)',
              border: '1px solid var(--border-light)',
              padding: '16px',
              display: 'flex',
              flexDirection: 'column',
              gap: '12px'
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <span className="badge badge-indigo" style={{ fontSize: '0.725rem', fontWeight: 600 }}>
                Candidate Question (Staged)
              </span>
              <span className="badge badge-emerald" style={{ fontSize: '0.725rem' }}>
                Score: {candidateQuestion.final_score || 95}/100
              </span>
            </div>

            <div>
              <div style={{ fontSize: '0.7rem', fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: '4px' }}>
                Question Prompt
              </div>
              <div style={{ fontSize: '0.85rem', color: 'var(--text-primary)', fontWeight: 600, lineHeight: 1.45 }}>
                {candidateQuestion.question_stem}
              </div>
            </div>

            <div>
              <div style={{ fontSize: '0.7rem', fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: '6px' }}>
                Choices
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                {candidateOptions.map((opt) => {
                  const isCorrect = candidateCorrectKeys.includes(String(opt.id).toUpperCase());
                  return (
                    <div
                      key={opt.id}
                      style={{
                        padding: '6px 10px',
                        borderRadius: 'var(--radius-xs)',
                        background: isCorrect ? 'rgba(16, 185, 129, 0.08)' : 'var(--bg-canvas)',
                        border: isCorrect ? '1px solid rgba(16, 185, 129, 0.4)' : '1px solid var(--border-light)',
                        display: 'flex',
                        alignItems: 'center',
                        gap: '8px',
                        fontSize: '0.8rem'
                      }}
                    >
                      <span
                        style={{
                          fontWeight: 700,
                          fontSize: '0.75rem',
                          color: isCorrect ? 'var(--status-success)' : 'var(--text-muted)',
                          width: '16px'
                        }}
                      >
                        {opt.id}
                      </span>
                      <span style={{ color: isCorrect ? 'var(--status-success)' : 'var(--text-secondary)', flex: 1 }}>
                        {opt.text}
                      </span>
                      {isCorrect && <Check size={13} color="var(--status-success)" strokeWidth={2.5} />}
                    </div>
                  );
                })}
              </div>
            </div>

            {candidateQuestion.explanation && (
              <div>
                <div style={{ fontSize: '0.7rem', fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: '4px' }}>
                  Pedagogical Explanation
                </div>
                <div
                  style={{
                    fontSize: '0.75rem',
                    color: 'var(--text-secondary)',
                    lineHeight: 1.45,
                    background: 'var(--bg-surface-subtle)',
                    padding: '8px 10px',
                    borderRadius: 'var(--radius-xs)'
                  }}
                >
                  {candidateQuestion.explanation}
                </div>
              </div>
            )}
          </div>

          {/* Right Column: Existing Question in Bank */}
          <div
            style={{
              background: 'var(--bg-surface)',
              borderRadius: 'var(--radius-sm)',
              border: '1px solid rgba(245, 158, 11, 0.3)',
              padding: '16px',
              display: 'flex',
              flexDirection: 'column',
              gap: '12px'
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <span className="badge badge-purple" style={{ fontSize: '0.725rem', fontWeight: 600 }}>
                Existing Bank Question
              </span>
              {dupInfo.matched_question_id && (
                <span style={{ fontSize: '0.725rem', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
                  ID: {dupInfo.matched_question_id.slice(0, 10)}...
                </span>
              )}
            </div>

            <div>
              <div style={{ fontSize: '0.7rem', fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: '4px' }}>
                Question Prompt
              </div>
              <div style={{ fontSize: '0.85rem', color: 'var(--text-primary)', fontWeight: 600, lineHeight: 1.45 }}>
                {dupInfo.matched_question_stem || '(Question text unavailable)'}
              </div>
            </div>

            <div>
              <div style={{ fontSize: '0.7rem', fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: '6px' }}>
                Choices
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                {matchedOptions.length > 0 ? (
                  matchedOptions.map((opt, i) => (
                    <div
                      key={opt.id || i}
                      style={{
                        padding: '6px 10px',
                        borderRadius: 'var(--radius-xs)',
                        background: 'var(--bg-canvas)',
                        border: '1px solid var(--border-light)',
                        display: 'flex',
                        alignItems: 'center',
                        gap: '8px',
                        fontSize: '0.8rem'
                      }}
                    >
                      <span style={{ fontWeight: 700, fontSize: '0.75rem', color: 'var(--text-muted)', width: '16px' }}>
                        {opt.id || String.fromCharCode(65 + i)}
                      </span>
                      <span style={{ color: 'var(--text-secondary)', flex: 1 }}>
                        {opt.text}
                      </span>
                    </div>
                  ))
                ) : (
                  <div style={{ fontSize: '0.775rem', color: 'var(--text-muted)', fontStyle: 'italic', padding: '6px 0' }}>
                    Options evaluated from database record.
                  </div>
                )}
              </div>
            </div>

            {dupInfo.matched_explanation && (
              <div>
                <div style={{ fontSize: '0.7rem', fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: '4px' }}>
                  Existing Explanation
                </div>
                <div
                  style={{
                    fontSize: '0.75rem',
                    color: 'var(--text-secondary)',
                    lineHeight: 1.45,
                    background: 'var(--bg-surface-subtle)',
                    padding: '8px 10px',
                    borderRadius: 'var(--radius-xs)'
                  }}
                >
                  {dupInfo.matched_explanation}
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Footer Actions */}
        <div
          style={{
            padding: '14px 20px',
            borderTop: '1px solid var(--border-light)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            background: 'var(--bg-surface)',
            flexWrap: 'wrap',
            gap: '10px'
          }}
        >
          <button
            type="button"
            onClick={handleDiscard}
            className="btn-secondary"
            style={{
              color: 'var(--status-danger)',
              borderColor: 'rgba(239, 68, 68, 0.3)',
              gap: '6px',
              fontSize: '0.8rem'
            }}
          >
            <Trash2 size={14} />
            <span>Discard Candidate</span>
          </button>

          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <button
              type="button"
              onClick={onClose}
              className="btn-secondary"
              style={{ fontSize: '0.8rem' }}
            >
              Cancel
            </button>

            {onRegenerate && (
              <button
                type="button"
                onClick={handleRegenerate}
                disabled={isSubmitting}
                className="btn-secondary"
                style={{
                  gap: '6px',
                  fontSize: '0.8rem',
                  borderColor: 'var(--brand-primary)',
                  color: 'var(--brand-primary)'
                }}
              >
                <RotateCcw size={14} />
                <span>Regenerate Fresh Angle</span>
              </button>
            )}

            <button
              type="button"
              onClick={handleOverride}
              disabled={isSubmitting}
              className="btn-primary"
              style={{
                gap: '6px',
                fontSize: '0.8rem',
                background: 'var(--status-warning, #f59e0b)',
                borderColor: 'var(--status-warning, #f59e0b)',
                color: 'var(--text-on-brand, #ffffff)'
              }}
              title="Accept question despite similarity, logging an override audit record in Question Bank"
            >
              <ShieldCheck size={14} />
              <span>{isSubmitting ? 'Approving...' : 'Override & Approve'}</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
