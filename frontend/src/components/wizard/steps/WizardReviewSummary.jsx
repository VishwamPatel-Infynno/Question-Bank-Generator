import { Edit3 } from 'lucide-react';

/**
 * WizardReviewSummary
 *
 * Summary card grid displaying current generation parameters (Section, Focus, Difficulty, Format, Count)
 * with quick-jump edit buttons back to corresponding wizard steps.
 */
export default function WizardReviewSummary({
  sectionLabel,
  topicLabel,
  diffLabel,
  formatSummary,
  totalQuestions,
  setStep
}) {
  return (
    <div className="wizard-review-card">
      <div className="wizard-review-grid">
        {/* Section */}
        <div className="wizard-review-cell">
          <div className="wizard-review-cell-header">
            <span className="wizard-review-cell-title">Section</span>
            <button
              type="button"
              onClick={() => setStep(1)}
              className="wizard-review-cell-edit-btn"
              title="Edit Section"
            >
              <Edit3 size={12} />
            </button>
          </div>
          <div className="wizard-review-cell-value">
            {sectionLabel}
          </div>
        </div>

        {/* Focus */}
        <div className="wizard-review-cell">
          <div className="wizard-review-cell-header">
            <span className="wizard-review-cell-title">Topic Focus</span>
            <button
              type="button"
              onClick={() => setStep(1)}
              className="wizard-review-cell-edit-btn"
              title="Edit Topic"
            >
              <Edit3 size={12} />
            </button>
          </div>
          <div className="wizard-review-cell-value">
            {topicLabel}
          </div>
        </div>

        {/* Difficulty */}
        <div className="wizard-review-cell">
          <div className="wizard-review-cell-header">
            <span className="wizard-review-cell-title">Difficulty</span>
            <button
              type="button"
              onClick={() => setStep(2)}
              className="wizard-review-cell-edit-btn"
              title="Edit Difficulty"
            >
              <Edit3 size={12} />
            </button>
          </div>
          <div className="wizard-review-cell-value">
            {diffLabel}
          </div>
        </div>

        {/* Format */}
        <div className="wizard-review-cell">
          <div className="wizard-review-cell-header">
            <span className="wizard-review-cell-title">Format</span>
            <button
              type="button"
              onClick={() => setStep(2)}
              className="wizard-review-cell-edit-btn"
              title="Edit Format"
            >
              <Edit3 size={12} />
            </button>
          </div>
          <div className="wizard-review-cell-value">
            {formatSummary}
          </div>
        </div>

        {/* Count */}
        <div className="wizard-review-cell">
          <div className="wizard-review-cell-header">
            <span className="wizard-review-cell-title">Questions</span>
            <button
              type="button"
              onClick={() => setStep(2)}
              className="wizard-review-cell-edit-btn"
              title="Edit Count"
            >
              <Edit3 size={12} />
            </button>
          </div>
          <div className="wizard-review-cell-value">
            {totalQuestions} Questions
          </div>
        </div>
      </div>
    </div>
  );
}
