import { Tag } from '../common/ui'

// Reference ranges for a quick in/out-of-range dot (visual only, not a clinical
// judgement). Keyed to the vitals we collect.
const RANGE = {
  temperature_c: [36.1, 37.8],
  heart_rate: [60, 100],
  respiratory_rate: [12, 20],
  spo2: [94, 100],
  systolic_bp: [90, 140],
  diastolic_bp: [60, 90],
}
const VLABEL = {
  temperature_c: 'Temp',
  heart_rate: 'HR',
  respiratory_rate: 'RR',
  spo2: 'SpO₂',
  systolic_bp: 'SBP',
  diastolic_bp: 'DBP',
}

function inRange(k, v) {
  const r = RANGE[k]
  if (!r || v == null) return null
  return v >= r[0] && v <= r[1]
}

// E1 patient context — compact form for a bento tile.
export default function PatientContextCard({ context }) {
  if (!context) return <p className="text-sm text-slate-500">No patient context available.</p>

  const { age, gender, symptoms = [], vitals = {}, comorbidity_flags = [], pregnancy_flag } = context

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-sm">
        <span>
          <span className="text-slate-500">Age</span> <span className="font-semibold text-slate-100">{age ?? '—'}</span>
        </span>
        <span>
          <span className="text-slate-500">Sex</span> <span className="font-semibold text-slate-100">{gender ?? '—'}</span>
        </span>
        {comorbidity_flags.map((c) => (
          <Tag key={c} tone="amber">
            {c}
          </Tag>
        ))}
        {pregnancy_flag && <Tag tone="amber">Pregnancy</Tag>}
      </div>

      <div className="grid grid-cols-3 gap-1.5">
        {Object.keys(VLABEL).map((k) => {
          const v = vitals[k]
          const ok = inRange(k, v)
          return (
            <div key={k} className="rounded-lg bg-white/5 px-2 py-1.5">
              <div className="flex items-center gap-1 text-[10px] uppercase tracking-wide text-slate-500">
                {ok === false && <span className="h-1.5 w-1.5 rounded-full bg-orange-400" />}
                {ok === true && <span className="h-1.5 w-1.5 rounded-full bg-emerald-400" />}
                {VLABEL[k]}
              </div>
              <div className="text-sm font-semibold text-slate-100">{v ?? '—'}</div>
            </div>
          )
        })}
      </div>

      <div className="flex flex-wrap gap-1">
        {symptoms.length ? (
          symptoms.map((s) => (
            <span key={s} className="rounded bg-white/5 px-1.5 py-0.5 text-[11px] text-slate-300">
              {s}
            </span>
          ))
        ) : (
          <span className="text-xs text-slate-500">No symptoms recorded</span>
        )}
      </div>
    </div>
  )
}
