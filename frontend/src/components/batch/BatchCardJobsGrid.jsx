import { memo } from 'react';
import { Layers } from 'lucide-react';
import BatchJobCard from './BatchJobCard';

const EMPTY_JOB_IDS = {};

function BatchCardJobsGrid({
  detail,
  loadingDetail,
  expandedJobIds = EMPTY_JOB_IDS,
  onToggleJob,
  onNavigateToBank,
  onNavigateToValidated,
  onOpenAudit,
  onSaveToBank,
  onRestoreQuestion
}) {
  return (
    <div style={{ padding: '20px', background: 'var(--bg-canvas)' }}>
      {loadingDetail && !detail ? (
        <div
          style={{
            textAlign: 'center',
            padding: '30px',
            color: 'var(--text-muted)'
          }}
        >
          <div
            style={{
              width: '22px',
              height: '22px',
              border: '2px solid var(--border-medium)',
              borderTopColor: 'var(--brand-primary)',
              borderRadius: '50%',
              animation: 'spin 0.8s linear infinite',
              margin: '0 auto 8px'
            }}
          />
          <span style={{ fontSize: '0.8rem' }}>Loading question sets...</span>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between'
            }}
          >
            <div
              style={{
                fontSize: '0.825rem',
                fontWeight: 700,
                color: 'var(--text-primary)',
                display: 'flex',
                alignItems: 'center',
                gap: '8px'
              }}
            >
              <Layers size={15} style={{ color: 'var(--brand-primary)' }} />
              <span>
                Question Sets ({detail?.jobs?.length || 0} sets &bull; 5 questions each):
              </span>
            </div>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
              Generating sets in parallel
            </div>
          </div>

          {/* Jobs Grid */}
          {!detail?.jobs || detail.jobs.length === 0 ? (
            <div
              style={{
                textAlign: 'center',
                padding: '24px',
                color: 'var(--text-muted)',
                fontSize: '0.8rem',
                background: 'var(--bg-surface)',
                borderRadius: 'var(--radius-sm)',
                border: '1px dashed var(--border-medium)'
              }}
            >
              No question sets recorded for this practice batch.
            </div>
          ) : (
            <div
              style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))',
                gap: '12px'
              }}
            >
              {detail.jobs.map((job) => (
                <BatchJobCard
                  key={job.id}
                  job={job}
                  isExpanded={Boolean(expandedJobIds[job.id])}
                  onToggleExpand={onToggleJob}
                  onNavigateToBank={onNavigateToBank}
                  onNavigateToValidated={onNavigateToValidated}
                  onOpenAudit={onOpenAudit}
                  onSaveToBank={onSaveToBank}
                  onRestoreQuestion={onRestoreQuestion}
                />
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default memo(BatchCardJobsGrid);

