const time = (p) => new Date(p.created_at || 0).getTime();

const SORTERS = {
  newest: (a, b) => time(b) - time(a),
  oldest: (a, b) => time(a) - time(b),
  words_desc: (a, b) => (b.word_count || 0) - (a.word_count || 0),
  words_asc: (a, b) => (a.word_count || 0) - (b.word_count || 0),
  title_asc: (a, b) => (a.title || '').localeCompare(b.title || '')
};

/** A sorted copy of `passages` (unknown `sortBy` keeps the original order). */
export function sortPassages(passages, sortBy) {
  const list = [...(passages || [])];
  const sorter = SORTERS[sortBy];
  return sorter ? list.sort(sorter) : list;
}

/** `{ passageId: question_count }` from the server-aggregated counts on each passage. */
export function passageQuestionCounts(passages) {
  const counts = {};
  (passages || []).forEach((p) => {
    counts[p.id] = p.question_count || 0;
  });
  return counts;
}
