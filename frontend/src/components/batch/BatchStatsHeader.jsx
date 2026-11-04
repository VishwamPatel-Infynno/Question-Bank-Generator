import { Layers, Zap, ShieldCheck } from 'lucide-react';

const EMPTY_BATCHES = [];

export default function BatchStatsHeader({ batches = EMPTY_BATCHES, activeCount = 0 }) {
  const totalQuestionsAuthored = batches.reduce((acc, b) => acc + (b.actual_count || 0), 0);

  return (
    <div className="batch-stats-grid">
      <div className="batch-stat-card">
        <div className="batch-stat-icon-box brand">
          <Layers size={16} />
        </div>
        <div>
          <div className="batch-stat-value">
            {batches.length}
          </div>
          <div className="batch-stat-label">
            Total Practice Batches
          </div>
        </div>
      </div>

      <div className="batch-stat-card">
        <div className="batch-stat-icon-box blue">
          <Zap size={16} />
        </div>
        <div>
          <div className={`batch-stat-value ${activeCount > 0 ? 'active' : ''}`}>
            {activeCount}
          </div>
          <div className="batch-stat-label">
            Currently Generating
          </div>
        </div>
      </div>

      <div className="batch-stat-card">
        <div className="batch-stat-icon-box success">
          <ShieldCheck size={16} />
        </div>
        <div>
          <div className="batch-stat-value">
            {totalQuestionsAuthored}
          </div>
          <div className="batch-stat-label">
            Total Questions Created
          </div>
        </div>
      </div>
    </div>
  );
}
