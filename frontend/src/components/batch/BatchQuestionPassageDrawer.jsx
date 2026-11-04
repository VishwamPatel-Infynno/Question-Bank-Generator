import React from 'react';
import { BookOpen, ChevronDown, ChevronUp } from 'lucide-react';
import VisualStimulusViewer from '../question/VisualStimulusViewer';

/**
 * BatchQuestionPassageDrawer - Collapsible reading passage drawer with word count and visual stimulus.
 */
export default function BatchQuestionPassageDrawer({
  question,
  hasDiagram = false,
  isExpanded = false,
  onToggle
}) {
  if (!question?.stimulus_text) return null;

  const wordCount = question.stimulus_text.trim().split(/\s+/).length;

  return (
    <div className="batch-qitem-drawer">
      <div className={`batch-qitem-drawer-head ${isExpanded ? 'expanded' : ''}`}>
        <div className="batch-qitem-drawer-head-left">
          <BookOpen size={13} className="batch-qitem-passage-icon" />
          <span className="batch-qitem-drawer-head-title">
            Reading Passage
          </span>
          <span className="batch-qitem-drawer-head-count">
            ({wordCount} words)
          </span>
        </div>
        <button
          type="button"
          onClick={onToggle}
          className="btn-secondary batch-qitem-drawer-btn"
        >
          {isExpanded ? (
            <>
              <ChevronUp size={12} />
              <span>Hide Passage</span>
            </>
          ) : (
            <>
              <ChevronDown size={12} />
              <span>View Passage</span>
            </>
          )}
        </button>
      </div>

      {isExpanded && (
        <div className="batch-qitem-drawer-body">
          {hasDiagram && (
            <div className="batch-qitem-stimulus-box">
              <VisualStimulusViewer question={question} />
            </div>
          )}
          {question.stimulus_text}
        </div>
      )}
    </div>
  );
}
