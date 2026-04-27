import { getAccessToken, request } from './auth.js'

function authHeaders() {
  const token = getAccessToken()
  return token ? { Authorization: `Bearer ${token}` } : {}
}

export function listAuditLogs() {
  return request('/audit/logs/', {
    headers: authHeaders(),
  })
}
