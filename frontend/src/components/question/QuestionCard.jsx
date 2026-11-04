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
import { getEffectiveTrapInfo, calculateOptionSymmetry, countWords } from '../../utils';

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
    { label: 'Scientific Style', score: review?.authenticity_score ?? 24, max: 25, color: 'var(--brand-primary)' },
    { label: 'Clarity & Logic', score: review?.clarity_score ?? 24, max: 25, color: 'var(--brand-indigo)' },
    { label: 'Wrong Answers', score: review?.distractor_score ?? 23, max: 25, color: 'var(--status-warning)' },
    { label: 'Explanation Accuracy', score: review?.explanation_score ?? 24, max: 25, color: 'var(--status-success)' },
  ];

  const correctKeysList = Array.isArray(question.correct_answer_ids) && question.correct_answer_ids.length > 0
    ? question.correct_answer_ids.map(k => String(k).trim().toUpperCase())
    : (question.correct_answer_id || '').split(',').map(k => k.trim().toUpperCase()).filter(Boolean);

  return (
    <div className="glass-panel qcard-container">
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
          { id: 'preview', label: 'Preview', icon: FileText },
          { id: 'scorecard', label: 'Scorecard', icon: BarChart3 },
          { id: 'telemetry', label: 'Details', icon: Code2 }
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
        <div className="qcard-preview-flow">
          {/* Edit Mode Alert */}
          {isEditing && (
            <QuestionInlineEditor
              onSave={handleSaveEdit}
              onCancel={handleCancelEdit}
            />
          )}

          {/* Reading Passage (Stimulus) */}
          {((question.stimulus_text && question.stimulus_text.trim()) || (isEditing && (showStimulusField || (editedStimulus && editedStimulus.trim())))) ? (
            <div className="passage-editorial vignette-editorial qcard-passage-box">
              <div className="qcard-passage-header">
                <span className="qcard-passage-title">
                  Reading Passage
                </span>
                <span className="qcard-passage-words">
                  ~{countWords(isEditing ? editedStimulus : question.stimulus_text)} words
                </span>
              </div>

              {isEditing ? (
                <textarea
                  value={editedStimulus}
                  onChange={(e) => setEditedStimulus(e.target.value)}
                  rows={6}
                  placeholder="Enter optional reading passage or context..."
                  className="qcard-passage-textarea"
                />
              ) : (
                <div className="qcard-passage-body">
                  {question.stimulus_text}
                </div>
              )}

              {hasImage && (
                <div className="qcard-passage-diagram-wrap">
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
            <div className="qcard-add-passage-wrap">
              <button
                type="button"
                onClick={() => setShowStimulusField(true)}
                className="btn-secondary qcard-add-passage-btn"
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
          <div className="qcard-stem-wrap">
            {isEditing ? (
              <textarea
                value={editedStem}
                onChange={(e) => setEditedStem(e.target.value)}
                rows={2}
                className="qcard-stem-textarea"
              />
            ) : (
              <h3 className="qcard-stem-title">
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
          <div className="qcard-explanation-bar">
            <button
              type="button"
              className="btn-secondary qcard-explanation-toggle-btn"
              onClick={() => setShowExplanation(!showExplanation)}
            >
              {showExplanation ? <ChevronUp size={13} /> : <ChevronDown size={13} />}
              <span>{showExplanation ? 'Hide Explanations' : 'View Explanations'}</span>
            </button>

            <span className="qcard-explanation-key-text">
              Correct Answer: <strong className="qcard-explanation-key-val">Option {question.correct_answer_id}</strong>
            </span>
          </div>

          {/* Explanation Box */}
          {showExplanation && (
            <div className="qcard-explanation-wrap">
              {isEditing ? (
                <>
                  <div className="qcard-explanation-edit-header">
                    <HelpCircle size={15} />
                    <span>Explanations</span>
                  </div>
                  <textarea
                    value={editedExplanation}
                    onChange={(e) => setEditedExplanation(e.target.value)}
                    rows={4}
                    className="qcard-explanation-textarea"
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
