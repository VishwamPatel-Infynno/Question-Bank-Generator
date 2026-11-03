import React, { useState } from 'react';
import {
  Edit3,
  Trash2,
  Image as ImageIcon,
  Copy,
  Check,
  Calendar,
  Layers
} from 'lucide-react';
import { formatDate } from '../../utils';
import { getSectionBadgeClass } from '../../constants/mcat';

const SECTION_SHORT_LABEL = {
  chem_phys: 'Chem / Phys',
  cars: 'CARS',
  bio_biochem: 'Bio / Biochem',
  psych_soc: 'Psych / Soc'
};

const EMPTY_ARRAY = Object.freeze([]);
const EMPTY_OBJECT = Object.freeze({});

/**
 * PassageBankTable
 *
 * Renders the list of MCAT reading passages in high-precision card rows,
 * highlighting word count, linked questions, stimulus figures, and editorial triggers.
 */
export default function PassageBankTable({
  passages = EMPTY_ARRAY,
  questionCounts = EMPTY_OBJECT, // map of passageId -> count of linked questions
  onSelectPassage,
  onDeletePassage,
  onCopyPassageId
}) {
  const [copiedId, setCopiedId] = useState(null);

  const handleCopy = (id, e) => {
    e.stopPropagation();
    navigator.clipboard.writeText(id);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
    if (onCopyPassageId) onCopyPassageId(id);
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
      {passages.map((passage) => {
        const wordCount = passage.word_count || (passage.text ? passage.text.split(/\s+/).filter(Boolean).length : 0);
        const linkedCount = questionCounts[passage.id] ?? (passage.questions ? passage.questions.length : 0);
        const hasVisual = Boolean(passage.image_url || passage.image_svg);
        const displayTitle = passage.title || `${passage.subtopic || 'MCAT'} Passage`;

        return (
          <div
            key={passage.id}
            role="button"
            tabIndex={0}
            onClick={() => onSelectPassage(passage)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                onSelectPassage(passage);
              }
            }}
            style={{
              padding: '16px 20px',
              display: 'flex',
              flexDirection: 'column',
              gap: '12px',
              background: 'var(--bg-surface)',
              border: '1px solid var(--border-subtle)',
              borderRadius: 'var(--radius-md)',
              cursor: 'pointer',
              transition: 'all var(--transition-fast)'
            }}
            className="passage-card-row"
            onMouseEnter={(e) => {
              e.currentTarget.style.borderColor = 'var(--border-medium)';
              e.currentTarget.style.transform = 'translateY(-1px)';
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.borderColor = 'var(--border-subtle)';
              e.currentTarget.style.transform = 'none';
            }}
          >
            {/* Top Row: Badges, Title, Actions */}
            <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: '16px' }}>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', flex: 1, minWidth: 0 }}>
                {/* Badges strip */}
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap', fontSize: '0.725rem' }}>
                  <span className={`badge ${getSectionBadgeClass(passage.section)}`} style={{ fontSize: '0.66rem', fontWeight: 700 }}>
                    {SECTION_SHORT_LABEL[passage.section] || passage.section || 'General'}
                  </span>

                  {passage.subtopic && (
                    <span style={{ color: 'var(--text-secondary)', fontWeight: 600, fontSize: '0.72rem' }}>
                      {passage.subtopic}
                    </span>
                  )}

                  <span
                    style={{
                      background: 'var(--bg-surface-subtle)',
                      border: '1px solid var(--border-light)',
                      borderRadius: 'var(--radius-full)',
                      padding: '1px 7px',
                      fontSize: '0.68rem',
                      fontWeight: 600,
                      color: 'var(--text-secondary)',
                      display: 'inline-flex',
                      alignItems: 'center',
                      gap: '4px'
                    }}
                  >
                    <span>{wordCount} words</span>
                  </span>

                  <span
                    style={{
                      background: linkedCount > 0 ? 'rgba(51, 90, 207, 0.08)' : 'var(--bg-surface-subtle)',
                      border: linkedCount > 0 ? '1px solid rgba(51, 90, 207, 0.25)' : '1px solid var(--border-light)',
                      borderRadius: 'var(--radius-full)',
                      padding: '1px 7px',
                      fontSize: '0.68rem',
                      fontWeight: 600,
                      color: linkedCount > 0 ? 'var(--brand-primary)' : 'var(--text-muted)',
                      display: 'inline-flex',
                      alignItems: 'center',
                      gap: '4px'
                    }}
                  >
                    <Layers size={11} />
                    <span>{linkedCount} {linkedCount === 1 ? 'question' : 'questions'}</span>
                  </span>

                  {hasVisual && (
                    <span
                      style={{
                        background: 'rgba(16, 185, 129, 0.08)',
                        border: '1px solid rgba(16, 185, 129, 0.25)',
                        borderRadius: 'var(--radius-full)',
                        padding: '1px 7px',
                        fontSize: '0.68rem',
                        fontWeight: 600,
                        color: 'var(--status-success)',
                        display: 'inline-flex',
                        alignItems: 'center',
                        gap: '4px'
                      }}
                      title="Passage contains scientific figure or vector diagram"
                    >
                      <ImageIcon size={11} />
                      <span>Figure / Diagram</span>
                    </span>
                  )}
                </div>

                {/* Title */}
                <h3
                  style={{
                    fontSize: '0.98rem',
                    fontWeight: 700,
                    color: 'var(--text-primary)',
                    margin: 0,
                    letterSpacing: '-0.01em',
                    lineHeight: 1.3
                  }}
                >
                  {displayTitle}
                </h3>
              </div>

              {/* Action Buttons */}
              <div
                style={{ display: 'flex', alignItems: 'center', gap: '6px', flexShrink: 0 }}
                onClick={(e) => e.stopPropagation()}
              >
                <button
                  type="button"
                  onClick={() => onSelectPassage(passage)}
                  className="btn-secondary"
                  style={{
                    padding: '5px 10px',
                    fontSize: '0.74rem',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '5px'
                  }}
                  title="Open dedicated passage editorial desk & linked questions"
                >
                  <Edit3 size={13} color="var(--brand-primary)" />
                  <span>Open &amp; Edit</span>
                </button>

                <button
                  type="button"
                  onClick={(e) => handleCopy(passage.id, e)}
                  className="btn-ghost"
                  style={{
                    padding: '5px 8px',
                    fontSize: '0.72rem',
                    color: copiedId === passage.id ? 'var(--status-success)' : 'var(--text-muted)'
                  }}
                  title="Copy Passage ID"
                  aria-label="Copy Passage ID"
                >
                  {copiedId === passage.id ? <Check size={13} /> : <Copy size={13} />}
                </button>

                <button
                  type="button"
                  onClick={(e) => {
                    e.stopPropagation();
                    if (onDeletePassage) onDeletePassage(passage);
                  }}
                  className="btn-ghost"
                  style={{
                    padding: '5px 8px',
                    fontSize: '0.72rem',
                    color: 'var(--status-danger)'
                  }}
                  title="Delete passage and linked questions"
                  aria-label="Delete passage"
                >
                  <Trash2 size={13} />
                </button>
              </div>
            </div>

            {/* Passage Text Preview Excerpt */}
            <p
              style={{
                fontFamily: 'var(--font-serif)',
                fontSize: '0.88rem',
                lineHeight: 1.55,
                color: 'var(--text-secondary)',
                margin: 0,
                display: '-webkit-box',
                WebkitLineClamp: 3,
                WebkitBoxOrient: 'vertical',
                overflow: 'hidden',
                textOverflow: 'ellipsis'
              }}
            >
              {passage.text || <span style={{ color: 'var(--text-muted)', fontStyle: 'italic' }}>No passage text provided.</span>}
            </p>

            {/* Bottom Meta Footer */}
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                paddingTop: '6px',
                borderTop: '1px solid var(--border-light)',
                fontSize: '0.68rem',
                color: 'var(--text-muted)'
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <span style={{ fontFamily: 'var(--font-mono)' }}>ID: {passage.id}</span>
                {passage.created_at && (
                  <>
                    <span>•</span>
                    <span style={{ display: 'inline-flex', alignItems: 'center', gap: '4px' }}>
                      <Calendar size={11} />
                      {formatDate(passage.created_at)}
                    </span>
                  </>
                )}
              </div>

              <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                <span style={{ color: 'var(--brand-primary)', fontWeight: 600 }}>
                  Click to inspect &amp; edit →
                </span>
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}
