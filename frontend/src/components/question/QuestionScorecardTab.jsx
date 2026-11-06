
/**
 * QuestionScorecardTab:
 * Renders the 100-point psychometric rubric breakdown tab, displaying
 * the overall quality score and four pillar metric progress bars.
 *
 * Props:
 * - question: object - The question instance containing final_score and review_rubric
 * - pillars: Array<{ label: string, score: number | null, max: number, color: string }>
 */
import PillarBars from './PillarBars';
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

      <PillarBars pillars={pillars} compact />
    </div>
  );
}
