import { Layers, Zap, ShieldCheck } from 'lucide-react';

const EMPTY_BATCHES = [];

export default function BatchStatsHeader({ batches = EMPTY_BATCHES, activeCount = 0 }) {
  const totalQuestionsAuthored = batches.reduce((acc, b) => acc + (b.actual_count || 0), 0);

  return (
    <div
      style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
        gap: '12px'
      }}
    >
      <div
        style={{
          background: 'var(--bg-surface)',
          border: '1px solid var(--border-light)',
          borderRadius: 'var(--radius-sm)',
          padding: '12px 16px',
          display: 'flex',
          alignItems: 'center',
          gap: '12px'
        }}
      >
        <div
          style={{
            width: '32px',
            height: '32px',
            borderRadius: 'var(--radius-xs)',
            background: 'rgba(79, 48, 185, 0.08)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: 'var(--brand-primary)'
          }}
        >
          <Layers size={16} />
        </div>
        <div>
          <div style={{ fontSize: '1.25rem', fontWeight: 700, color: 'var(--text-primary)', lineHeight: 1.1 }}>
            {batches.length}
          </div>
          <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', marginTop: '2px' }}>
            Total Practice Batches
          </div>
        </div>
      </div>

      <div
        style={{
          background: 'var(--bg-surface)',
          border: '1px solid var(--border-light)',
          borderRadius: 'var(--radius-sm)',
          padding: '12px 16px',
          display: 'flex',
          alignItems: 'center',
          gap: '12px'
        }}
      >
        <div
          style={{
            width: '32px',
            height: '32px',
            borderRadius: 'var(--radius-xs)',
            background: 'rgba(51, 90, 207, 0.08)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: 'var(--infynno-blue)'
          }}
        >
          <Zap size={16} />
        </div>
        <div>
          <div
            style={{
              fontSize: '1.25rem',
              fontWeight: 700,
              color: activeCount > 0 ? 'var(--infynno-cyan)' : 'var(--text-primary)',
              lineHeight: 1.1
            }}
          >
            {activeCount}
          </div>
          <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', marginTop: '2px' }}>
            Currently Generating
          </div>
        </div>
      </div>

      <div
        style={{
          background: 'var(--bg-surface)',
          border: '1px solid var(--border-light)',
          borderRadius: 'var(--radius-sm)',
          padding: '12px 16px',
          display: 'flex',
          alignItems: 'center',
          gap: '12px'
        }}
      >
        <div
          style={{
            width: '32px',
            height: '32px',
            borderRadius: 'var(--radius-xs)',
            background: 'rgba(16, 185, 129, 0.08)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: 'var(--status-success)'
          }}
        >
          <ShieldCheck size={16} />
        </div>
        <div>
          <div style={{ fontSize: '1.25rem', fontWeight: 700, color: 'var(--text-primary)', lineHeight: 1.1 }}>
            {totalQuestionsAuthored}
          </div>
          <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', marginTop: '2px' }}>
            Total Questions Created
          </div>
        </div>
      </div>
    </div>
  );
}
