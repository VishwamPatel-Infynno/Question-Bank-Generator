import { useState } from 'react';
import {
  BookOpen,
  ChevronDown,
  ChevronUp,
  Image as ImageIcon
} from 'lucide-react';
import { countWords } from '../../utils';
import VisualStimulusViewer from './VisualStimulusViewer';
import { EMPTY_OBJECT } from '../../constants';

/**
 * SharedPassageCard:
 * Unified, reusable reading passage container for PassageEditorialDesk, QuestionCard, and QuestionBank.
 * Encapsulates:
 * - Header with BookOpen icon, title, word count badge, linked questions badge, and diagram badge.
 * - Collapsible toggle with expand/collapse states.
 * - High-legibility editorial serif passage typography.
 * - Embedded VisualStimulusViewer with fullscreen preview support.
 */

export default function SharedPassageCard({
  title,
  passageText = '',
  questionCount = 1,
  totalCount: _totalCount,
  isMixedBatch = false,
  diagramQuestion = null,
  collapsible = true,
  defaultCollapsed = false,
  isSplitPane = false,
  style = EMPTY_OBJECT
}) {
  const [isCollapsed, setIsCollapsed] = useState(defaultCollapsed);
  const [fontSizeLevel, setFontSizeLevel] = useState(1); // 0: 0.85rem, 1: 0.935rem, 2: 1.05rem

  const fontSizes = ['0.85rem', '0.935rem', '1.05rem'];
  const fontLabels = ['Small (A-)', 'Default (A)', 'Large (A+)'];

  const handleDecreaseFont = () => {
    setFontSizeLevel(prev => Math.max(0, prev - 1));
  };

  const handleIncreaseFont = () => {
    setFontSizeLevel(prev => Math.min(fontSizes.length - 1, prev + 1));
  };

  if (!passageText || !passageText.trim()) {
    return null;
  }

  const wordCount = countWords(passageText);

  // Determine if a diagram/image is present
  const hasDiagram = Boolean(
    diagramQuestion &&
    (diagramQuestion.image_url ||
     diagramQuestion.image_svg ||
     diagramQuestion.stage_outcomes?.visual_stimulus?.image_url ||
     diagramQuestion.stage_outcomes?.visual_stimulus?.image_svg ||
     diagramQuestion.stage_outcomes?.passage_visual_stimulus?.image_url ||
     diagramQuestion.stage_outcomes?.passage_visual_stimulus?.image_svg)
  );

  const defaultTitle = isMixedBatch
    ? `Shared Reading Passage (Questions 1 to ${questionCount})`
    : 'Single Shared Reading Passage';

  return (
    <div
      className={`glass-panel shared-passage-card ${isSplitPane ? 'is-split-pane' : ''}`}
      style={style}
    >
      {/* Header Bar */}
      <div className="shared-passage-header">
        <div className="shared-passage-title-group">
          <div className="shared-passage-icon-box">
            <BookOpen size={18} />
          </div>

          <div>
            <div className="shared-passage-meta-wrap">
              <h3 className="shared-passage-title">
                {title || defaultTitle}
              </h3>
              <span className="badge badge-cyan shared-passage-badge">
                {wordCount} Words
              </span>
              {questionCount > 1 && (
                <span className="badge badge-indigo shared-passage-badge">
                  {questionCount} Linked Questions
                </span>
              )}
              {hasDiagram && (
                <span className="badge badge-purple shared-passage-figure-tag">
                  <ImageIcon size={10} /> Diagram
                </span>
              )}
            </div>
          </div>
        </div>

        <div className="shared-passage-controls">
          {/* Font Size Scaling Controls */}
          <div
            className="shared-passage-font-controls"
            title={`Passage text scale: ${fontLabels[fontSizeLevel]}`}
          >
            <button
              type="button"
              onClick={handleDecreaseFont}
              disabled={fontSizeLevel === 0}
              className="shared-passage-font-btn"
              title="Decrease passage font size"
            >
              A-
            </button>
            <span className="shared-passage-font-indicator">
              {fontSizeLevel === 0 ? '85%' : fontSizeLevel === 1 ? '100%' : '115%'}
            </span>
            <button
              type="button"
              onClick={handleIncreaseFont}
              disabled={fontSizeLevel === fontSizes.length - 1}
              className="shared-passage-font-btn"
              title="Increase passage font size"
            >
              A+
            </button>
          </div>

          {collapsible && (
            <button
              type="button"
              onClick={() => setIsCollapsed(prev => !prev)}
              className="btn-secondary shared-passage-toggle-btn"
              title={isCollapsed ? 'Expand Passage' : 'Collapse Passage'}
            >
              {isCollapsed ? <ChevronDown size={13} /> : <ChevronUp size={13} />}
              <span>{isCollapsed ? 'Show Full Passage' : 'Collapse Passage'}</span>
            </button>
          )}
        </div>
      </div>

      {/* Collapsible Body */}
      {(!collapsible || !isCollapsed) && (
        <div className="shared-passage-content-wrap">
          <div
            className={`shared-passage-body ${isSplitPane ? 'split-pane' : ''}`}
            style={{ fontSize: fontSizes[fontSizeLevel] }}
          >
            {passageText}
          </div>

          {/* Embedded Visual Stimulus Diagram */}
          {hasDiagram && (
            <div className="shared-passage-diagram-wrap">
              <VisualStimulusViewer
                question={diagramQuestion}
                compact={false}
              />
            </div>
          )}
        </div>
      )}
    </div>
  );
}
