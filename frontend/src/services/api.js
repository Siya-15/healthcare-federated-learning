// Base HTTP layer. Every portal's service module builds on this.
//
// Integration rules (spec section 16):
//   - React talks to FastAPI only; it never calls Python or reads ML files.
//   - RBAC / hospital scope is enforced server-side. The frontend sends the
//     current demo role/hospital as headers so a real backend can act on them;
//     it does not rely on them for security.
//
// No backend exists on this branch yet, so calls resolve labelled fixtures by
// default. Once the FastAPI service is running, start the dev server with
// VITE_USE_MOCK=0 for live mode; in live mode a connection failure still falls
// back to a fixture, but real HTTP error statuses (401/403/404/422/501/503)
// propagate as ApiError.

const MOCK_FORCED = import.meta.env.VITE_USE_MOCK !== '0'

// Statuses that mean "the Vite proxy could not reach a FastAPI upstream" - only
// these trigger the fixture fallback in live mode. A real 500/503 from a running
// backend is surfaced as an error (spec section 9), never masked.
const UPSTREAM_DOWN = new Set([0, 502, 504])

let demoRole = 'DOCTOR'
let demoHospital = 'H001'

export function setDemoIdentity({ role, hospitalId }) {
  if (role) demoRole = role
  if (hospitalId) demoHospital = hospitalId
}

export class ApiError extends Error {
  constructor(message, { status = 0, body = null } = {}) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.body = body
  }
  get isNetwork() {
    return this.status === 0
  }
}

async function http(path, { method = 'GET', body, signal } = {}) {
  let res
  try {
    res = await fetch(`/api${path}`, {
      method,
      signal,
      headers: {
        Accept: 'application/json',
        ...(body ? { 'Content-Type': 'application/json' } : {}),
        'X-Demo-Role': demoRole,
        'X-Demo-Hospital': demoHospital,
      },
      body: body ? JSON.stringify(body) : undefined,
    })
  } catch (err) {
    if (err?.name === 'AbortError') throw err
    throw new ApiError(`Network error contacting ${path}`, { status: 0 })
  }

  if (!res.ok) {
    let parsed = null
    try {
      parsed = await res.json()
    } catch {
      /* non-JSON body */
    }
    const detail = parsed?.detail || `${res.status} ${res.statusText}`
    throw new ApiError(`${method} ${path} failed: ${detail}`, { status: res.status, body: parsed })
  }

  if (res.status === 204) return null
  return res.json()
}

// Try the real endpoint; on a pure connectivity failure fall back to `mock()`
// and tag the payload so the UI can show a "sample data" banner. HTTP error
// statuses are surfaced, never masked.
export async function callOrMock(realCall, mock) {
  if (MOCK_FORCED) return tag(await mock())
  try {
    return await realCall()
  } catch (err) {
    if (err instanceof ApiError && UPSTREAM_DOWN.has(err.status)) return tag(await mock())
    throw err
  }
}

function tag(value) {
  if (value && typeof value === 'object' && !Array.isArray(value)) return { ...value, _mock: true }
  return { data: value, _mock: true }
}

export { http }
