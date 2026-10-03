export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api'
export const ACCESS_TOKEN_KEY = 'dentcare_access_token'
export const REFRESH_TOKEN_KEY = 'dentcare_refresh_token'

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

export async function request(path, options = {}) {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...(options.headers || {}),
    },
  })

  const data = await response.json().catch(() => ({}))

  if (!response.ok) {
    throw new Error(formatApiError(data))
  }

  return data
}

export function loginRequest({ username, password }) {
  return request('/auth/login/', {
    method: 'POST',
    body: JSON.stringify({ username, password }),
  })
}

export function fetchCurrentUser(accessToken) {
  return request('/auth/me/', {
    headers: {
      Authorization: `Bearer ${accessToken}`,
    },
  })
}

export function getAccessToken() {
  return localStorage.getItem(ACCESS_TOKEN_KEY)
}
