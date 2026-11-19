import { memo } from 'react';
import {
  Edit3,
  Trash2,
  Image as ImageIcon,
  Copy,
  Check,
  Calendar,
  Layers
} from 'lucide-react';
import { countWords, formatDate } from '../../utils';
import { getSectionBadgeClass, getSectionShortLabel } from '../../constants';

/**
 * PassageBankCardRow
 *
 * Isolated, memoized card row for MCAT reading passages.
 * Prevents full-table re-render cascades during clipboard copy and desk navigation.
 *
 * @param {Object} props
 * @param {Object} props.passage - Passage data object.
 * @param {number} props.linkedCount - Number of questions linked to this passage.
 * @param {boolean} props.isCopied - Whether this passage's ID is currently copied.
 * @param {function(Object): void} props.onSelectPassage - Callback to open editorial desk.
 * @param {function(Object): void} [props.onDeletePassage] - Callback to delete passage.
 * @param {function(string, Event): void} props.onCopyPassageId - Callback to copy passage ID.
 * @returns {JSX.Element}
 */
function PassageBankCardRow({
  passage,
  linkedCount = 0,
  isCopied = false,
  onSelectPassage,
  onDeletePassage,
  onCopyPassageId
}) {
  const wordCount = passage.word_count || countWords(passage.text);
  const hasVisual = Boolean(passage.image_url || passage.image_svg);
  const displayTitle = passage.title || `${passage.subtopic || 'MCAT'} Passage`;

  return (
    <div
      role="button"
      tabIndex={0}
      onClick={() => onSelectPassage?.(passage)}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          onSelectPassage?.(passage);
        }
      }}
      className="passage-card-row"
    >
      {/* Top Row: Badges, Title, Actions */}
      <div className="passage-card-header">
        <div className="passage-card-meta">
          {/* Badges strip */}
          <div className="passage-card-badges">
            <span className={`badge ${getSectionBadgeClass(passage.section)}`}>
              {getSectionShortLabel(passage.section)}
            </span>

            {passage.subtopic && (
              <span className="passage-card-subtopic">
                {passage.subtopic}
              </span>
            )}

            <span className="passage-desk-pill-words">
              <span>{wordCount} words</span>
            </span>

            <span className={linkedCount > 0 ? 'passage-desk-pill-linked' : 'passage-desk-pill-words'}>
              <Layers size={11} />
              <span>{linkedCount} {linkedCount === 1 ? 'question' : 'questions'}</span>
            </span>

            {hasVisual && (
              <span
                className="passage-card-figure-pill"
                title="Passage contains scientific figure or vector diagram"
              >
                <ImageIcon size={11} />
                <span>Figure / Diagram</span>
              </span>
            )}
          </div>

          {/* Title */}
          <h3 className="passage-card-title">
            {displayTitle}
          </h3>
        </div>

        {/* Action Buttons */}
        <div
          className="passage-card-actions"
          onClick={(e) => e.stopPropagation()}
        >
          <button
            type="button"
            onClick={() => onSelectPassage?.(passage)}
            className="btn-secondary passage-card-edit-btn"
            title="Open dedicated passage editorial desk & linked questions"
          >
            <Edit3 size={13} color="var(--brand-primary)" />
            <span>Open &amp; Edit</span>
          </button>

          <button
            type="button"
            onClick={(e) => onCopyPassageId?.(passage.id, e)}
            className={`btn-ghost passage-card-icon-btn ${isCopied ? 'copied' : ''}`}
            title="Copy Passage ID"
            aria-label="Copy Passage ID"
          >
            {isCopied ? <Check size={13} /> : <Copy size={13} />}
          </button>

          {onDeletePassage && (
            <button
              type="button"
              onClick={(e) => {
                e.stopPropagation();
                onDeletePassage(passage);
              }}
              className="btn-ghost passage-card-icon-btn danger"
              title="Delete passage and linked questions"
              aria-label="Delete passage"
            >
              <Trash2 size={13} />
            </button>
          )}
        </div>
      </div>

      {/* Passage Text Preview Excerpt */}
      <p className="passage-card-excerpt">
        {passage.text || <span className="passage-card-empty-text">No passage text provided.</span>}
      </p>

      {/* Bottom Meta Footer */}
      <div className="passage-card-footer">
        <div className="passage-card-footer-left">
          <span className="passage-card-footer-id">ID: {passage.id}</span>
          {passage.created_at && (
            <>
              <span>•</span>
              <span className="passage-card-footer-date">
                <Calendar size={11} />
                {formatDate(passage.created_at)}
              </span>
            </>
          )}
        </div>

        <div className="passage-card-footer-right">
          <span className="passage-card-footer-cta">
            Click to inspect &amp; edit →
          </span>
        </div>
      </div>
    </div>
  );
}

export default memo(PassageBankCardRow);
