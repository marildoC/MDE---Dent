import { getAccessToken, request } from './auth.js'

function authHeaders() {
  const token = getAccessToken()
  return token ? { Authorization: `Bearer ${token}` } : {}
}

export function generateAdvice(assessmentId) {
  return request(`/ai-support/risk-assessments/${assessmentId}/generate-advice/`, {
    method: 'POST',
    body: JSON.stringify({}),
    headers: authHeaders(),
  })
}
