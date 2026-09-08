// Doctor Portal / clinical endpoints (spec section 7).
//   GET  /clinical/encounters
//   GET  /clinical/encounters/{id}
//   POST /clinical/encounters
//   GET  /clinical/treatment-advisor/{id}
//   POST /clinical/treatment-advisor
//   GET  /models/explanations/{encounter}/{treatment}
//   GET  /clinical/form-options

import { http, callOrMock } from './api'
import { E13_SAMPLE, E13_SAMPLE_NO_CANDIDATES, buildAdvisorFromContext } from '../mocks/e13Sample'
import { ENCOUNTERS, DOCTOR_DASHBOARD } from '../mocks/encounters'
import { FORM_OPTIONS } from '../mocks/master'

export function getFormOptions(opts) {
  return callOrMock(
    () => http('/clinical/form-options', opts),
    async () => FORM_OPTIONS
  )
}

export function getDoctorDashboard(opts) {
  return callOrMock(
    () => http('/clinical/dashboard', opts),
    async () => DOCTOR_DASHBOARD
  )
}

export function listEncounters(params = {}, opts) {
  const qs = new URLSearchParams(
    Object.entries(params).filter(([, v]) => v !== '' && v != null)
  ).toString()
  return callOrMock(
    () => http(`/clinical/encounters${qs ? `?${qs}` : ''}`, opts),
    async () => ({
      items: ENCOUNTERS.filter((e) => (params.hospital_id ? e.hospital_id === params.hospital_id : true)),
    })
  )
}

export function getEncounter(id, opts) {
  return callOrMock(
    () => http(`/clinical/encounters/${encodeURIComponent(id)}`, opts),
    async () => ENCOUNTERS.find((e) => e.encounter_id === id) || { ...ENCOUNTERS[0], encounter_id: id }
  )
}

export function createEncounter(payload, opts) {
  return callOrMock(
    () => http('/clinical/encounters', { method: 'POST', body: payload, ...opts }),
    async () => ({
      encounter_id: `ENC-DEMO-${Date.now().toString(36).toUpperCase()}`,
      status: 'CREATED',
      echo: payload,
    })
  )
}

export function getTreatmentAdvisor(encounterId, opts) {
  const isNoCand = String(encounterId || '').toUpperCase().includes('NOCAND')
  return callOrMock(
    () => http(`/clinical/treatment-advisor/${encodeURIComponent(encounterId)}`, opts),
    async () => ({
      ...(isNoCand ? E13_SAMPLE_NO_CANDIDATES : E13_SAMPLE),
      encounter_id: encounterId || E13_SAMPLE.encounter_id,
    })
  )
}

export function runTreatmentAdvisor(context, opts) {
  return callOrMock(
    () => http('/clinical/treatment-advisor', { method: 'POST', body: context, ...opts }),
    async () => buildAdvisorFromContext(context)
  )
}

export function getExplanation(encounterId, treatmentId, opts) {
  return callOrMock(
    () =>
      http(
        `/models/explanations/${encodeURIComponent(encounterId)}/${encodeURIComponent(treatmentId)}`,
        opts
      ),
    async () => {
      const rec =
        E13_SAMPLE.recommendations.find((r) => r.treatment_id === treatmentId) ||
        E13_SAMPLE.recommendations[0]
      return {
        encounter_id: encounterId,
        treatment_id: rec.treatment_id,
        treatment_name: rec.treatment_name,
        explainability: rec.explainability,
      }
    }
  )
}
