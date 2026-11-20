import { GitCompare, Loader2 } from 'lucide-react';
import { Modal, FormattedText } from '../common';
import { getDuplicateState, isCorrectOption } from '../../utils';

function OptionRow({ id, text, isKey = false }) {
  return (
    <li className={`dup-compare-option ${isKey ? 'correct' : ''}`}>
      <span className="dup-compare-option-id">{id}.</span>
      <span className="dup-compare-option-text">{text}</span>
      {isKey && <span className="badge badge-emerald">Key</span>}
    </li>
  );
}

/**
 * DuplicateCompareModal
 *
 * Side-by-side view of a flagged question and the original it matched, using the stem, options and
 * explanation the API already returns in `duplicate_info` (no extra fetch). The original may have
 * been removed, in which case a plain notice is shown.
 *
 * @param {Object} props
 * @param {Object|null} props.question - Question being compared; the modal is closed when null.
 * @param {() => void} props.onClose
 * @param {(question: Object) => void} [props.onOverride]
 * @param {boolean} [props.isOverriding]
 */
export default function DuplicateCompareModal({ question, onClose, onOverride, isOverriding = false }) {
  const { level, percent, isOverridden, info } = getDuplicateState(question);
  const hasOriginal = Boolean(info?.matched_question_stem);
  const matchedOptions = info?.matched_options || [];

  const footer = (
    <>
      <button type="button" className="btn-secondary" onClick={onClose} disabled={isOverriding}>
        Close
      </button>
      {!isOverridden && onOverride && question && (
        <button
          type="button"
          className="btn-primary"
          onClick={() => onOverride(question)}
          disabled={isOverriding}
        >
          {isOverriding ? <Loader2 size={14} className="spin-animate" aria-hidden="true" /> : null}
          <span>Override and approve</span>
        </button>
      )}
    </>
  );

  const subtitle =
    level === 'none'
      ? undefined
      : isOverridden
        ? 'You approved this question even though it looks like another one.'
        : `${percent}% similar${info?.match_reason ? `. ${info.match_reason}` : ''}`;

  return (
    <Modal
      isOpen={Boolean(question)}
      onClose={onClose}
      title="Compare with original"
      subtitle={subtitle}
      icon={<GitCompare size={18} />}
      maxWidth="900px"
      isProcessing={isOverriding}
      footer={footer}
    >
      {question && (
        <div className="dup-compare-grid">
          <section className="dup-compare-col" aria-label="This question">
            <h3 className="dup-compare-heading">This question</h3>
            <p className="dup-compare-stem">
              <FormattedText text={question.question_stem} />
            </p>
            <ul className="dup-compare-options">
              {(question.options || []).map((opt) => (
                <OptionRow key={opt.id} id={opt.id} text={opt.text} isKey={isCorrectOption(question, opt.id)} />
              ))}
            </ul>
            {question.explanation && (
              <div className="dup-compare-explanation">
                <h4 className="dup-compare-subheading">Explanation</h4>
                <FormattedText text={question.explanation} />
              </div>
            )}
          </section>

          <section className="dup-compare-col" aria-label="Original question">
            <h3 className="dup-compare-heading">Original question</h3>
            {hasOriginal ? (
              <>
                <p className="dup-compare-stem">
                  <FormattedText text={info.matched_question_stem} />
                </p>
                {matchedOptions.length > 0 && (
                  <ul className="dup-compare-options">
                    {matchedOptions.map((opt) => (
                      <OptionRow key={opt.id} id={opt.id} text={opt.text} />
                    ))}
                  </ul>
                )}
                {info.matched_explanation && (
                  <div className="dup-compare-explanation">
                    <h4 className="dup-compare-subheading">Explanation</h4>
                    <FormattedText text={info.matched_explanation} />
                  </div>
                )}
              </>
            ) : (
              <p className="dup-compare-missing">The original is no longer available.</p>
            )}
          </section>
        </div>
      )}
    </Modal>
  );
}
