// AI Operations / Transparency endpoints (spec section 7 & 12).
import { http, callOrMock } from './api'
import { MODEL_OVERVIEW, MODEL_METRICS, MODEL_VERSIONS } from '../mocks/models'

export { getExplanation } from './clinicalApi'

export function getModelOverview(opts) {
  return callOrMock(() => http('/models/overview', opts), async () => MODEL_OVERVIEW)
}

export function getModelMetrics(opts) {
  return callOrMock(() => http('/models/metrics', opts), async () => MODEL_METRICS)
}

export function getModelVersions(opts) {
  return callOrMock(
    () => http('/models/versions', opts),
    async () => ({ items: MODEL_VERSIONS })
  )
}
