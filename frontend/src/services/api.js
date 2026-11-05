/**
 * @module api
 * @description Typed HTTP client for the Question Bank Generator REST API.
 * All functions throw a descriptive Error on non-2xx responses via {@link assertOk}.
 */

// API Service for communicating with backend API
const API_BASE = '/api';

// Optional shared secret (backend API_ACCESS_KEY). Unset by default, so local use is unchanged.
const API_ACCESS_KEY = import.meta.env.VITE_API_ACCESS_KEY || '';

/**
 * fetch wrapper that adds the optional X-API-Key header to every API call.
 * @param {string} url
 * @param {RequestInit} [init]
 * @returns {Promise<Response>}
 */
function apiFetch(url, init = {}) {
  if (!API_ACCESS_KEY) return fetch(url, init);
  return fetch(url, { ...init, headers: { ...(init.headers || {}), 'X-API-Key': API_ACCESS_KEY } });
}

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
  const res = await apiFetch(`${API_BASE}/health`);
  await assertOk(res, 'Health check');
  return res.json();
}

export async function fetchSections() {
  const res = await apiFetch(`${API_BASE}/sections`);
  await assertOk(res, 'Fetch sections');
  return res.json();
}

export async function fetchQuestions(params = {}, signal = null) {
  const query = buildQuery(params);
  const res = await apiFetch(`${API_BASE}/questions?${query.toString()}`, { signal });
  await assertOk(res, 'Fetch questions');
  return res.json();
}

export async function fetchQuestionCounts(signal = null) {
  const res = await apiFetch(`${API_BASE}/questions/counts`, { signal });
  await assertOk(res, 'Fetch question counts');
  return res.json();
}

export async function updateQuestionStatus(id, status) {
  const res = await apiFetch(`${API_BASE}/questions/${id}/status`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ status })
  });
  await assertOk(res, `Update question ${id} status to ${status}`);
  return res.json();
}

export async function batchUpdateQuestionStatus(ids, status) {
  const res = await apiFetch(`${API_BASE}/questions/update-status`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ ids, status })
  });
  await assertOk(res, `Bulk update questions status to ${status}`);
  return res.json();
}

export async function fetchQuestionById(id) {
  const res = await apiFetch(`${API_BASE}/questions/${id}`);
  await assertOk(res, `Fetch question ${id}`);
  return res.json();
}

export async function deleteQuestion(id) {
  const res = await apiFetch(`${API_BASE}/questions/${id}`, { method: 'DELETE' });
  await assertOk(res, `Delete question ${id}`);
  return res.json();
}

export async function batchDeleteQuestions(ids) {
  const res = await apiFetch(`${API_BASE}/questions/delete-batch`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ ids })
  });
  await assertOk(res, 'Bulk delete questions');
  return res.json();
}

export async function purgeQuestion(id) {
  const res = await apiFetch(`${API_BASE}/questions/${id}/permanent`, {
    method: 'DELETE'
  });
  await assertOk(res, `Purge question ${id}`);
  return res.json();
}

export async function purgeQuestionsBatch(ids) {
  const res = await apiFetch(`${API_BASE}/questions/purge-batch`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ ids })
  });
  await assertOk(res, 'Purge questions batch');
  return res.json();
}

export async function restoreQuestion(id) {
  const res = await apiFetch(`${API_BASE}/questions/${id}/restore`, {
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
async function approveQuestion(question) {
  const res = await apiFetch(`${API_BASE}/questions`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(question)
  });
  await assertOk(res, 'Save approved question');
  return res.json();
}

// List endpoints return slim questions (large audit columns emptied for speed). Saving such an
// object back through POST /questions would overwrite the stored audit data with empties.
const AUDIT_FIELDS = ['stage_outcomes', 'iterations_history', 'token_usage_details'];

const isEmptyAudit = (value) =>
  value == null ||
  (Array.isArray(value) && value.length === 0) ||
  (typeof value === 'object' && !Array.isArray(value) && Object.keys(value).length === 0);

/**
 * Saves an edited question without losing its stored audit history: the full record is fetched
 * and any audit field missing from the edited copy is restored before saving.
 * @param {Object} edited - The edited question (possibly a slim list item).
 * @returns {Promise<Object>} The saved question record as returned by the API.
 */
export async function saveEditedQuestion(edited) {
  const full = await fetchQuestionById(edited.id);
  const merged = { ...full, ...edited };
  for (const field of AUDIT_FIELDS) {
    if (isEmptyAudit(edited[field]) && !isEmptyAudit(full[field])) merged[field] = full[field];
  }
  return approveQuestion(merged);
}

export async function startBackgroundBatch(payload) {
  const res = await apiFetch(`${API_BASE}/batches/start`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  });
  await assertOk(res, 'Start background batch');
  return res.json();
}

export async function fetchBatches(params = {}, signal = null) {
  const query = buildQuery(params);
  const res = await apiFetch(`${API_BASE}/batches?${query.toString()}`, { signal });
  await assertOk(res, 'Fetch batches');
  return res.json();
}

export async function fetchBatchDetail(batchId, signal = null) {
  const res = await apiFetch(`${API_BASE}/batches/${batchId}`, { signal });
  await assertOk(res, `Fetch batch ${batchId}`);
  return res.json();
}

export async function deleteBatch(batchId) {
  const res = await apiFetch(`${API_BASE}/batches/${batchId}`, { method: 'DELETE' });
  await assertOk(res, `Delete batch ${batchId}`);
  return res.json();
}

export async function stopBatch(batchId) {
  const res = await apiFetch(`${API_BASE}/batches/${batchId}/stop`, { method: 'POST' });
  await assertOk(res, `Stop batch ${batchId}`);
  return res.json();
}

export async function retryBatchJobs(batchId, payload = null) {
  const res = await apiFetch(`${API_BASE}/batches/${batchId}/retry`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: payload ? JSON.stringify(payload) : undefined
  });
  await assertOk(res, `Retry batch ${batchId}`);
  return res.json();
}

export async function cancelAllBatches() {
  const res = await apiFetch(`${API_BASE}/batches/cancel-all`, { method: 'POST' });
  await assertOk(res, 'Cancel all active batches');
  return res.json();
}

// ── Passages API ─────────────────────────────────────────────────────────────

export async function fetchPassages(params = {}, signal = null) {
  const query = buildQuery(params);
  const res = await apiFetch(`${API_BASE}/passages?${query.toString()}`, { signal });
  await assertOk(res, 'Fetch passages');
  return res.json();
}

export async function fetchSinglePassage(passageId, signal = null) {
  const res = await apiFetch(`${API_BASE}/passages/${passageId}`, { signal });
  await assertOk(res, `Fetch passage ${passageId}`);
  return res.json();
}

export async function savePassage(passageData) {
  const res = await apiFetch(`${API_BASE}/passages`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(passageData)
  });
  await assertOk(res, 'Save passage');
  return res.json();
}

export async function deletePassage(passageId) {
  const res = await apiFetch(`${API_BASE}/passages/${passageId}`, { method: 'DELETE' });
  await assertOk(res, `Delete passage ${passageId}`);
  return res.json();
}
