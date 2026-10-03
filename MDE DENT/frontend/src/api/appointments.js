import { getAccessToken, request } from './auth.js'

function authHeaders() {
  const token = getAccessToken()
  return token ? { Authorization: `Bearer ${token}` } : {}
}

export function listAppointments({ escalationCaseId, followUpCaseId } = {}) {
  const params = new URLSearchParams()
  if (escalationCaseId) {
    params.set('escalation_case', escalationCaseId)
  }
  if (followUpCaseId) {
    params.set('follow_up_case', followUpCaseId)
  }
  const query = params.toString()
  return request(`/appointments/appointments/${query ? `?${query}` : ''}`, {
    headers: authHeaders(),
  })
}

export function createAppointment(payload) {
  return request('/appointments/appointments/', {
    method: 'POST',
    body: JSON.stringify(payload),
    headers: authHeaders(),
  })
}

export function updateAppointment(appointmentId, payload) {
  return request(`/appointments/appointments/${appointmentId}/`, {
    method: 'PATCH',
    body: JSON.stringify(payload),
    headers: authHeaders(),
  })
}
