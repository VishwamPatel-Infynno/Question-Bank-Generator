
/**
 * QuestionScorecardTab:
 * Renders the 100-point psychometric rubric breakdown tab, displaying
 * the overall quality score and four pillar metric progress bars.
 *
 * Props:
 * - question: object - The question instance containing final_score and review_rubric
 * - pillars: Array<{ label: string, score: number, max: number, color: string }>
 */
const EMPTY_PILLARS = [];

export default function QuestionScorecardTab({ question, pillars = EMPTY_PILLARS }) {
  if (!question) return null;

  return (
    <div className="scorecard-tab">
      <div className="scorecard-header">
        <div>
          <h4 className="scorecard-title">
            Quality Scorecard
          </h4>
        </div>
        <span className="badge badge-emerald scorecard-total-badge">
          Score: {question.final_score}/100
        </span>
      </div>

      <div className="scorecard-grid">
        {pillars.map(p => (
          <div
            key={p.label}
            className="scorecard-pillar-card"
          >
            <div className="scorecard-pillar-row">
              <span className="scorecard-pillar-label">{p.label}</span>
              <span className="scorecard-pillar-score" style={{ color: p.color }}>{p.score}/{p.max}</span>
            </div>
            <div className="scorecard-progress-track">
              <div
                className="scorecard-progress-fill"
                style={{ width: `${(p.score / p.max) * 100}%`, background: p.color }}
              />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
