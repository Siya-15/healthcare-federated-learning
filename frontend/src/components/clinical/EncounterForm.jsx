import { useState } from 'react'
import { Card } from '../common/ui'

// Clinical context entry. Field names follow the spec section 8 request shape
// (note: `temperature`, not `temp`). Options come from master data.
const VITALS = [
  ['temperature', 'Temperature (°C)', 38.2],
  ['heart_rate', 'Heart rate (bpm)', 96],
  ['respiratory_rate', 'Respiratory rate (/min)', 18],
  ['systolic_bp', 'Systolic BP (mmHg)', 120],
  ['diastolic_bp', 'Diastolic BP (mmHg)', 78],
  ['spo2', 'SpO₂ (%)', 97],
]

function num(v) {
  return v === '' || v === null || v === undefined ? null : Number(v)
}

export default function EncounterForm({ options, defaultHospital = 'H001', submitting, onSubmit }) {
  const { hospitals = [], diseases = [], severities = [], symptoms = [] } = options || {}
  const [form, setForm] = useState({
    hospital_id: defaultHospital,
    age: 45,
    gender: 'Female',
    temperature: 38.2,
    heart_rate: 96,
    respiratory_rate: 18,
    systolic_bp: 120,
    diastolic_bp: 78,
    spo2: 97,
    disease_id: diseases[2]?.disease_id || 'D003',
    severity_id: 'SV002',
    symptoms: ['Fever', 'Headache'],
  })

  const set = (k, v) => setForm((f) => ({ ...f, [k]: v }))
  const toggleSymptom = (s) =>
    setForm((f) => ({
      ...f,
      symptoms: f.symptoms.includes(s) ? f.symptoms.filter((x) => x !== s) : [...f.symptoms, s],
    }))

  const handleSubmit = (e) => {
    e.preventDefault()
    onSubmit({
      ...form,
      age: num(form.age),
      ...Object.fromEntries(VITALS.map(([k]) => [k, num(form[k])])),
    })
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <Card title="Demographics & context">
        <div className="grid gap-3 sm:grid-cols-3">
          <label className="text-sm">
            <span className="mb-1 block text-xs font-medium text-slate-400">Hospital</span>
            <select
              value={form.hospital_id}
              onChange={(e) => set('hospital_id', e.target.value)}
              className="w-full rounded-md border border-white/15 px-2 py-1.5 text-sm"
            >
              {hospitals.map((h) => (
                <option key={h.hospital_id} value={h.hospital_id}>
                  {h.hospital_id}
                </option>
              ))}
            </select>
          </label>
          <label className="text-sm">
            <span className="mb-1 block text-xs font-medium text-slate-400">Age</span>
            <input
              type="number"
              min="0"
              max="120"
              value={form.age}
              onChange={(e) => set('age', e.target.value)}
              className="w-full rounded-md border border-white/15 px-2 py-1.5 text-sm"
            />
          </label>
          <label className="text-sm">
            <span className="mb-1 block text-xs font-medium text-slate-400">Gender</span>
            <select
              value={form.gender}
              onChange={(e) => set('gender', e.target.value)}
              className="w-full rounded-md border border-white/15 px-2 py-1.5 text-sm"
            >
              <option>Female</option>
              <option>Male</option>
              <option>Other</option>
            </select>
          </label>
          <label className="text-sm">
            <span className="mb-1 block text-xs font-medium text-slate-400">Disease</span>
            <select
              value={form.disease_id}
              onChange={(e) => set('disease_id', e.target.value)}
              className="w-full rounded-md border border-white/15 px-2 py-1.5 text-sm"
            >
              {diseases.map((d) => (
                <option key={d.disease_id} value={d.disease_id}>
                  {d.disease_name}
                </option>
              ))}
            </select>
          </label>
          <label className="text-sm">
            <span className="mb-1 block text-xs font-medium text-slate-400">Severity</span>
            <select
              value={form.severity_id}
              onChange={(e) => set('severity_id', e.target.value)}
              className="w-full rounded-md border border-white/15 px-2 py-1.5 text-sm"
            >
              {severities.map((s) => (
                <option key={s.severity_id} value={s.severity_id}>
                  {s.severity_label}
                </option>
              ))}
            </select>
          </label>
        </div>
      </Card>

      <Card title="Vitals">
        <div className="grid gap-3 sm:grid-cols-3">
          {VITALS.map(([k, label]) => (
            <label key={k} className="text-sm">
              <span className="mb-1 block text-xs font-medium text-slate-400">{label}</span>
              <input
                type="number"
                step="any"
                value={form[k]}
                onChange={(e) => set(k, e.target.value)}
                className="w-full rounded-md border border-white/15 px-2 py-1.5 text-sm"
              />
            </label>
          ))}
        </div>
      </Card>

      <Card title={`Symptoms (${form.symptoms.length}/27)`}>
        <div className="grid grid-cols-2 gap-x-4 gap-y-1.5 sm:grid-cols-3">
          {symptoms.map((s) => (
            <label key={s} className="flex items-center gap-2 text-sm text-slate-300">
              <input
                type="checkbox"
                checked={form.symptoms.includes(s)}
                onChange={() => toggleSymptom(s)}
                className="rounded border-white/15"
              />
              {s}
            </label>
          ))}
        </div>
      </Card>

      <div className="flex justify-end">
        <button
          type="submit"
          disabled={submitting}
          className="rounded-md bg-accent-blue px-4 py-2 text-sm font-semibold text-white hover:bg-accent-blue/90 disabled:opacity-50"
        >
          {submitting ? 'Analyzing…' : 'Analyze — run E1–E12'}
        </button>
      </div>
    </form>
  )
}
