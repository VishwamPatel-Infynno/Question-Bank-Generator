import { useState, useEffect } from 'react';
import { CheckCircle, AlertTriangle, ShieldCheck, Sparkles, Target, Zap, Image as ImageIcon } from 'lucide-react';
import { Modal } from '../common';
import PillarBars from './PillarBars';
import AuditMetricsGrid from './AuditMetricsGrid';
import AuditStageBreakdown from './AuditStageBreakdown';
import AuditIterationTimeline from './AuditIterationTimeline';
import {
  getEffectiveTrapInfo,
  formatTokenCount,
  formatCostUsd,
  getAuditCostBreakdown,
  getReviewPillars
} from '../../utils';
import { SCORE_CUTOFFS } from '../../constants';
import { fetchQuestionById } from '../../services';

/**
 * ReviewAuditView
 *
 * Detailed quality, token cost, and exam calibration modal for a question.
 * Built on the unified Modal primitive with WCAG AA compliance.
 */
export default function ReviewAuditView({ question: initialQuestion, onClose }) {
  const [hydratedQuestion, setHydratedQuestion] = useState(null);

  const initialId = initialQuestion?.id;
  const hasHistory = Boolean(initialQuestion?.iterations_history?.length);
  const hasStages = Boolean(initialQuestion?.stage_outcomes);

  useEffect(() => {
    let isCancelled = false;
    if (initialId && (!hasHistory || !hasStages)) {
      fetchQuestionById(initialId)
        .then((fullQ) => {
          if (!isCancelled && fullQ) {
            setHydratedQuestion(fullQ);
          }
        })
        .catch((err) => {
          console.warn('Could not hydrate full audit diagnostics:', err);
        });
    }
    return () => {
      isCancelled = true;
    };
  }, [initialId, hasHistory, hasStages]);

  const question = hydratedQuestion || initialQuestion;

  if (!question) return null;

  const review = question.review_rubric;
  const history = question.iterations_history || [];
  const trapInfo = getEffectiveTrapInfo(question);
  const mistakePattern = question.likely_mistake_pattern && question.likely_mistake_pattern !== 'None'
    ? question.likely_mistake_pattern
    : null;
  const { hasVisual, totalCost, visualCost, cognitiveCost, stageTimings, totalDurationMs } =
    getAuditCostBreakdown(question);
  const isHighQuality = question.final_score > SCORE_CUTOFFS.passingAbove;
  const metrics = [
    { label: 'INPUT TOKENS', tone: 'brand', value: formatTokenCount(question.prompt_tokens) },
    { label: 'OUTPUT TOKENS', tone: 'indigo', value: formatTokenCount(question.completion_tokens) },
    { label: 'TOTAL TOKENS', tone: 'primary', value: formatTokenCount(question.total_tokens) },
    { label: 'GENERATION COST', tone: 'success', value: formatCostUsd(totalCost) },
    {
      label: 'QUALITY STATUS',
      tone: isHighQuality ? 'success' : 'warning',
      value: isHighQuality ? 'High Quality' : 'Needs Polish'
    }
  ];

  const pillars = getReviewPillars(review);

  const iconElement = (
    <div className="audit-header-icon">
      <ShieldCheck size={20} />
    </div>
  );

  const footer = (
    <button type="button" onClick={onClose} className="btn-secondary">
      Close Review
    </button>
  );

  return (
    <Modal
      isOpen={Boolean(question)}
      onClose={onClose}
      title="Quality Review"
      icon={iconElement}
      maxWidth="820px"
      footer={footer}
    >
      <div className="audit-modal-body">
        {/* Overall Score Banner */}
        <div className="audit-score-banner">
          <div>
            <div className="audit-score-label">Score</div>
            <div className="audit-score-value">
              {question.final_score} <span className="audit-score-max">/ 100</span>
            </div>
          </div>
          <div className="audit-score-right">
            <span
              className={`badge ${question.final_score > SCORE_CUTOFFS.passingAbove ? 'badge-emerald' : 'badge-amber'} audit-score-badge`}
            >
              {isHighQuality ? 'Passed' : 'Needs Polish'}
            </span>
            <div className="audit-rounds-label">
              Rounds: {question.iteration_count || 1}
            </div>
          </div>
        </div>

        {/* Usage & Cost Details Section */}
        <div className="audit-section-block">
          <div className="audit-section-header">
            <h4 className="audit-section-title">
              Usage Details
            </h4>
            <span className="audit-section-subtitle">
              Quality Review Summary
            </span>
          </div>

          {/* Metric Cards Grid */}
          <AuditMetricsGrid metrics={metrics} />

          {/* Engine & Latency Stage Breakdown */}
          <AuditStageBreakdown
            totalCost={totalCost}
            cognitiveCost={cognitiveCost}
            visualCost={visualCost}
            hasVisual={hasVisual}
            totalTokens={question.total_tokens}
            stageTimings={stageTimings}
            totalDurationMs={totalDurationMs}
          />
        </div>

        {/* 4 Pillars Breakdown */}
        <div className="audit-section-block gap-12">
          <h4 className="audit-section-title">
            Quality Pillars (100 Points Total)
          </h4>
          <PillarBars pillars={pillars} />
        </div>

        {/* Cognitive & Pedagogical Calibration */}
        <div className="audit-section-block gap-12">
          <div className="audit-section-header">
            <h4 className="audit-section-title">
              Exam Accuracy &amp; Question Design
            </h4>
            <span className="audit-section-subtitle">
              Question Trap Analysis &amp; Student Misconceptions
            </span>
          </div>

          <div className="audit-calibration-grid">
            {/* Primary Trap */}
            <div className="audit-calibration-card">
              <div className="audit-card-top">
                <span className="audit-card-category-label">
                  <Zap size={13} className="audit-trap-icon" />
                  Common Trap Tested
                </span>
                <span className="badge badge-purple audit-tag-badge">
                  <Sparkles size={11} /> Trap Breakdown
                </span>
              </div>
              <div className="audit-card-title">
                {trapInfo?.label || 'Direct Conceptual Application'}
              </div>
              <p className="audit-card-desc">
                {trapInfo?.advice || 'Evaluates direct conceptual understanding without deceptive distractor skew.'}
              </p>
            </div>

            {/* Target Misconception */}
            <div className="audit-calibration-card">
              <div className="audit-card-top">
                <span className="audit-card-category-label">
                  <Target size={13} className="audit-mistake-icon" />
                  Common Student Mistake
                </span>
                <span className="badge badge-cyan audit-tag-badge">
                  <Sparkles size={11} /> Common Mistake
                </span>
              </div>
              <div className="audit-card-title">
                {mistakePattern ? mistakePattern.replace(/_/g, ' ') : 'None Diagnosed (Clean Distractor)'}
              </div>
              <p className="audit-card-desc">
                {mistakePattern
                  ? 'Incorrect choices were specifically crafted to highlight this common conceptual mistake.'
                  : 'Incorrect choices test fundamental science concepts without relying on a specific trick.'}
              </p>
            </div>
          </div>

          {/* Visual Stimulus Evaluation */}
          <div className="audit-figure-card">
            <div className="audit-figure-left">
              <div className={`audit-figure-icon ${hasVisual ? 'has-visual' : 'no-visual'}`}>
                <ImageIcon size={16} />
              </div>
              <div>
                <div className="audit-figure-title">
                  Figure Review: {hasVisual ? 'Diagram Generated & Attached' : 'Text-Only Question (No Diagram Needed)'}
                </div>
                <div className="audit-figure-subtitle">
                  {hasVisual
                    ? (question.image_description || 'Custom biomedical or physical sciences diagram rendered to accompany item stem.')
                    : 'The question stem and passage provide all necessary context without needing a diagram.'}
                </div>
              </div>
            </div>
            <span className={`badge ${hasVisual ? 'badge-cyan' : 'badge-neutral'} audit-figure-badge`}>
              {hasVisual ? 'Diagram Attached' : 'Text Only'}
            </span>
          </div>
        </div>

        {/* Strengths & Deficiencies */}
        {review && (
          <div className="audit-feedback-grid">
            {/* Strengths */}
            <div className="audit-strengths-card">
              <div className="audit-feedback-header-success">
                <CheckCircle size={16} /> Question Strengths
              </div>
              <ul className="audit-feedback-list">
                {review.strengths?.length > 0 ? (
                  review.strengths.map((s) => <li key={s}>{s}</li>)
                ) : (
                  <li>Consistent authentic formatting adhered to.</li>
                )}
              </ul>
            </div>

            {/* Recommendations / Remediation */}
            <div className="audit-suggestions-card">
              <div className="audit-feedback-header-warning">
                <AlertTriangle size={16} /> Suggestions for Polish
              </div>
              <ul className="audit-feedback-list">
                {review.recommendations?.length > 0 ? (
                  review.recommendations.map((r) => <li key={r}>{r}</li>)
                ) : (
                  <li>Draft scored high and is ready for your Question Bank.</li>
                )}
              </ul>
            </div>
          </div>
        )}

        {/* Iterations Evolution Timeline */}
        <AuditIterationTimeline history={history} />
      </div>
    </Modal>
  );
}
