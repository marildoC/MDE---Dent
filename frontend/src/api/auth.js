const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api'

async function request(path, options = {}) {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...(options.headers || {}),
    },
  })

  const data = await response.json().catch(() => ({}))

  if (!response.ok) {
    throw new Error(data.detail || 'Request failed')
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
