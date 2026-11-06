import { useQuestionDraft } from '../../hooks/useQuestionDraft';
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
import {
  calculateOptionSymmetry,
  countWords,
  getCorrectAnswerIds,
  getEffectiveTrapInfo,
  getReviewPillars,
  hasQuestionImage
} from '../../utils';

function QuestionCard({ question, isSaved = true, onOpenAudit, onUpdateQuestion }) {
  const [activeTab, setActiveTab] = useState('preview'); // 'preview' | 'scorecard' | 'telemetry'
  const [showExplanation, setShowExplanation] = useState(true);

  // Quick Inline Edit Mode State
  const [isEditing, setIsEditing] = useState(false);
  const { draft, setDraftField, resetDraft, toQuestion } = useQuestionDraft(question);

  const effectiveTrapInfo = getEffectiveTrapInfo(question);

  const optionSymmetry = useMemo(() => {
    if (!question) return null;
    if (question.option_symmetry && Object.keys(question.option_symmetry).length > 0) {
      return question.option_symmetry;
    }
    if (question.stage_outcomes?.option_symmetry) {
      return question.stage_outcomes.option_symmetry;
    }
    const currentOptions = isEditing ? draft.options : (question.options || []);
    return calculateOptionSymmetry(currentOptions);
  }, [question, isEditing, draft.options]);

  const hasStimulus = Boolean(
    (question?.stimulus_text && question.stimulus_text.trim()) ||
    (isEditing && (draft.showStimulusField || (draft.stimulus && draft.stimulus.trim())))
  );

  const hasImage = hasQuestionImage(question);

  if (!question) return null;

  const handleSaveEdit = async () => {
    const updated = toQuestion();
    try {
      if (onUpdateQuestion) await onUpdateQuestion(updated);
      setIsEditing(false);
    } catch {
      // The save failed (the owner already showed an error): stay in edit mode so the user's
      // changes are not lost
    }
  };

  const handleCancelEdit = () => {
    resetDraft();
    setIsEditing(false);
  };

  const review = question.review_rubric;
  const pillars = getReviewPillars(review);

  const correctKeysList = getCorrectAnswerIds(question);

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
        onToggleEditing={() => (isEditing ? handleCancelEdit() : setIsEditing(true))}
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
          {((question.stimulus_text && question.stimulus_text.trim()) || (isEditing && (draft.showStimulusField || (draft.stimulus && draft.stimulus.trim())))) ? (
            <div className="passage-editorial vignette-editorial qcard-passage-box">
              <div className="qcard-passage-header">
                <span className="qcard-passage-title">
                  Reading Passage
                </span>
                <span className="qcard-passage-words">
                  ~{countWords(isEditing ? draft.stimulus : question.stimulus_text)} words
                </span>
              </div>

              {isEditing ? (
                <textarea
                  value={draft.stimulus}
                  onChange={(e) => setDraftField('stimulus', e.target.value)}
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
                    editedDescription={draft.imageDescription}
                    onDescriptionChange={(v) => setDraftField('imageDescription', v)}
                  />
                </div>
              )}
            </div>
          ) : isEditing ? (
            <div className="qcard-add-passage-wrap">
              <button
                type="button"
                onClick={() => setDraftField('showStimulusField', true)}
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
              editedDescription={draft.imageDescription}
              onDescriptionChange={(v) => setDraftField('imageDescription', v)}
            />
          )}

          {/* Question Stem */}
          <div className="qcard-stem-wrap">
            {isEditing ? (
              <textarea
                value={draft.stem}
                onChange={(e) => setDraftField('stem', e.target.value)}
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
            editedOptions={draft.options}
            onEditedOptionsChange={(v) => setDraftField('options', v)}
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
                    value={draft.explanation}
                    onChange={(e) => setDraftField('explanation', e.target.value)}
                    rows={4}
                    className="qcard-explanation-textarea"
                  />
                </>
              ) : (
                <MentorExplanationView
                  explanation={question.explanation}
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
      <QuestionCardFooter isSaved={isSaved} />
    </div>
  );
}

export default React.memo(QuestionCard);
