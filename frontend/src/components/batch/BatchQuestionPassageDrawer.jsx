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
    <div
      style={{
        marginBottom: '8px',
        borderRadius: 'var(--radius-xs)',
        border: '1px solid var(--border-light)',
        overflow: 'hidden',
        background: 'var(--bg-surface)'
      }}
    >
      <div
        style={{
          padding: '6px 10px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          background: 'var(--bg-surface-subtle)',
          borderBottom: isExpanded ? '1px solid var(--border-light)' : 'none'
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          <BookOpen size={13} style={{ color: 'var(--brand-primary)' }} />
          <span style={{ fontWeight: 600, fontSize: '0.75rem', color: 'var(--text-primary)' }}>
            Reading Passage
          </span>
          <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>
            ({wordCount} words)
          </span>
        </div>
        <button
          type="button"
          onClick={onToggle}
          className="btn-secondary"
          style={{
            padding: '2px 7px',
            fontSize: '0.7rem',
            gap: '4px',
            display: 'inline-flex',
            alignItems: 'center'
          }}
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
        <div
          style={{
            padding: '10px 12px',
            fontSize: '0.78rem',
            lineHeight: 1.6,
            color: 'var(--text-secondary)',
            maxHeight: '320px',
            overflowY: 'auto',
            whiteSpace: 'pre-wrap',
            background: 'var(--bg-canvas)'
          }}
        >
          {hasDiagram && (
            <div style={{ marginBottom: '10px' }}>
              <VisualStimulusViewer question={question} />
            </div>
          )}
          {question.stimulus_text}
        </div>
      )}
    </div>
  );
}

