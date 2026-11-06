/**
 * The four quality pillars as labelled progress bars. `compact` is the dense card layout used
 * inside the question scorecard tab; the default is the audit dialog's two-column grid.
 */
import { EMPTY_ARRAY } from '../../constants';

export default function PillarBars({ pillars = EMPTY_ARRAY, compact = false }) {
  return (
    <div className={`pillar-grid ${compact ? 'compact' : ''}`}>
      {pillars.map((p) => (
        <div key={p.label} className={`pillar-card ${compact ? 'compact' : ''}`}>
          <div className="pillar-row">
            <span className="pillar-label">{p.label}</span>
            <span className="pillar-score" style={{ color: p.color }}>
              {p.score ?? 'N/A'} / {p.max}
            </span>
          </div>
          <div className="pillar-track">
            <div
              className="pillar-fill"
              style={{ width: `${((p.score ?? 0) / p.max) * 100}%`, background: p.color }}
            />
          </div>
        </div>
      ))}
    </div>
  );
}
