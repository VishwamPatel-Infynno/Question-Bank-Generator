/**
 * @module api
 * @description Typed HTTP client for the Question Bank Generator REST API.
 * All functions throw a descriptive Error on non-2xx responses via {@link assertOk}.
 */

// API Service for communicating with backend API
const API_BASE = '/api';

/**
 * Serializes an object into URLSearchParams, omitting undefined, null, and empty values.
 * @param {Record<string, any>} params
 * @returns {URLSearchParams}
 */
function buildQuery(params = {}) {
  const query = new URLSearchParams();
  for (const [key, val] of Object.entries(params)) {
    if (val !== undefined && val !== null && val !== '') {
      query.append(key, val);
    }
  }
  return query;
}

/**
 * Asserts that a fetch Response is successful (2xx).
 * Extracts the server error detail from JSON body when available.
 * @param {Response} res - The fetch Response object.
 * @param {string} context - Human-readable description of the call for error messages.
 * @returns {Promise<Response>} The same response if OK.
 * @throws {Error} A descriptive error if the response is not OK.
 */
async function assertOk(res, context = 'API call') {
  if (!res.ok) {
    let detail = '';
    try {
      const body = await res.clone().json();
      detail = body?.detail || body?.message || '';
    } catch { /* ignore parse failures - use status code only */ }
    throw new Error(
      `${context} failed (HTTP ${res.status})${detail ? `: ${detail}` : ''}`
    );
  }
  return res;
}

export async function fetchHealth() {
  const res = await fetch(`${API_BASE}/health`);
  await assertOk(res, 'Health check');
  return res.json();
}

export async function fetchSections() {
  const res = await fetch(`${API_BASE}/sections`);
  await assertOk(res, 'Fetch sections');
  return res.json();
}

/**
 * Fetches the full manager MCAT dependent taxonomy directly from backend API.
 * Used for dynamic outline updates and synchronizing runtime taxonomy state.
 */
export async function fetchTaxonomy() {
  const res = await fetch(`${API_BASE}/taxonomy`);
  await assertOk(res, 'Fetch taxonomy');
  return res.json();
}

export async function fetchQuestions(params = {}, signal = null) {
  const query = buildQuery(params);
  const res = await fetch(`${API_BASE}/questions?${query.toString()}`, { signal });
  await assertOk(res, 'Fetch questions');
  return res.json();
}

export async function fetchQuestionCounts(signal = null) {
  const res = await fetch(`${API_BASE}/questions/counts`, { signal });
  await assertOk(res, 'Fetch question counts');
  return res.json();
}

export async function updateQuestionStatus(id, status) {
  const res = await fetch(`${API_BASE}/questions/${id}/status`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ status })
  });
  await assertOk(res, `Update question ${id} status to ${status}`);
  return res.json();
}

export async function batchUpdateQuestionStatus(ids, status) {
  const res = await fetch(`${API_BASE}/questions/update-status`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ ids, status })
  });
  await assertOk(res, `Bulk update questions status to ${status}`);
  return res.json();
}

export async function fetchQuestionById(id) {
  const res = await fetch(`${API_BASE}/questions/${id}`);
  await assertOk(res, `Fetch question ${id}`);
  return res.json();
}

export async function deleteQuestion(id) {
  const res = await fetch(`${API_BASE}/questions/${id}`, { method: 'DELETE' });
  await assertOk(res, `Delete question ${id}`);
  return res.json();
}

export async function batchDeleteQuestions(ids) {
  const res = await fetch(`${API_BASE}/questions/delete-batch`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ ids })
  });
  await assertOk(res, 'Bulk delete questions');
  return res.json();
}

export async function purgeQuestion(id) {
  const res = await fetch(`${API_BASE}/questions/${id}/permanent`, {
    method: 'DELETE'
  });
  await assertOk(res, `Purge question ${id}`);
  return res.json();
}

export async function purgeQuestionsBatch(ids) {
  const res = await fetch(`${API_BASE}/questions/purge-batch`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ ids })
  });
  await assertOk(res, 'Purge questions batch');
  return res.json();
}

export async function restoreQuestion(id) {
  const res = await fetch(`${API_BASE}/questions/${id}/restore`, {
    method: 'POST'
  });
  await assertOk(res, `Restore question ${id}`);
  return res.json();
}

/**
 * Approves and saves a single question to the Question Bank.
 *
 * POSTs the full question object to `/api/questions`. On success the question
 * is persisted with status `in_bank` and a database-assigned ID is returned.
 *
 * @param {Object} question - Full Question schema object (must include all required fields).
 * @returns {Promise<Object>} The saved question record as returned by the API.
 * @throws {Error} If the HTTP response is not 2xx.
 */
