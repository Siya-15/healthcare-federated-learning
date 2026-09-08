// Surveillance Portal endpoints (spec section 7): Objectives A + B, aggregate only.
import { http, callOrMock } from './api'
import {
  SURVEILLANCE_OVERVIEW,
  SURVEILLANCE_ALERTS,
  EMERGING_SYMPTOMS,
  SURVEILLANCE_TRENDS,
} from '../mocks/surveillance'

export function getOverview(opts) {
  return callOrMock(() => http('/surveillance/overview', opts), async () => SURVEILLANCE_OVERVIEW)
}

export function getAlerts(opts) {
  return callOrMock(
    () => http('/surveillance/alerts', opts),
    async () => ({ items: SURVEILLANCE_ALERTS })
  )
}

export function getEmergingSymptoms(opts) {
  return callOrMock(
    () => http('/surveillance/emerging-symptoms', opts),
    async () => EMERGING_SYMPTOMS
  )
}

export function getTrends(opts) {
  return callOrMock(() => http('/surveillance/trends', opts), async () => SURVEILLANCE_TRENDS)
}
