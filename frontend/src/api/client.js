export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? '/api/v1'

function normalizeErrors(payload) {
  if (Array.isArray(payload?.errors) && payload.errors.length) {
    return payload.errors
      .map((error) => error?.message || error?.code)
      .filter(Boolean)
  }

  if (Array.isArray(payload?.detail)) {
    return payload.detail
      .map((item) => item?.msg || item?.message)
      .filter(Boolean)
  }

  if (typeof payload?.detail === 'string') {
    return [payload.detail]
  }

  if (typeof payload?.message === 'string') {
    return [payload.message]
  }

  return []
}

export function formatApiError(payload, fallbackMessage = 'Request failed.') {
  const messages = normalizeErrors(payload)
  return messages.length ? messages.join(' ') : fallbackMessage
}

async function request(path, options = {}) {
  const headers = {
    Accept: 'application/json',
    ...(options.body ? { 'Content-Type': 'application/json' } : {}),
    ...options.headers,
  }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers,
  })

  const payload = await response.json().catch(() => null)

  if (!response.ok || payload?.success === false) {
    throw new Error(
      formatApiError(payload, `${response.status} ${response.statusText}`),
    )
  }

  return payload?.data ?? null
}

export function getHealth() {
  return request('/health')
}

export function createHunt(payload) {
  return request('/hunts', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export function recommendCareer(payload) {
  return request('/recommend-career', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export function getHunt(huntId) {
  return request(`/hunts/${encodeURIComponent(huntId)}`)
}

export function getHuntJobs(huntId) {
  return request(`/hunts/${encodeURIComponent(huntId)}/jobs`)
}

export function getHuntApplications(huntId) {
  return request(`/hunts/${encodeURIComponent(huntId)}/applications`)
}

export function getAnalytics() {
  return request('/analytics')
}