export async function approveQuestion(question) {
  const res = await fetch(`${API_BASE}/questions`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(question)
  });
  await assertOk(res, 'Save approved question');
  return res.json();
}

/**
 * Manually overrides a duplicate warning on a question and approves it to Question Bank.
 * @param {string} id - Question ID.
 * @returns {Promise<Object>} The updated question record.
 */
export async function overrideQuestionDuplicate(id) {
  const res = await fetch(`${API_BASE}/questions/${id}/override-duplicate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' }
  });
  await assertOk(res, `Override duplicate on question ${id}`);
  return res.json();
}

/**
 * Checks a candidate question for duplicates against the Question Bank on demand.
 * @param {Object} payload - Question payload with section, subtopic, question_stem, options.
 * @returns {Promise<Object>} Duplicate check result with similarity score and matched question.
 */
export async function checkQuestionDuplicate(payload) {
  const res = await fetch(`${API_BASE}/questions/check-duplicate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  });
  await assertOk(res, 'Check question duplicate');
  return res.json();
}

export async function startBackgroundBatch(payload) {
  const res = await fetch(`${API_BASE}/batches/start`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  });
  await assertOk(res, 'Start background batch');
  return res.json();
}

export async function fetchBatches(params = {}, signal = null) {
  const query = buildQuery(params);
  const res = await fetch(`${API_BASE}/batches?${query.toString()}`, { signal });
  await assertOk(res, 'Fetch batches');
  return res.json();
}

export async function fetchBatchDetail(batchId, signal = null) {
  const res = await fetch(`${API_BASE}/batches/${batchId}`, { signal });
  await assertOk(res, `Fetch batch ${batchId}`);
  return res.json();
}

export async function deleteBatch(batchId) {
  const res = await fetch(`${API_BASE}/batches/${batchId}`, { method: 'DELETE' });
  await assertOk(res, `Delete batch ${batchId}`);
  return res.json();
}

export async function stopBatch(batchId) {
  const res = await fetch(`${API_BASE}/batches/${batchId}/stop`, { method: 'POST' });
  await assertOk(res, `Stop batch ${batchId}`);
  return res.json();
}

export async function retryBatchJobs(batchId, payload = null) {
  const res = await fetch(`${API_BASE}/batches/${batchId}/retry`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: payload ? JSON.stringify(payload) : undefined
  });
  await assertOk(res, `Retry batch ${batchId}`);
  return res.json();
}

export async function cancelAllBatches() {
  const res = await fetch(`${API_BASE}/batches/cancel-all`, { method: 'POST' });
  await assertOk(res, 'Cancel all active batches');
  return res.json();
}

export async function fetchBatchDuplicateClusters(batchId, threshold = 0.75, signal = null) {
  const res = await fetch(`${API_BASE}/batches/${batchId}/duplicate-clusters?threshold=${threshold}`, { signal });
  await assertOk(res, `Fetch duplicate clusters for batch ${batchId}`);
  return res.json();
}

export async function resolveBatchDuplicates(batchId, payload = { action: 'delete' }) {
  const res = await fetch(`${API_BASE}/batches/${batchId}/resolve-duplicates`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  });
  await assertOk(res, `Resolve duplicates for batch ${batchId}`);
  return res.json();
}

export async function refillBatchQuestions(batchId) {
  const res = await fetch(`${API_BASE}/batches/${batchId}/refill`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' }
  });
  await assertOk(res, `Refill batch ${batchId}`);
  return res.json();
}

// ── Passages API ─────────────────────────────────────────────────────────────

export async function fetchPassages(params = {}, signal = null) {
  const query = buildQuery(params);
  const res = await fetch(`${API_BASE}/passages?${query.toString()}`, { signal });
  await assertOk(res, 'Fetch passages');
  return res.json();
}

export async function fetchSinglePassage(passageId, signal = null) {
  const res = await fetch(`${API_BASE}/passages/${passageId}`, { signal });
  await assertOk(res, `Fetch passage ${passageId}`);
  return res.json();
}

export async function savePassage(passageData) {
  const res = await fetch(`${API_BASE}/passages`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(passageData)
  });
  await assertOk(res, 'Save passage');
  return res.json();
}

export async function deletePassage(passageId) {
  const res = await fetch(`${API_BASE}/passages/${passageId}`, { method: 'DELETE' });
  await assertOk(res, `Delete passage ${passageId}`);
  return res.json();
}
