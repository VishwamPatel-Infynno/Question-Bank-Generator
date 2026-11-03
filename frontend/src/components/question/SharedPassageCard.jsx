import { useState } from 'react';
import {
  BookOpen,
  ChevronDown,
  ChevronUp,
  Image as ImageIcon
} from 'lucide-react';
import VisualStimulusViewer from './VisualStimulusViewer';

/**
 * SharedPassageCard:
 * Unified, reusable reading passage container for PassageEditorialDesk, QuestionCard, and QuestionBank.
 * Encapsulates:
 * - Header with BookOpen icon, title, word count badge, linked questions badge, and diagram badge.
 * - Collapsible toggle with expand/collapse states.
 * - High-legibility editorial serif passage typography.
 * - Embedded VisualStimulusViewer with fullscreen preview support.
 */
const EMPTY_OBJECT = Object.freeze({});

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

  const wordCount = passageText.trim().split(/\s+/).filter(Boolean).length;

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
      className="glass-panel shared-passage-card"
      style={{
        padding: '16px 20px',
        borderLeft: '4px solid var(--brand-primary)',
        borderRadius: 'var(--radius-md)',
        display: 'flex',
        flexDirection: 'column',
        gap: '12px',
        background: 'var(--bg-surface)',
        boxShadow: 'var(--shadow-sm)',
        ...(isSplitPane
          ? {
              maxHeight: 'calc(100vh - 120px)',
              overflowY: 'auto',
              position: 'sticky',
              top: '88px'
            }
          : {}),
        ...style
      }}
    >
      {/* Header Bar */}
      <div
        style={{
          display: 'flex',
          alignItems: 'flex-start',
          justifyContent: 'space-between',
          flexWrap: 'wrap',
          gap: '12px'
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              width: '32px',
              height: '32px',
              borderRadius: 'var(--radius-xs)',
              background: 'var(--brand-light)',
              color: 'var(--brand-primary)',
              flexShrink: 0
            }}
          >
            <BookOpen size={18} />
          </div>

          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
              <h3 style={{ fontSize: '0.925rem', fontWeight: 700, color: 'var(--text-primary)', margin: 0 }}>
                {title || defaultTitle}
              </h3>
              <span className="badge badge-cyan" style={{ fontSize: '0.675rem', fontWeight: 600 }}>
                {wordCount} Words
              </span>
              {questionCount > 1 && (
                <span className="badge badge-indigo" style={{ fontSize: '0.675rem', fontWeight: 600 }}>
                  {questionCount} Linked Questions
                </span>
              )}
              {hasDiagram && (
                <span
                  className="badge badge-purple"
                  style={{
                    fontSize: '0.675rem',
                    fontWeight: 600,
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: '3px'
                  }}
                >
                  <ImageIcon size={10} /> Diagram
                </span>
              )}
            </div>
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          {/* Font Size Scaling Controls */}
          <div
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              background: 'var(--bg-surface-subtle)',
              border: '1px solid var(--border-light)',
              borderRadius: 'var(--radius-xs)',
              padding: '2px 4px',
              gap: '2px'
            }}
            title={`Passage text scale: ${fontLabels[fontSizeLevel]}`}
          >
            <button
              type="button"
              onClick={handleDecreaseFont}
              disabled={fontSizeLevel === 0}
              style={{
                background: 'transparent',
                border: 'none',
                color: fontSizeLevel === 0 ? 'var(--text-dim)' : 'var(--text-secondary)',
                cursor: fontSizeLevel === 0 ? 'default' : 'pointer',
                fontSize: '0.7rem',
                fontWeight: 700,
                padding: '2px 6px',
                borderRadius: 'var(--radius-xs)'
              }}
              title="Decrease passage font size"
            >
              A-
            </button>
            <span style={{ fontSize: '0.675rem', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)', minWidth: '32px', textAlign: 'center' }}>
              {fontSizeLevel === 0 ? '85%' : fontSizeLevel === 1 ? '100%' : '115%'}
            </span>
            <button
              type="button"
              onClick={handleIncreaseFont}
              disabled={fontSizeLevel === fontSizes.length - 1}
              style={{
                background: 'transparent',
                border: 'none',
                color: fontSizeLevel === fontSizes.length - 1 ? 'var(--text-dim)' : 'var(--text-secondary)',
                cursor: fontSizeLevel === fontSizes.length - 1 ? 'default' : 'pointer',
                fontSize: '0.7rem',
                fontWeight: 700,
                padding: '2px 6px',
                borderRadius: 'var(--radius-xs)'
              }}
              title="Increase passage font size"
            >
              A+
            </button>
          </div>

          {collapsible && (
            <button
              type="button"
              onClick={() => setIsCollapsed(prev => !prev)}
              className="btn-secondary"
              style={{ padding: '5px 12px', fontSize: '0.725rem', gap: '6px' }}
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
        <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
          <div
            style={{
              padding: '14px 18px',
              background: 'var(--bg-surface-subtle)',
              borderRadius: 'var(--radius-sm)',
              border: '1px solid var(--border-light)',
              maxHeight: isSplitPane ? 'none' : '300px',
              overflowY: isSplitPane ? 'visible' : 'auto',
              fontFamily: 'var(--font-serif)',
              fontSize: fontSizes[fontSizeLevel],
              lineHeight: '1.7',
              color: 'var(--text-primary)',
              whiteSpace: 'pre-line'
            }}
          >
            {passageText}
          </div>

          {/* Embedded Visual Stimulus Diagram */}
          {hasDiagram && (
            <div
              style={{
                borderRadius: 'var(--radius-sm)',
                overflow: 'hidden',
                border: '1px solid var(--border-light)'
              }}
            >
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
