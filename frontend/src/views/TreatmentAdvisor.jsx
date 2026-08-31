import { useEffect, useState } from 'react'

import { api } from '../api/client'
import { useApi } from '../components/useApi'
import { Card, Disclaimer, ErrorBox, Loading } from '../components/ui'

const BLANK = {
  age: 45,
  gender: 'Male',
  temperature: 37.7,
  heart_rate: 78,
  respiratory_rate: 17,
  systolic_bp: 111,
  diastolic_bp: 67,
  spo2: 97,
  disease_id: 'D004',
  severity_id: 'SV001',
  symptoms: [],
}

function Field({ label, children }) {
  return (
    <label className="block">
      <span className="text-xs font-medium uppercase tracking-wide text-slate-500">{label}</span>
      {children}
    </label>
  )
}

const inputCls =
  'mt-1 w-full rounded-lg border border-slate-300 px-3 py-1.5 text-sm focus:border-slate-900 focus:outline-none'

export default function TreatmentAdvisor() {
  const options = useApi(api.treatmentOptions)
  const [form, setForm] = useState(BLANK)
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)
  const [busy, setBusy] = useState(false)

  const set = (k, v) => setForm((f) => ({ ...f, [k]: v }))

  const toggleSymptom = (s) =>
    setForm((f) => ({
      ...f,
      symptoms: f.symptoms.includes(s)
        ? f.symptoms.filter((x) => x !== s)
        : [...f.symptoms, s],
    }))

  async function submit(e) {
    e.preventDefault()
    setBusy(true)
    setError(null)
    try {
      setResult(await api.recommend(form))
    } catch (err) {
      setError(err)
    } finally {
      setBusy(false)
    }
  }

  // Run once on load so the view is never empty for a demo.
  useEffect(() => {
    api.recommend(BLANK).then(setResult).catch(setError)
  }, [])

  if (options.loading) return <Loading what="treatment options" />
  if (options.error) return <ErrorBox error={options.error} />

  return (
    <div className="space-y-4">
      <Disclaimer>
        <strong>Clinical decision support only.</strong> These rankings are model output over
        simulated data. They are not a prescription and require review by a qualified clinician.
      </Disclaimer>

      <div className="grid gap-5 lg:grid-cols-[400px_1fr]">
        <Card title="Patient input">
          <form onSubmit={submit} className="space-y-3">
            <div className="grid grid-cols-2 gap-3">
              <Field label="Age">
                <input
                  type="number" min="0" max="120" value={form.age}
                  onChange={(e) => set('age', Number(e.target.value))}
                  className={inputCls}
                />
              </Field>
              <Field label="Gender">
                <select
                  value={form.gender} onChange={(e) => set('gender', e.target.value)}
                  className={inputCls}
                >
                  <option>Male</option>
                  <option>Female</option>
                </select>
              </Field>
            </div>

            <div className="grid grid-cols-3 gap-3">
              <Field label="Temp °C">
                <input type="number" step="0.1" value={form.temperature}
                  onChange={(e) => set('temperature', Number(e.target.value))} className={inputCls} />
              </Field>
              <Field label="HR">
                <input type="number" value={form.heart_rate}
                  onChange={(e) => set('heart_rate', Number(e.target.value))} className={inputCls} />
              </Field>
              <Field label="RR">
                <input type="number" value={form.respiratory_rate}
                  onChange={(e) => set('respiratory_rate', Number(e.target.value))} className={inputCls} />
              </Field>
            </div>

            <div className="grid grid-cols-3 gap-3">
              <Field label="Systolic">
                <input type="number" value={form.systolic_bp}
                  onChange={(e) => set('systolic_bp', Number(e.target.value))} className={inputCls} />
              </Field>
              <Field label="Diastolic">
                <input type="number" value={form.diastolic_bp}
                  onChange={(e) => set('diastolic_bp', Number(e.target.value))} className={inputCls} />
              </Field>
              <Field label="SpO2 %">
                <input type="number" value={form.spo2}
                  onChange={(e) => set('spo2', Number(e.target.value))} className={inputCls} />
              </Field>
            </div>

            <Field label="Disease">
              <select value={form.disease_id} onChange={(e) => set('disease_id', e.target.value)}
                className={inputCls}>
                {options.data.diseases.map((d) => (
                  <option key={d.disease_id} value={d.disease_id}>
                    {d.disease_id} — {d.disease_name}
                  </option>
                ))}
              </select>
            </Field>

            <Field label="Severity">
              <select value={form.severity_id} onChange={(e) => set('severity_id', e.target.value)}
                className={inputCls}>
                {options.data.severities.map((s) => (
                  <option key={s.severity_id} value={s.severity_id}>
                    {s.severity_id} — {s.severity_name}
                  </option>
                ))}
              </select>
            </Field>

            <div>
              <span className="text-xs font-medium uppercase tracking-wide text-slate-500">
                Symptoms ({form.symptoms.length})
              </span>
              <div className="mt-2 flex max-h-40 flex-wrap gap-1.5 overflow-y-auto">
                {options.data.symptoms.map((s) => (
                  <button
                    key={s} type="button" onClick={() => toggleSymptom(s)}
                    className={`rounded-full px-2.5 py-1 text-xs transition ${
                      form.symptoms.includes(s)
                        ? 'bg-blue-600 text-white'
                        : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                    }`}
                  >
                    {s}
                  </button>
                ))}
              </div>
            </div>

            <button
              type="submit" disabled={busy}
              className="w-full rounded-lg bg-slate-900 py-2 text-sm font-semibold text-white transition hover:bg-slate-700 disabled:opacity-50"
            >
              {busy ? 'Ranking…' : 'Get recommendations'}
            </button>
          </form>
        </Card>

        <div className="space-y-5">
          {error && <ErrorBox error={error} />}

          {result && (
            <>
              <Card
                title="Ranked treatment options"
                subtitle={`${result.disease_name} (${result.disease_id}) · ${result.severity_name}`}
              >
                {result.recommendations.length === 0 ? (
                  <p className="text-sm text-slate-500">
                    No candidate treatments mapped for this disease and severity.
                  </p>
                ) : (
                  <ul className="space-y-3">
                    {result.recommendations.map((r) => (
                      <li key={r.treatment_id} className="rounded-lg border border-slate-200 p-3">
                        <div className="flex items-start justify-between gap-4">
                          <div>
                            <div className="flex items-center gap-2">
                              <span className="flex h-6 w-6 items-center justify-center rounded-full bg-slate-900 text-xs font-bold text-white">
                                {r.rank}
                              </span>
                              <span className="font-semibold text-slate-900">
                                {r.treatment_name}
                              </span>
                              <span className="font-mono text-xs text-slate-400">
                                {r.treatment_id}
                              </span>
                            </div>
                            <p className="mt-1 text-xs text-slate-500">{r.comments}</p>
                            <div className="mt-2 flex flex-wrap gap-1.5 text-[11px]">
                              <span className="rounded bg-slate-100 px-2 py-0.5">
                                priority {r.priority}
                              </span>
                              {r.first_line === 'Yes' && (
                                <span className="rounded bg-green-100 px-2 py-0.5 text-green-800">
                                  first line
                                </span>
                              )}
                              {r.referral_required === 'Yes' && (
                                <span className="rounded bg-orange-100 px-2 py-0.5 text-orange-800">
                                  referral required
                                </span>
                              )}
                            </div>
                          </div>
                          <div className="text-right">
                            <div className="text-2xl font-bold text-slate-900">
                              {r.success_probability}%
                            </div>
                            <div className="text-[11px] text-slate-400">predicted success</div>
                          </div>
                        </div>
                        <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-slate-100">
                          <div
                            className="h-full rounded-full bg-slate-900"
                            style={{ width: `${r.success_probability}%` }}
                          />
                        </div>
                      </li>
                    ))}
                  </ul>
                )}
              </Card>

              <div className="grid gap-5 sm:grid-cols-2">
                <Card title="Expected recovery">
                  <div className="text-3xl font-bold text-slate-900">
                    {result.expected_recovery_days ?? '—'}
                    <span className="ml-1 text-base font-normal text-slate-400">days</span>
                  </div>
                  <p className="mt-1 text-xs text-slate-500">
                    Historical mean across {result.recovery_cohort_size.toLocaleString()} comparable
                    encounters.
                  </p>
                </Card>

                <Card title="Potential complications">
                  {result.risks.length === 0 ? (
                    <p className="text-sm text-slate-500">None mapped for this disease.</p>
                  ) : (
                    <ul className="space-y-1.5">
                      {result.risks.map((r) => (
                        <li key={r.complication_id} className="flex items-center gap-2 text-sm">
                          <span className="text-amber-600">▲</span>
                          <span className="text-slate-700">{r.complication_name}</span>
                        </li>
                      ))}
                    </ul>
                  )}
                </Card>
              </div>

              <p className="text-xs text-slate-400">{result.disclaimer}</p>
            </>
          )}
        </div>
      </div>
    </div>
  )
}
