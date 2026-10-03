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

export function getMyActiveCase() {
  return api('/patients/my-active-case/')
}

export function listMyFollowUpCases() {
  return api('/patients/my-follow-up-cases/')
}

export function listPatientUsers() {
  return api('/patients/patient-users/')
}

export function listPatientProfiles() {
  return api('/patients/profiles/')
}

export function createPatientProfile(payload) {
  return createResource('/patients/profiles/', payload)
}

export function createPatientProfileWithUser(payload) {
  return createResource('/patients/profiles/create-with-user/', payload)
}

export function listFollowUpCases() {
  return api('/patients/follow-up-cases/')
}

export function createFollowUpCase(payload) {
  return createResource('/patients/follow-up-cases/', payload)
}
