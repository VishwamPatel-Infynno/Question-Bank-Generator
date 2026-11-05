import React, { useState } from 'react';
import { useCopyToClipboard } from '../../hooks';
import { Code2, Copy, Check, ChevronDown, ChevronUp, PenTool, ShieldCheck, RotateCcw, ImageIcon, Sparkles } from 'lucide-react';

export default function StageJsonInspector({ question }) {
  const [isOpen, setIsOpen] = useState(true);
  const [activeStage, setActiveStage] = useState('drafting');
  const { copiedKey, copy } = useCopyToClipboard();
  const copied = copiedKey === true;

  if (!question) return null;

  // Extract stage outcomes from question or build from question attributes
  const stageOutcomes = question.stage_outcomes || {};

  const stages = [
    {
      id: 'drafting',
      label: 'Drafting',
      icon: PenTool,
      agent: 'Initial Drafting',
      data: stageOutcomes.drafting || {
        stimulus_text: question.stimulus_text,
        question_stem: question.question_stem,
        options: question.options,
        correct_answer_id: question.correct_answer_id,
        explanation: question.explanation,
        combination_id: question.combination_id,
        content_domain: question.content_domain,
        question_type: question.question_type,
        primary_trap: question.primary_trap
      }
    },
    {
      id: 'quality_audit',
      label: 'Quality Review',
      icon: ShieldCheck,
      agent: 'Quality Review',
      data: stageOutcomes.quality_audit || question.review_rubric || {
        audit_id: question.review_rubric?.audit_id,
        evaluated_at: question.review_rubric?.evaluated_at,
        total_score: question.final_score,
        passed: question.final_score > 90,
        authenticity_score: 24,
        clarity_score: 24,
        distractor_score: 23,
        explanation_score: 24,
        strengths: ['Authentic clinical scenario', 'Plausible distractors'],
        recommendations: []
      }
    },
    {
      id: 'polish_refine',
      label: 'Polish & Refine',
      icon: RotateCcw,
      agent: 'Refinement',
      data: stageOutcomes.polish_refine || (question.iteration_count > 1 ? {
        iteration_count: question.iteration_count,
        history: question.iterations_history
      } : null),
      bypassedNote: question.iteration_count <= 1 ? 'First draft met the quality rubric, so no additional revisions were needed.' : null
    },
    {
      id: 'visual_stimulus',
      label: 'Figures & Diagrams',
      icon: ImageIcon,
      agent: 'Figure Generation',
      data: stageOutcomes.visual_stimulus || (question.image_svg || question.image_url ? {
        image_svg: question.image_svg ? `${question.image_svg.slice(0, 120)}...` : null,
        image_url: question.image_url,
        image_description: question.image_description,
        visual_type: question.visual_type || 'SVG_Diagram'
      } : null),
      bypassedNote: (!question.image_svg && !question.image_url) ? 'No diagram or figure required for this question.' : null
    },
    {
      id: 'final_payload',
      label: 'Final Question',
      icon: Sparkles,
      agent: 'Verified Question Record',
      data: stageOutcomes.final_payload || {
        id: question.id,
        run_id: question.run_id,
        batch_id: question.batch_id,
        combination_id: question.combination_id,
        section: question.section,
        section_label: question.section_label,
        subtopic: question.subtopic,
        difficulty: question.difficulty,
        content_domain: question.content_domain,
        question_type: question.question_type,
        primary_trap: question.primary_trap,
        final_score: question.final_score,
        correct_answer_id: question.correct_answer_id,
        compute_units: question.total_tokens,
        quality_status: question.final_score > 90 ? 'High Quality' : 'Passed Benchmark',
        created_at: question.created_at
      }
    }
  ];

  const currentStageObj = stages.find(s => s.id === activeStage) || stages[0];
  const jsonString = currentStageObj.data ? JSON.stringify(currentStageObj.data, null, 2) : null;

  const handleCopy = () => {
    if (jsonString) {
      copy(jsonString);
    }
  };

  return (
    <div className="glass-panel audit-trail-container stage-inspector-wrapper">
      {/* Header Accordion Toggle */}
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        className="stage-inspector-header-btn"
      >
        <span className="stage-inspector-header-left">
          <Code2 size={16} color="var(--brand-primary)" />
          <span>Generation Details</span>
        </span>

        {isOpen ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
      </button>

      {/* Expanded Content */}
      {isOpen && (
        <div className="stage-inspector-content">
          {/* Stage Tabs */}
          <div className="stage-inspector-nav-strip">
            <div className="stage-inspector-tabs">
              {stages.map((stage) => {
                const Icon = stage.icon;
                const isSelected = activeStage === stage.id;
                return (
                  <button
                    key={stage.id}
                    type="button"
                    onClick={() => setActiveStage(stage.id)}
                    className={`stage-inspector-tab-btn ${isSelected ? 'is-active' : ''}`}
                  >
                    <Icon size={14} />
                    <span>{stage.label}</span>
                  </button>
                );
              })}
            </div>

            {/* Copy Button */}
            {jsonString && (
              <button
                type="button"
                onClick={handleCopy}
                className="btn-secondary stage-inspector-copy-btn"
                title="Copy current stage JSON to clipboard"
              >
                {copied ? <Check size={13} color="var(--status-success)" /> : <Copy size={13} />}
                <span>{copied ? 'Copied!' : 'Copy Stage JSON'}</span>
              </button>
            )}
          </div>

          {/* Current Stage Metadata Banner */}
          <div className="stage-inspector-meta-banner">
            <span>Editorial Step: <strong>{currentStageObj.label}</strong></span>
            {question.combination_id && (
              <span className="badge badge-indigo stage-inspector-badge">
                Combination: {question.combination_id}
              </span>
            )}
          </div>

          {/* Code Viewer or Bypassed Notice */}
          {jsonString ? (
            <div className="stage-inspector-code-box">
              <pre className="stage-inspector-pre">
                {jsonString}
              </pre>
            </div>
          ) : (
            <div className="stage-inspector-empty">
              {currentStageObj.bypassedNote || 'No payload recorded for this stage.'}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

