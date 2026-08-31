import { useState } from 'react'

import { api } from '../api/client'
import { useApi } from '../components/useApi'
import { Card, ErrorBox, Loading } from '../components/ui'

const SEVERITY_STYLES = {
  Mild: 'bg-green-100 text-green-800',
  Moderate: 'bg-yellow-100 text-yellow-800',
  Severe: 'bg-red-100 text-red-800',
}

function Vital({ label, value, unit }) {
  return (
    <div className="rounded-lg bg-slate-50 p-3">
      <div className="text-[11px] font-medium uppercase tracking-wide text-slate-500">{label}</div>
      <div className="mt-0.5 text-lg font-semibold text-slate-900">
        {value}
        <span className="ml-1 text-xs font-normal text-slate-400">{unit}</span>
      </div>
    </div>
  )
}

function Detail({ label, value }) {
  return (
    <div className="flex justify-between gap-4 py-1.5 text-sm">
      <span className="text-slate-500">{label}</span>
      <span className="font-medium text-slate-800">{String(value)}</span>
    </div>
  )
}

export default function Clinical() {
  const [hospital, setHospital] = useState('')
  const [selected, setSelected] = useState(null)

  const hospitals = useApi(api.hospitals)
  const list = useApi(() => api.encounters({ hospital_id: hospital, limit: 40 }), [hospital])

  if (list.error) return <ErrorBox error={list.error} />

  const encounter = selected || list.data?.encounters?.[0]

  return (
    <div className="space-y-4">
      <Card>
        <div className="flex flex-wrap items-center gap-3">
          <label className="text-sm font-medium text-slate-600">Hospital</label>
          <select
            value={hospital}
            onChange={(e) => {
              setHospital(e.target.value)
              setSelected(null)
            }}
            className="rounded-lg border border-slate-300 px-3 py-1.5 text-sm"
          >
            <option value="">All hospitals</option>
            {hospitals.data?.hospitals?.map((h) => (
              <option key={h.hospital_id} value={h.hospital_id}>
                {h.hospital_id} ({h.encounter_count})
              </option>
            ))}
          </select>
          {list.data && (
            <span className="text-xs text-slate-400">
              showing {list.data.encounters.length} of {list.data.total.toLocaleString()}
            </span>
          )}
        </div>
      </Card>

      <div className="grid gap-5 lg:grid-cols-[380px_1fr]">
        <Card title="Encounters" subtitle="Identified by pseudonymous token only">
          {list.loading ? (
            <Loading what="encounters" />
          ) : (
            <ul className="max-h-[560px] space-y-1 overflow-y-auto pr-1">
              {list.data.encounters.map((e) => (
                <li key={e.patient_token}>
                  <button
                    onClick={() => setSelected(e)}
                    className={`w-full rounded-lg px-3 py-2 text-left transition ${
                      encounter?.patient_token === e.patient_token
                        ? 'bg-slate-900 text-white'
                        : 'hover:bg-slate-100'
                    }`}
                  >
                    <div className="font-mono text-xs">{e.patient_token}</div>
                    <div
                      className={`mt-0.5 text-xs ${
                        encounter?.patient_token === e.patient_token
                          ? 'text-slate-300'
                          : 'text-slate-500'
                      }`}
                    >
                      {e.hospital_id} · {e.disease_name} · {e.severity_name}
                    </div>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </Card>

        {encounter && (
          <Card>
            <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
              <div>
                <div className="font-mono text-sm font-semibold text-slate-900">
                  {encounter.patient_token}
                </div>
                <div className="mt-1 text-xs text-slate-500">
                  {encounter.age} yrs · {encounter.gender} · {encounter.occupation} ·{' '}
                  {encounter.hospital_id}
                </div>
              </div>
              <span
                className={`rounded-full px-3 py-1 text-xs font-semibold ${
                  SEVERITY_STYLES[encounter.severity_name] || 'bg-slate-100 text-slate-700'
                }`}
              >
                {encounter.disease_name} · {encounter.severity_name}
              </span>
            </div>

            <div className="mb-5 grid grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-6">
              <Vital label="Temp" value={encounter.vitals.temperature} unit="°C" />
              <Vital label="HR" value={encounter.vitals.heart_rate} unit="bpm" />
              <Vital label="RR" value={encounter.vitals.respiratory_rate} unit="/min" />
              <Vital
                label="BP"
                value={`${encounter.vitals.systolic_bp}/${encounter.vitals.diastolic_bp}`}
                unit="mmHg"
              />
              <Vital label="SpO2" value={encounter.vitals.spo2} unit="%" />
              <Vital label="Onset" value={encounter.symptom_onset_days} unit="days" />
            </div>

            <div className="grid gap-5 sm:grid-cols-2">
              <div>
                <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
                  Symptoms ({encounter.symptoms.length})
                </h3>
                <div className="flex flex-wrap gap-1.5">
                  {encounter.symptoms.map((s) => (
                    <span
                      key={s}
                      className="rounded-full bg-blue-50 px-2.5 py-1 text-xs text-blue-800"
                    >
                      {s}
                    </span>
                  ))}
                </div>
              </div>

              <div className="divide-y divide-slate-100">
                <Detail label="Admission" value={encounter.admission_status} />
                <Detail label="Visit type" value={encounter.visit_type} />
                <Detail label="Travel history" value={encounter.travel_history ? 'Yes' : 'No'} />
                <Detail label="Vaccination" value={encounter.vaccination_status} />
                <Detail label="Discharge" value={encounter.discharge_status} />
                <Detail label="Recovery days" value={encounter.recovery_days ?? '—'} />
              </div>
            </div>

            <p className="mt-5 rounded bg-slate-50 p-2 text-xs text-slate-500">
              Raw patient identifiers are never sent to this view. The token is a deterministic
              SHA-256 pseudonym generated by the backend.
            </p>
          </Card>
        )}
      </div>
    </div>
  )
}
