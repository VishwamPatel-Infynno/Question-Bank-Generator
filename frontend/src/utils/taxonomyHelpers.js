/** Pure helpers over the section taxonomy (subjects > units > topics). */

/** With "All disciplines" only the first units and topics of each subject are offered. */
export const OVERVIEW_UNITS_PER_SUBJECT = 2;
export const OVERVIEW_TOPICS_PER_UNIT = 2;

const withContext = (topic, unit, subject) => ({
  ...topic,
  unitId: unit.id,
  unitName: unit.name,
  subjectId: subject.id,
  subjectName: subject.name
});

/**
 * Flat list of topics, each carrying its unit and subject ids/names.
 * @param {Array<object>} subjects - Subjects of one section
 * @param {object|null} activeSubject - A selected subject (all its topics), or null for the
 *   cross-subject overview (first few high-yield topics per subject)
 */
export function flattenTopics(subjects, activeSubject) {
  if (activeSubject) {
    return (activeSubject.units || []).flatMap((unit) =>
      (unit.topics || []).map((topic) => withContext(topic, unit, activeSubject))
    );
  }
  return (subjects || []).flatMap((subject) =>
    (subject.units || [])
      .slice(0, OVERVIEW_UNITS_PER_SUBJECT)
      .flatMap((unit) =>
        (unit.topics || [])
          .slice(0, OVERVIEW_TOPICS_PER_UNIT)
          .map((topic) => withContext(topic, unit, subject))
      )
  );
}
