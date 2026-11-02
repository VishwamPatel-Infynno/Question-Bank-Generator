import React from 'react';
import { ShieldCheck, RefreshCw, Database } from 'lucide-react';

const EMPTY_COUNTS = {};

export default function AiValidatedStatsBar({
  counts = EMPTY_COUNTS,
  questionsCount = 0,
  refreshing = false,
  onRefresh,
  onNavigateToBank
}) {
  return (
    <div
      style={{
        background: 'var(--bg-surface)',
        border: '1px solid var(--border-light)',
        borderRadius: 'var(--radius-sm)',
        padding: '14px 18px',
        display: 'flex',
        flexDirection: 'column',
        gap: '12px'
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '16px', flexWrap: 'wrap' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <div
              style={{
                width: '24px',
                height: '24px',
                borderRadius: 'var(--radius-xs)',
                background: 'rgba(16, 185, 129, 0.12)',
                color: 'var(--status-success)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center'
              }}
            >
              <ShieldCheck size={15} />
            </div>
            <h2 style={{ fontSize: '1.1rem', fontWeight: 700, color: 'var(--text-primary)', margin: 0, letterSpacing: '-0.02em' }}>
              Review Queue
            </h2>
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <button
            type="button"
            onClick={onRefresh}
            disabled={refreshing}
            className="btn-secondary"
            style={{ display: 'flex', alignItems: 'center', gap: '6px', padding: '6px 12px', fontSize: '0.76rem' }}
            title="Refresh questions list"
          >
            <RefreshCw size={12} className={refreshing ? 'animate-spin' : ''} />
            <span>Refresh</span>
          </button>
          {onNavigateToBank && (
            <button
              type="button"
              onClick={onNavigateToBank}
              className="btn-secondary"
              style={{ display: 'flex', alignItems: 'center', gap: '6px', padding: '6px 12px', fontSize: '0.76rem' }}
            >
              <Database size={12} />
              <span>Question Bank</span>
            </button>
          )}
        </div>
      </div>

      {/* Quick Metrics Bar */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: '16px',
          flexWrap: 'wrap',
          paddingTop: '10px',
          borderTop: '1px solid var(--border-light)',
          fontSize: '0.75rem'
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          <span style={{ color: 'var(--text-muted)' }}>Ready for Review:</span>
          <strong style={{ fontWeight: 700, color: 'var(--status-success)' }}>
            {counts.ai_validated || questionsCount}
          </strong>
        </div>
        <span style={{ color: 'var(--border-light)' }}>•</span>
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          <span style={{ color: 'var(--text-muted)' }}>In Question Bank:</span>
          <strong style={{ fontWeight: 700, color: 'var(--brand-primary)' }}>
            {counts.in_bank || 0}
          </strong>
        </div>
        <span style={{ color: 'var(--border-light)' }}>•</span>
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          <span style={{ color: 'var(--text-muted)' }}>Good Quality (86-90):</span>
          <strong style={{ fontWeight: 700, color: 'var(--brand-indigo, #6366f1)' }}>
            {counts.batch_only || 0}
          </strong>
        </div>
        <span style={{ color: 'var(--border-light)' }}>•</span>
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          <span style={{ color: 'var(--text-muted)' }}>Discarded:</span>
          <strong style={{ fontWeight: 700, color: 'var(--text-muted)' }}>
            {counts.discarded || 0}
          </strong>
        </div>
        <span style={{ color: 'var(--border-light)' }}>•</span>
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          <span style={{ color: 'var(--text-muted)' }}>Needs Polish (&le;85):</span>
          <strong style={{ fontWeight: 700, color: 'var(--status-warning, #d97706)' }}>
            {counts.below_threshold || 0}
          </strong>
        </div>
      </div>
    </div>
  );
}
