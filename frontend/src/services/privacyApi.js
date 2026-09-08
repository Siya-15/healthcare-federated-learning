// Privacy Portal endpoints (spec section 7): Objective C governance.
import { http, callOrMock } from './api'
import { PRIVACY_POLICY, PRIVACY_DATA_FLOW, PRIVACY_AUDIT } from '../mocks/privacy'

export function getPolicy(opts) {
  return callOrMock(() => http('/privacy/policy', opts), async () => PRIVACY_POLICY)
}

export function getDataFlow(opts) {
  return callOrMock(() => http('/privacy/data-flow', opts), async () => PRIVACY_DATA_FLOW)
}

export function getAudit(opts) {
  return callOrMock(() => http('/privacy/audit', opts), async () => PRIVACY_AUDIT)
}
