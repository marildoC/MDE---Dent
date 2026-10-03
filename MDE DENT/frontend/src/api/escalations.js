import { getAccessToken, request } from './auth.js'

function authHeaders() {
  const token = getAccessToken()
  return token ? { Authorization: `Bearer ${token}` } : {}
}

export function listEscalationCases({ followUpCaseId, reportId } = {}) {
  const params = new URLSearchParams()
  if (followUpCaseId) {
    params.set('follow_up_case', followUpCaseId)
  }
  if (reportId) {
    params.set('report', reportId)
  }
  const query = params.toString()
  return request(`/escalations/cases/${query ? `?${query}` : ''}`, {
    headers: authHeaders(),
  })
}

export function updateEscalationCase(caseId, payload) {
  return request(`/escalations/cases/${caseId}/`, {
    method: 'PATCH',
    body: JSON.stringify(payload),
    headers: authHeaders(),
  })
}
