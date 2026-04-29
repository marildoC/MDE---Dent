import { getAccessToken, request } from './auth.js'

function authHeaders() {
  const token = getAccessToken()
  return token ? { Authorization: `Bearer ${token}` } : {}
}

export function askAdminIntelligence(question) {
  return request('/admin-intelligence/query/', {
    method: 'POST',
    body: JSON.stringify({ question }),
    headers: authHeaders(),
  })
}

export function listAdminIntelligenceSuggestions(query = '') {
  const params = new URLSearchParams()
  if (query) {
    params.set('q', query)
  }
  const suffix = params.toString() ? `?${params.toString()}` : ''
  return request(`/admin-intelligence/suggestions/${suffix}`, {
    headers: authHeaders(),
  })
}
