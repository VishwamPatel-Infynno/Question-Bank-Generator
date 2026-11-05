// JSON export of the question bank.
/**
 * Serializes an array of questions into formatted JSON.
 * @param {Array<object>} questions - Questions dataset
 * @returns {string} Formatted JSON string with 2-space indentation
 */
export function generateExamJson(questions = []) {
  return JSON.stringify(questions || [], null, 2);
}
