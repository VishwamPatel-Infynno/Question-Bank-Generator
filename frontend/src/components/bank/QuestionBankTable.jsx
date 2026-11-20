import { useMemo } from 'react';
import QuestionBankCardRow from './QuestionBankCardRow';
import { EMPTY_ARRAY } from '../../constants';

/**
 * QuestionBankTable
 *
 * Renders the question bank repository using the canonical Editorial Cards view,
 * featuring interactive selection, expandable stimulus/diagram drawers,
 * options proof breakdowns, and mentor pedagogical explanations.
 */
export default function QuestionBankTable({
  paginatedQuestions = EMPTY_ARRAY,
  selectedIds = EMPTY_ARRAY,
  expandedId,
  setExpandedId,
  copiedId,
  onToggleSelect,
  onCopy,
  onDelete,
  onSelectQuestion,
  onCompareDuplicate,
}) {
  const selectedSet = useMemo(() => new Set(selectedIds), [selectedIds]);

  return (
    <div className="qbank-table-list-wrap">
      {paginatedQuestions.map((q) => (
        <QuestionBankCardRow
          key={q.id}
          q={q}
          isSelected={selectedSet.has(q.id)}
          isExpanded={expandedId === q.id}
          isCopied={copiedId === q.id}
          onToggleSelect={onToggleSelect}
          onToggleExpand={setExpandedId}
          onCopy={onCopy}
          onDelete={onDelete}
          onSelectQuestion={onSelectQuestion}
          onCompareDuplicate={onCompareDuplicate}
        />
      ))}
    </div>
  );
}
