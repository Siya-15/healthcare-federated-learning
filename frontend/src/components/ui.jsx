// Small shared presentational pieces.

const ALERT_STYLES = {
  GREEN: 'bg-green-100 text-green-800 border-green-300',
  YELLOW: 'bg-yellow-100 text-yellow-800 border-yellow-300',
  ORANGE: 'bg-orange-100 text-orange-800 border-orange-300',
  RED: 'bg-red-100 text-red-800 border-red-300',
}

export function AlertBadge({ level }) {
  return (
    <span
      className={`inline-block rounded-full border px-3 py-0.5 text-xs font-semibold tracking-wide ${
        ALERT_STYLES[level] || 'bg-slate-100 text-slate-700 border-slate-300'
      }`}
    >
      {level}
    </span>
  )
}

export function Card({ title, subtitle, children, className = '' }) {
  return (
    <div className={`rounded-xl border border-slate-200 bg-white p-5 shadow-sm ${className}`}>
      {title && (
        <div className="mb-3">
          <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-500">
            {title}
          </h2>
          {subtitle && <p className="mt-0.5 text-xs text-slate-400">{subtitle}</p>}
        </div>
      )}
      {children}
    </div>
  )
}

export function Stat({ label, value, hint, tone = 'default' }) {
  const tones = {
    default: 'text-slate-900',
    good: 'text-green-700',
    warn: 'text-orange-700',
    bad: 'text-red-700',
  }
  return (
    <div>
      <div className="text-xs font-medium uppercase tracking-wide text-slate-500">{label}</div>
      <div className={`mt-1 text-2xl font-bold ${tones[tone]}`}>{value}</div>
      {hint && <div className="mt-0.5 text-xs text-slate-400">{hint}</div>}
    </div>
  )
}

export function PassFail({ status }) {
  const ok = status === 'PASS'
  return (
    <span
      className={`rounded px-2 py-0.5 text-xs font-bold ${
        ok ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
      }`}
    >
      {status}
    </span>
  )
}

export function Loading({ what = 'data' }) {
  return <div className="p-8 text-sm text-slate-400">Loading {what}…</div>
}

export function ErrorBox({ error }) {
  return (
    <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-800">
      <p className="font-semibold">Could not reach the API.</p>
      <p className="mt-1 font-mono text-xs">{String(error.message || error)}</p>
      <p className="mt-2 text-xs text-red-700">
        Is the backend running? Start it with{' '}
        <code className="rounded bg-red-100 px-1">
          .venv/bin/uvicorn backend.app.main:app --reload
        </code>{' '}
        from the repo root.
      </p>
    </div>
  )
}

export function Disclaimer({ children }) {
  return (
    <div className="rounded-lg border border-amber-300 bg-amber-50 p-3 text-xs text-amber-900">
      {children}
    </div>
  )
}
