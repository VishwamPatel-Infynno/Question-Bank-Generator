import React, { useState, useMemo } from 'react';
import { 
  ChevronDown, 
  ChevronUp, 
  HelpCircle,
  FileText,
  BarChart3,
  Code2
} from 'lucide-react';
import QuestionCardHeader from './QuestionCardHeader';
import QuestionOptionsList from './QuestionOptionsList';
import QuestionCardFooter from './QuestionCardFooter';
import StageJsonInspector from './StageJsonInspector';
import VisualStimulusViewer from './VisualStimulusViewer';
import MentorExplanationView from './MentorExplanationView';
import QuestionScorecardTab from './QuestionScorecardTab';
import QuestionInlineEditor from './QuestionInlineEditor';
import { getEffectiveTrapInfo, calculateOptionSymmetry } from '../../utils';

function QuestionCard({ 
  question, 
  isSaved = false, 
  onApprove, 
  onDiscard, 
  onOpenAudit, 
  onNextQuestion,
  onUpdateQuestion 
}) {
  const [activeTab, setActiveTab] = useState('preview'); // 'preview' | 'scorecard' | 'telemetry'
  const [showExplanation, setShowExplanation] = useState(true);
  const [isApproving, setIsApproving] = useState(false);

  // Quick Inline Edit Mode State
  const [isEditing, setIsEditing] = useState(false);
  const [editedStem, setEditedStem] = useState(question?.question_stem || '');
  const [editedStimulus, setEditedStimulus] = useState(question?.stimulus_text || '');
  const [editedOptions, setEditedOptions] = useState(question?.options || []);
  const [editedExplanation, setEditedExplanation] = useState(question?.explanation || '');
  const [editedImageDescription, setEditedImageDescription] = useState(question?.image_description || '');
  const [showStimulusField, setShowStimulusField] = useState(Boolean(question?.stimulus_text && question.stimulus_text.trim().length > 0));

  const effectiveTrapInfo = getEffectiveTrapInfo(question);

  const optionSymmetry = useMemo(() => {
    if (!question) return null;
    if (question.option_symmetry && Object.keys(question.option_symmetry).length > 0) {
      return question.option_symmetry;
    }
    if (question.stage_outcomes?.option_symmetry) {
      return question.stage_outcomes.option_symmetry;
    }
    const currentOptions = isEditing ? editedOptions : (question.options || []);
    return calculateOptionSymmetry(currentOptions);
  }, [question, isEditing, editedOptions]);

  const hasStimulus = Boolean(
    (question?.stimulus_text && question.stimulus_text.trim()) ||
    (isEditing && (showStimulusField || (editedStimulus && editedStimulus.trim())))
  );

  const hasImage = Boolean(
    question?.image_svg ||
    question?.image_url ||
    question?.stage_outcomes?.visual_stimulus?.image_svg ||
    question?.stage_outcomes?.visual_stimulus?.image_url ||
    question?.stage_outcomes?.passage_visual_stimulus?.image_svg ||
    question?.stage_outcomes?.passage_visual_stimulus?.image_url
  );

  if (!question) return null;

  const handleApproveClick = async () => {
    if (!onApprove || isApproving) return;
    setIsApproving(true);
    try {
      await onApprove(question);
    } finally {
      setIsApproving(false);
    }
  };

  const handleSaveEdit = () => {
    const updated = {
      ...question,
      question_stem: editedStem,
      stimulus_text: editedStimulus,
      options: editedOptions,
      explanation: editedExplanation,
      image_description: editedImageDescription
    };
    if (onUpdateQuestion) onUpdateQuestion(updated);
    setIsEditing(false);
  };

  const handleCancelEdit = () => {
    setEditedStem(question.question_stem);
    setEditedStimulus(question.stimulus_text || '');
    setEditedOptions(question.options || []);
    setEditedExplanation(question.explanation || '');
    setEditedImageDescription(question.image_description || '');
    setShowStimulusField(Boolean(question.stimulus_text && question.stimulus_text.trim().length > 0));
    setIsEditing(false);
  };

  const review = question.review_rubric;
  const pillars = [
    { label: 'MCAT Scientific Style & Tone', score: review?.authenticity_score ?? 24, max: 25, color: 'var(--brand-primary)' },
    { label: 'Clarity & Logic', score: review?.clarity_score ?? 24, max: 25, color: 'var(--brand-indigo)' },
    { label: 'Wrong Answer Quality', score: review?.distractor_score ?? 23, max: 25, color: 'var(--status-warning)' },
    { label: 'Explanation & Key Accuracy', score: review?.explanation_score ?? 24, max: 25, color: 'var(--status-success)' },
  ];

  const correctKeysList = Array.isArray(question.correct_answer_ids) && question.correct_answer_ids.length > 0
    ? question.correct_answer_ids.map(k => String(k).trim().toUpperCase())
    : (question.correct_answer_id || '').split(',').map(k => k.trim().toUpperCase()).filter(Boolean);

  return (
    <div
      className="glass-panel"
      style={{
        padding: '24px',
        display: 'flex',
        flexDirection: 'column',
        gap: '18px',
        position: 'relative'
      }}
    >
      {/* Top Header Metadata Strip */}
      <QuestionCardHeader
        question={question}
        isSaved={isSaved}
        hasImage={hasImage}
        effectiveTrapInfo={effectiveTrapInfo}
        onOpenAudit={onOpenAudit}
        isEditing={isEditing}
        onToggleEditing={() => setIsEditing(!isEditing)}
      />

      {/* Desk Tab Navigation */}
      <div className="pill-track">
        {[
          { id: 'preview', label: 'Question & Choices', icon: FileText },
          { id: 'scorecard', label: 'Quality Checklist', icon: BarChart3 },
          { id: 'telemetry', label: 'Generation Details & Cost', icon: Code2 }
        ].map(tab => {
          const Icon = tab.icon;
          const isSel = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`pill-track-btn ${isSel ? 'active' : ''}`}
            >
              <Icon size={12} />
              <span>{tab.label}</span>
            </button>
          );
        })}
      </div>

      {/* --- TAB 1: CANDIDATE PREVIEW --- */}
      {activeTab === 'preview' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          {/* Edit Mode Alert */}
          {isEditing && (
            <QuestionInlineEditor
              onSave={handleSaveEdit}
              onCancel={handleCancelEdit}
            />
          )}

          {/* Reading Passage (Stimulus) */}
          {((question.stimulus_text && question.stimulus_text.trim()) || (isEditing && (showStimulusField || (editedStimulus && editedStimulus.trim())))) ? (
            <div
              className="passage-editorial vignette-editorial"
              style={{
                display: 'flex',
                flexDirection: 'column',
                gap: '8px',
                border: '1px solid var(--border-light)',
                borderLeft: '3px solid var(--brand-primary)'
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <span style={{ fontSize: '0.7rem', fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.04em', fontFamily: 'var(--font-sans)' }}>
                  Reading Passage
                </span>
                <span style={{ fontSize: '0.675rem', color: 'var(--text-muted)', fontFamily: 'var(--font-sans)' }}>
                  ~{isEditing ? (editedStimulus ? editedStimulus.split(/\s+/).filter(Boolean).length : 0) : (question.stimulus_text ? question.stimulus_text.split(/\s+/).filter(Boolean).length : 0)} words
                </span>
              </div>

              {isEditing ? (
                <textarea
                  value={editedStimulus}
                  onChange={(e) => setEditedStimulus(e.target.value)}
                  rows={6}
                  placeholder="Enter optional reading passage or context..."
                  style={{ width: '100%', fontSize: '0.95rem', fontFamily: 'var(--font-serif)', lineHeight: 1.65 }}
                />
              ) : (
                <div
                  style={{
                    fontFamily: 'var(--font-serif)',
                    fontSize: '0.975rem',
                    lineHeight: '1.72',
                    color: 'var(--text-primary)',
                    whiteSpace: 'pre-line'
                  }}
                >
                  {question.stimulus_text}
                </div>
              )}

              {hasImage && (
                <div style={{ marginTop: '10px', borderTop: '1px solid var(--border-light)', paddingTop: '10px' }}>
                  <VisualStimulusViewer
                    question={question}
                    isEditing={isEditing}
                    editedDescription={editedImageDescription}
                    onDescriptionChange={setEditedImageDescription}
                  />
                </div>
              )}
            </div>
          ) : isEditing ? (
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <button
                type="button"
                onClick={() => setShowStimulusField(true)}
                className="btn-secondary"
                style={{ fontSize: '0.75rem', padding: '4px 10px', color: 'var(--text-secondary)' }}
              >
                + Add Reading Passage
              </button>
            </div>
          ) : null}

          {/* Visual Stimulus Diagram / Image for standalone questions (without passage) */}
          {!hasStimulus && hasImage && (
            <VisualStimulusViewer
              question={question}
              isEditing={isEditing}
              editedDescription={editedImageDescription}
              onDescriptionChange={setEditedImageDescription}
            />
          )}

          {/* Question Stem */}
          <div style={{ padding: '2px 4px' }}>
            {isEditing ? (
              <textarea
                value={editedStem}
                onChange={(e) => setEditedStem(e.target.value)}
                rows={2}
                style={{ width: '100%', fontSize: '1rem', fontWeight: 600 }}
              />
            ) : (
              <h3
                style={{
                  fontSize: '1rem',
                  fontWeight: 700,
                  lineHeight: '1.5',
                  color: 'var(--text-primary)'
                }}
              >
                {question.question_stem}
              </h3>
            )}
          </div>

          {/* Options List */}
          <QuestionOptionsList
            options={question.options}
            correctKeysList={correctKeysList}
            optionSymmetry={optionSymmetry}
            isEditing={isEditing}
            editedOptions={editedOptions}
            onEditedOptionsChange={setEditedOptions}
          />

          {/* Explanation Accordion Toggle */}
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', paddingTop: '4px' }}>
            <button
              type="button"
              className="btn-secondary"
              onClick={() => setShowExplanation(!showExplanation)}
              style={{ gap: '6px', fontSize: '0.775rem' }}
            >
              {showExplanation ? <ChevronUp size={13} /> : <ChevronDown size={13} />}
              <span>{showExplanation ? 'Hide Answer Explanations' : 'Why Each Choice is Right or Wrong'}</span>
            </button>

            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
              Correct Answer: <strong style={{ color: 'var(--status-success)' }}>Option {question.correct_answer_id}</strong>
            </span>
          </div>

          {/* Explanation Box */}
          {showExplanation && (
            <div
              style={{
                background: 'var(--bg-surface-elevated)',
                borderRadius: 'var(--radius-md)',
                padding: '16px',
                border: '1px solid var(--border-light)',
                fontSize: '0.85rem',
                lineHeight: '1.65',
                color: 'var(--text-secondary)'
              }}
            >
              {isEditing ? (
                <>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '8px', color: 'var(--brand-primary)', fontWeight: 600 }}>
                    <HelpCircle size={15} />
                    <span>Why Answers are Right or Wrong</span>
                  </div>
                  <textarea
                    value={editedExplanation}
                    onChange={(e) => setEditedExplanation(e.target.value)}
                    rows={4}
                    style={{ width: '100%', fontSize: '0.85rem', lineHeight: '1.6' }}
                  />
                </>
              ) : (
                <MentorExplanationView
                  explanation={question.explanation}
                  options={question.options}
                  correctAnswerId={question.correct_answer_id}
                  primaryTrap={question.primary_trap || effectiveTrapInfo?.key}
                  likelyMistakePattern={question.likely_mistake_pattern}
                />
              )}
            </div>
          )}
        </div>
      )}

      {/* --- TAB 2: 100-PT QUALITY SCORECARD --- */}
      {activeTab === 'scorecard' && (
        <QuestionScorecardTab question={question} pillars={pillars} />
      )}

      {/* --- TAB 3: STAGE JSON TELEMETRY --- */}
      {activeTab === 'telemetry' && (
        <StageJsonInspector question={question} />
      )}

      {/* Bottom Action Bar */}
      <QuestionCardFooter
        question={question}
        isSaved={isSaved}
        isApproving={isApproving}
        onApprove={handleApproveClick}
        onDiscard={onDiscard}
        onNextQuestion={onNextQuestion}
      />
    </div>
  );
}

export default React.memo(QuestionCard);
