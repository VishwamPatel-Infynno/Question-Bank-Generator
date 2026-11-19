import PassageBankCardRow from './PassageBankCardRow';
import { useCopyToClipboard } from '../../hooks';
import { EMPTY_ARRAY, EMPTY_OBJECT } from '../../constants';

/**
 * PassageBankTable
 *
 * Renders the list of MCAT reading passages using memoized card rows,
 * isolating row-level clipboard copying and editorial desk interactions.
 */
export default function PassageBankTable({
  passages = EMPTY_ARRAY,
  questionCounts = EMPTY_OBJECT, // map of passageId -> count of linked questions
  onSelectPassage,
  onDeletePassage,
  onCopyPassageId
}) {
  const { copiedKey: copiedId, copy } = useCopyToClipboard();

  const handleCopy = (id, e) => {
    e.stopPropagation();
    copy(id, id);
    if (onCopyPassageId) onCopyPassageId(id);
  };

  return (
    <div className="passage-bank-list-wrap">
      {passages.map((passage) => {
        const linkedCount = questionCounts[passage.id] ?? (passage.questions ? passage.questions.length : 0);
        return (
          <PassageBankCardRow
            key={passage.id}
            passage={passage}
            linkedCount={linkedCount}
            isCopied={copiedId === passage.id}
            onSelectPassage={onSelectPassage}
            onDeletePassage={onDeletePassage}
            onCopyPassageId={handleCopy}
          />
        );
      })}
    </div>
  );
}
