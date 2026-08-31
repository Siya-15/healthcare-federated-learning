// Single point of contact with the backend.
//
// Integration rule (md_files/04_BACKEND_FRONTEND_INTEGRATION.md): the frontend
// consumes backend JSON only. It never connects to PostgreSQL and never
// imports the Python ML modules. Every network call in this app goes through
// this file.

const BASE = '/api'

async function get(path) {
  const res = await fetch(`${BASE}${path}`)
  if (!res.ok) throw new Error(`GET ${path} failed: ${res.status}`)
  return res.json()
}

async function post(path, body) {
  const res = await fetch(`${BASE}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  if (!res.ok) {
    const detail = await res.json().catch(() => ({}))
    throw new Error(detail.detail || `POST ${path} failed: ${res.status}`)
  }
  return res.json()
}

export const api = {
  dashboard: () => get('/dashboard'),
  surveillance: () => get('/surveillance'),
  flStatus: () => get('/federated-learning/status'),
  privacy: () => get('/privacy/status'),
  hospitals: () => get('/hospitals'),
  encounters: (params = {}) => {
    const q = new URLSearchParams(
      Object.entries(params).filter(([, v]) => v !== '' && v != null)
    )
    return get(`/encounters?${q}`)
  },
  encounter: (token) => get(`/encounters/${token}`),
  treatmentOptions: () => get('/treatment/options'),
  recommend: (payload) => post('/treatment/recommend', payload),
}
