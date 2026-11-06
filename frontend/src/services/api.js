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

/** Joins a path and its non-empty query parameters. */
function withQuery(path, params) {
  const query = buildQuery(params).toString();
  return query ? `${path}?${query}` : path;
}

/**
 * One API call: JSON body in (when given), JSON body out, descriptive Error on non-2xx.
 * @param {string} path - Path under /api.
 * @param {{method?: string, body?: any, signal?: AbortSignal|null, context: string}} opts
 */
async function request(path, { method = 'GET', body, signal = null, context } = {}) {
  const init = { method, signal };
  if (body !== undefined) {
    init.headers = { 'Content-Type': 'application/json' };
    init.body = JSON.stringify(body);
  }
  const res = await apiFetch(`${API_BASE}${path}`, init);
  await assertOk(res, context);
  return res.json();
}

export const fetchHealth = () => request('/health', { context: 'Health check' });

export const fetchSections = () => request('/sections', { context: 'Fetch sections' });

export const fetchQuestions = (params = {}, signal = null) =>
  request(withQuery('/questions', params), { signal, context: 'Fetch questions' });

export const fetchQuestionCounts = (signal = null) =>
  request('/questions/counts', { signal, context: 'Fetch question counts' });

export const updateQuestionStatus = (id, status) =>
  request(`/questions/${id}/status`, {
    method: 'PATCH',
    body: { status },
    context: `Update question ${id} status to ${status}`
  });

export const batchUpdateQuestionStatus = (ids, status) =>
  request('/questions/update-status', {
    method: 'POST',
    body: { ids, status },
    context: `Bulk update questions status to ${status}`
  });

export const fetchQuestionById = (id, signal = null) =>
  request(`/questions/${id}`, { signal, context: `Fetch question ${id}` });

export const deleteQuestion = (id) =>
  request(`/questions/${id}`, { method: 'DELETE', context: `Delete question ${id}` });

export const batchDeleteQuestions = (ids) =>
  request('/questions/delete-batch', { method: 'POST', body: { ids }, context: 'Bulk delete questions' });

export const purgeQuestion = (id) =>
  request(`/questions/${id}/permanent`, { method: 'DELETE', context: `Purge question ${id}` });

export const purgeQuestionsBatch = (ids) =>
  request('/questions/purge-batch', { method: 'POST', body: { ids }, context: 'Purge questions batch' });

export const restoreQuestion = (id) =>
  request(`/questions/${id}/restore`, { method: 'POST', context: `Restore question ${id}` });

/**
 * Approves and saves a single question to the Question Bank (status `in_bank`, DB-assigned id).
 * @param {Object} question - Full Question schema object.
 * @returns {Promise<Object>} The saved question record.
 */
const approveQuestion = (question) =>
  request('/questions', { method: 'POST', body: question, context: 'Save approved question' });

// List endpoints return slim questions (large audit columns emptied for speed). Saving such an
// object back through POST /questions would overwrite the stored audit data with empties.
const AUDIT_FIELDS = ['stage_outcomes', 'iterations_history', 'token_usage_details'];

const isEmptyAudit = (value) =>
  value === null ||
  value === undefined ||
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

export const startBackgroundBatch = (payload) =>
  request('/batches/start', { method: 'POST', body: payload, context: 'Start background batch' });

export const fetchBatches = (params = {}, signal = null) =>
  request(withQuery('/batches', params), { signal, context: 'Fetch batches' });

export const fetchBatchDetail = (batchId, signal = null) =>
  request(`/batches/${batchId}`, { signal, context: `Fetch batch ${batchId}` });

export const deleteBatch = (batchId) =>
  request(`/batches/${batchId}`, { method: 'DELETE', context: `Delete batch ${batchId}` });

export const stopBatch = (batchId) =>
  request(`/batches/${batchId}/stop`, { method: 'POST', context: `Stop batch ${batchId}` });

export const retryBatchJobs = (batchId, payload = null) =>
  request(`/batches/${batchId}/retry`, {
    method: 'POST',
    body: payload || undefined,
    context: `Retry batch ${batchId}`
  });

export const cancelAllBatches = () =>
  request('/batches/cancel-all', { method: 'POST', context: 'Cancel all active batches' });

// ── Passages API ─────────────────────────────────────────────────────────────

export const fetchPassages = (params = {}, signal = null) =>
  request(withQuery('/passages', params), { signal, context: 'Fetch passages' });

export const fetchSinglePassage = (passageId, signal = null) =>
  request(`/passages/${passageId}`, { signal, context: `Fetch passage ${passageId}` });

export const savePassage = (passageData) =>
  request('/passages', { method: 'POST', body: passageData, context: 'Save passage' });

export const deletePassage = (passageId) =>
  request(`/passages/${passageId}`, { method: 'DELETE', context: `Delete passage ${passageId}` });
