import { API_BASE_URL, getAccessToken, request } from './auth.js'

function authHeaders() {
  const token = getAccessToken()
  return token ? { Authorization: `Bearer ${token}` } : {}
}

function formatApiError(data) {
  if (data.detail) {
    return data.detail
  }

  const firstField = Object.keys(data)[0]
  const firstError = firstField ? data[firstField] : null
  if (Array.isArray(firstError) && firstError.length > 0) {
    return `${firstField}: ${firstError[0]}`
  }
  if (firstError && typeof firstError === 'object') {
    const nestedField = Object.keys(firstError)[0]
    const nestedError = nestedField ? firstError[nestedField] : null
    if (Array.isArray(nestedError) && nestedError.length > 0) {
      return `${firstField}.${nestedField}: ${nestedError[0]}`
    }
    if (nestedError) {
      return `${firstField}.${nestedField}: ${nestedError}`
    }
  }

  return 'Request failed'
}

export function listSymptomReports({ followUpCaseId } = {}) {
  const params = new URLSearchParams()
  if (followUpCaseId) {
    params.set('follow_up_case', followUpCaseId)
  }
  const query = params.toString()
  return request(`/reports/symptom-reports/${query ? `?${query}` : ''}`, {
    headers: authHeaders(),
  })
}

export async function createSymptomReport(payload) {
  const formData = new FormData()
  formData.append('follow_up_case', payload.follow_up_case)
  formData.append('symptom_values', JSON.stringify(payload.symptom_values || {}))
  if (payload.pain_level !== undefined) {
    formData.append('pain_level', payload.pain_level)
  }
  if (payload.swelling !== undefined) {
    formData.append('swelling', payload.swelling)
  }
  if (payload.bleeding !== undefined) {
    formData.append('bleeding', payload.bleeding)
  }
  if (payload.fever !== undefined) {
    formData.append('fever', payload.fever ? 'true' : 'false')
  }
  if (payload.bad_smell !== undefined) {
    formData.append('bad_smell', payload.bad_smell ? 'true' : 'false')
  }
  formData.append('notes', payload.notes || '')
  if (payload.image) {
    formData.append('image', payload.image)
  }

  const response = await fetch(`${API_BASE_URL}/reports/symptom-reports/`, {
    method: 'POST',
    headers: authHeaders(),
    body: formData,
  })
  const data = await response.json().catch(() => ({}))

  if (!response.ok) {
    throw new Error(formatApiError(data))
  }

  return data
}
