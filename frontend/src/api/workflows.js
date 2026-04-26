import { getAccessToken, request } from './auth.js'

function authHeaders() {
  const token = getAccessToken()
  return token ? { Authorization: `Bearer ${token}` } : {}
}

function api(path, options = {}) {
  return request(path, {
    ...options,
    headers: {
      ...authHeaders(),
      ...(options.headers || {}),
    },
  })
}

function createResource(path, payload) {
  return api(path, {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

function updateResource(path, payload) {
  return api(path, {
    method: 'PATCH',
    body: JSON.stringify(payload),
  })
}

export function listWorkflows() {
  return api('/workflows/treatment-workflows/')
}

export function getWorkflow(id) {
  return api(`/workflows/treatment-workflows/${id}/`)
}

export function createWorkflow(payload) {
  return createResource('/workflows/treatment-workflows/', payload)
}

export function updateWorkflow(id, payload) {
  return updateResource(`/workflows/treatment-workflows/${id}/`, payload)
}

export function listCareStages() {
  return api('/workflows/care-stages/')
}

export function createCareStage(payload) {
  return createResource('/workflows/care-stages/', payload)
}

export function listSymptomDefinitions() {
  return api('/workflows/symptom-definitions/')
}

export function createSymptomDefinition(payload) {
  return createResource('/workflows/symptom-definitions/', payload)
}

export function listSymptomRules() {
  return api('/workflows/symptom-rules/')
}

export function createSymptomRule(payload) {
  return createResource('/workflows/symptom-rules/', payload)
}

export function listAdviceBoundaries() {
  return api('/workflows/advice-boundaries/')
}

export function createAdviceBoundary(payload) {
  return createResource('/workflows/advice-boundaries/', payload)
}

export function listEscalationRules() {
  return api('/workflows/escalation-rules/')
}

export function createEscalationRule(payload) {
  return createResource('/workflows/escalation-rules/', payload)
}
