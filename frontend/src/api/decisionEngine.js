import { getAccessToken, request } from './auth.js'

function authHeaders() {
  const token = getAccessToken()
  return token ? { Authorization: `Bearer ${token}` } : {}
}

export function listRiskAssessments({ reportId } = {}) {
  const params = new URLSearchParams()
  if (reportId) {
    params.set('report', reportId)
  }
  const query = params.toString()
  return request(`/decision-engine/risk-assessments/${query ? `?${query}` : ''}`, {
    headers: authHeaders(),
  })
}

export function evaluateReport(reportId) {
  return request(`/decision-engine/reports/${reportId}/evaluate/`, {
    method: 'POST',
    body: JSON.stringify({}),
    headers: authHeaders(),
  })
}
