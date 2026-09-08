// Shared presentational primitives (dark clinical theme).
import { levelToneClass, classNames } from '../../utils/format'
import Sparkline from '../charts/Sparkline'

export function Card({ title, subtitle, right, children, className = '' }) {
  return (
    <section className={`rounded-2xl border border-line bg-ink-850 p-5 ${className}`}>
      {(title || right) && (
        <header className="mb-3 flex items-start justify-between gap-3">
          <div>
            {title && <h2 className="text-sm font-semibold text-slate-200">{title}</h2>}
            {subtitle && <p className="mt-0.5 text-xs text-slate-500">{subtitle}</p>}
          </div>
          {right}
        </header>
      )}
      {children}
    </section>
  )
}

export function PageHeader({ title, subtitle, children }) {
  return (
    <div className="mb-5 flex flex-wrap items-start justify-between gap-3">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-slate-50">{title}</h1>
        {subtitle && <p className="mt-1 text-sm text-slate-500">{subtitle}</p>}
      </div>
      {children}
    </div>
  )
}

export function StatusPill({ children = 'Live', tone = 'brand' }) {
  const tones = {
    brand: 'bg-brand/10 text-brand-fg border-brand/25',
    amber: 'bg-amber-500/10 text-amber-300 border-amber-500/25',
    slate: 'bg-white/5 text-slate-400 border-white/10',
  }
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-xs font-semibold ${
        tones[tone] || tones.brand
      }`}
    >
      <span className="h-1.5 w-1.5 rounded-full bg-current" />
      {children}
    </span>
  )
}

const ICON_TONES = {
  brand: 'bg-brand/12 text-brand-fg',
  blue: 'bg-accent-blue/15 text-accent-blue',
  orange: 'bg-orange-500/15 text-orange-300',
  purple: 'bg-accent-purple/15 text-accent-purple',
  slate: 'bg-white/5 text-slate-400',
}

export function IconTile({ children, tone = 'slate' }) {
  return (
    <span className={`inline-flex h-9 w-9 items-center justify-center rounded-xl text-base ${ICON_TONES[tone] || ICON_TONES.slate}`}>
      {children}
    </span>
  )
}

// A qualitative level pill (LOW / MODERATE / HIGH / GREEN…). Text verbatim.
export function LevelBadge({ value, className = '' }) {
  if (value === null || value === undefined || value === '') return <span className="text-slate-600">—</span>
  return (
    <span
      className={classNames(
        'inline-block whitespace-nowrap rounded-full border px-2.5 py-0.5 text-xs font-semibold tracking-wide',
        levelToneClass(value),
        className
      )}
    >
      {String(value)}
    </span>
  )
}

export function Tag({ children, tone = 'slate' }) {
  const tones = {
    slate: 'bg-white/5 text-slate-300',
    blue: 'bg-accent-blue/15 text-accent-blue',
    green: 'bg-emerald-500/15 text-emerald-300',
    amber: 'bg-amber-500/15 text-amber-300',
    red: 'bg-red-500/15 text-red-300',
  }
  return (
    <span className={`inline-block rounded-md px-2 py-0.5 text-xs font-medium ${tones[tone] || tones.slate}`}>
      {children}
    </span>
  )
}

export function Field({ label, children }) {
  return (
    <div>
      <dt className="text-xs font-medium uppercase tracking-wide text-slate-500">{label}</dt>
      <dd className="mt-0.5 text-sm text-slate-200">{children ?? '—'}</dd>
    </div>
  )
}

export function Stat({ label, value, hint }) {
  return (
    <div>
      <div className="text-xs font-medium uppercase tracking-wide text-slate-500">{label}</div>
      <div className="mt-1 text-2xl font-bold text-slate-50">{value}</div>
      {hint && <div className="mt-0.5 text-xs text-slate-500">{hint}</div>}
    </div>
  )
}

function DeltaLine({ delta, deltaTone }) {
  if (!delta) return null
  const tone =
    deltaTone === 'up'
      ? 'text-brand-fg'
      : deltaTone === 'down'
      ? 'text-red-300'
      : 'text-orange-300'
  const glyph = deltaTone === 'down' ? '▼' : '▲'
  return (
    <div className={`mt-2 flex items-center gap-1 text-xs font-medium ${tone}`}>
      <span>{glyph}</span>
      <span>{delta}</span>
    </div>
  )
}

// Rich KPI card: icon tile · label · big number · sparkline · delta.
export function KpiCard({ label, value, hint, delta, deltaTone = 'up', icon, iconTone = 'slate', spark, sparkColor }) {
  return (
    <div className="rounded-2xl border border-line bg-ink-850 p-4">
      <div className="flex items-start justify-between">
        {icon ? <IconTile tone={iconTone}>{icon}</IconTile> : <span />}
        {spark && (
          <Sparkline
            data={spark}
            color={sparkColor || (deltaTone === 'up' ? '#34d399' : '#fb923c')}
          />
        )}
      </div>
      <div className="mt-3 text-xs font-medium text-slate-500">{label}</div>
      <div className="mt-0.5 text-3xl font-bold tracking-tight text-slate-50">{value}</div>
      {hint && !delta && <div className="mt-1 text-xs text-slate-500">{hint}</div>}
      <DeltaLine delta={delta} deltaTone={deltaTone} />
    </div>
  )
}

export function KpiRow({ items }) {
  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
      {items.map((it) => (
        <KpiCard key={it.label} {...it} />
      ))}
    </div>
  )
}

export function InfoNote({ children, tone = 'slate' }) {
  const tones = {
    slate: 'border-line bg-white/[0.03] text-slate-400',
    amber: 'border-amber-500/25 bg-amber-500/10 text-amber-200',
    blue: 'border-accent-blue/25 bg-accent-blue/10 text-slate-300',
  }
  return (
    <div className={`rounded-xl border p-3 text-xs leading-relaxed ${tones[tone] || tones.slate}`}>
      {children}
    </div>
  )
}

// Shown wherever the prototype genuinely does not produce a value (spec §16).
export function NotImplemented({ label = 'NOT_IMPLEMENTED', detail }) {
  return (
    <span className="inline-flex items-center gap-1">
      <span className="rounded bg-white/10 px-1.5 py-0.5 font-mono text-[11px] font-semibold text-slate-400">
        {label}
      </span>
      {detail && <span className="text-xs text-slate-500">{detail}</span>}
    </span>
  )
}

export function Skeleton({ className = '' }) {
  return <div className={`animate-pulse rounded-xl bg-white/5 ${className}`} />
}

export function Loading({ rows = 3 }) {
  return (
    <div className="space-y-3">
      {Array.from({ length: rows }).map((_, i) => (
        <Skeleton key={i} className="h-24 w-full" />
      ))}
    </div>
  )
}

export function LoadingAdvisor() {
  return (
    <div className="space-y-4">
      <Skeleton className="h-24 w-full" />
      <div className="grid gap-4 lg:grid-cols-[2fr,1fr]">
        <div className="space-y-4">
          <Skeleton className="h-40 w-full" />
          <Skeleton className="h-64 w-full" />
        </div>
        <div className="space-y-4">
          <Skeleton className="h-40 w-full" />
          <Skeleton className="h-40 w-full" />
        </div>
      </div>
    </div>
  )
}

const STATUS_HELP = {
  401: 'Not authenticated.',
  403: 'Your role is not authorised for this resource.',
  404: 'Not found.',
  422: 'The request was rejected as invalid.',
  501: 'This endpoint is not implemented on the backend yet.',
  503: 'The service is temporarily unavailable (a model or configuration is not loaded).',
}

export function ErrorState({ error, onRetry }) {
  const status = error?.status
  const help = STATUS_HELP[status]
  return (
    <div className="rounded-2xl border border-red-500/25 bg-red-500/10 p-5 text-sm text-red-200">
      <p className="font-semibold">{status ? `Request failed (${status})` : 'Could not reach the API.'}</p>
      {help && <p className="mt-1">{help}</p>}
      {!status && (
        <p className="mt-1">
          No backend is running. Start FastAPI on <code className="rounded bg-white/10 px-1 font-mono text-xs">:8000</code>,
          or run the dev server normally to preview with sample data.
        </p>
      )}
      <p className="mt-2 font-mono text-xs text-red-300/80">{String(error?.message || error)}</p>
      {onRetry && (
        <button
          onClick={onRetry}
          className="mt-3 rounded-md border border-red-500/30 bg-white/5 px-3 py-1 text-xs font-semibold text-red-200 hover:bg-white/10"
        >
          Retry
        </button>
      )}
    </div>
  )
}

export function MockBanner({ feature = 'This screen' }) {
  return (
    <div className="rounded-xl border border-accent-purple/25 bg-accent-purple/10 px-4 py-2 text-xs font-medium text-slate-300">
      Sample data — the API is not reachable, so {feature.toLowerCase()} is showing fixed example
      values. No real patient, hospital, or model data is displayed.
    </div>
  )
}

// Wraps a useApi() result: loader / error / mock banner, then children.
export function DataState({ query, feature, loader, children }) {
  const { data, error, loading, reload, isMock } = query
  if (loading) return loader || <Loading />
  if (error) return <ErrorState error={error} onRetry={reload} />
  if (!data) return <ErrorState error={{ message: 'No data' }} onRetry={reload} />
  return (
    <div className="space-y-4">
      {isMock && <MockBanner feature={feature} />}
      {children(data)}
    </div>
  )
}
