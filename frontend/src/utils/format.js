// Presentation-only helpers for the Objective E treatment advisor.
//
// These functions format numbers, dates and labels for display. They do NOT
// compute scores, probabilities, risk levels or rankings - all of that comes
// from the backend E13 contract and is rendered as-is (spec section 13).

export function formatPct(value, digits = 1) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return '—'
  const n = Number(value)
  // Accept either a 0..1 fraction or an already-scaled percentage.
  const pct = n <= 1 ? n * 100 : n
  return `${pct.toFixed(digits)}%`
}

export function formatScore(value, digits = 3) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return '—'
  return Number(value).toFixed(digits)
}

export function formatDays(value) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return '—'
  const n = Number(value)
  const unit = n === 1 ? 'day' : 'days'
  return `${Number.isInteger(n) ? n : n.toFixed(1)} ${unit}`
}

export function formatRange(pair, unit = '') {
  if (!Array.isArray(pair) || pair.length !== 2) return '—'
  const [lo, hi] = pair
  if (lo === null || hi === null || lo === undefined || hi === undefined) return '—'
  const suffix = unit ? ` ${unit}` : ''
  return `${lo}–${hi}${suffix}`
}

export function formatIntervalPct(pair, digits = 0) {
  if (!Array.isArray(pair) || pair.length !== 2) return '—'
  return `${formatPct(pair[0], digits)} – ${formatPct(pair[1], digits)}`
}

export function formatDateTime(iso) {
  if (!iso) return '—'
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return String(iso)
  return d.toLocaleString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

export function formatDate(iso) {
  if (!iso) return '—'
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return String(iso)
  return d.toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric' })
}

// Human label for an ALL_CAPS_ENUM coming from the backend.
export function humanizeEnum(value) {
  if (value === null || value === undefined || value === '') return '—'
  return String(value)
    .toLowerCase()
    .replace(/_/g, ' ')
    .replace(/\b\w/g, (c) => c.toUpperCase())
}

// Tailwind classes for a qualitative level. `kind` flips the colour meaning:
// for "risk" and "uncertainty" LOW is good; for "activity" GREEN is good.
const GOOD = 'bg-emerald-500/15 text-emerald-300 border-emerald-500/25'
const WARN = 'bg-amber-500/15 text-amber-300 border-amber-500/25'
const BAD = 'bg-red-500/15 text-red-300 border-red-500/25'
const NEUTRAL = 'bg-white/5 text-slate-400 border-white/10'
const ORANGE = 'bg-orange-500/15 text-orange-300 border-orange-500/25'

const LEVEL_TONE = {
  LOW: GOOD,
  MODERATE: WARN,
  MEDIUM: WARN,
  HIGH: BAD,
  AVAILABLE: GOOD,
  LIMITED: WARN,
  UNAVAILABLE: BAD,
  PROJECT_SUPPORTED: GOOD,
  PROJECT_SUPPORTED_REVIEW: WARN,
  NOT_SUPPORTED: BAD,
  UNKNOWN: NEUTRAL,
  GREEN: GOOD,
  YELLOW: WARN,
  ORANGE,
  RED: BAD,
  RISING: ORANGE,
  STABLE: NEUTRAL,
  FALLING: GOOD,
}

export function levelToneClass(value) {
  return LEVEL_TONE[String(value || '').toUpperCase()] || NEUTRAL
}

export function trendArrow(trend) {
  const t = String(trend || '').toUpperCase()
  if (t === 'RISING') return '▲'
  if (t === 'FALLING') return '▼'
  if (t === 'STABLE') return '▬'
  return ''
}

export function fmtInt(value) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return '—'
  return Number(value).toLocaleString()
}

export function fmtDelta(value, digits = 1) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return '—'
  const n = Number(value)
  return `${n > 0 ? '+' : ''}${n.toFixed(digits)}`
}

export function pctChange(current, baseline) {
  const c = Number(current)
  const b = Number(baseline)
  if (!b || Number.isNaN(c) || Number.isNaN(b)) return null
  return ((c - b) / b) * 100
}

export function classNames(...xs) {
  return xs.filter(Boolean).join(' ')
}

// Shown wherever the ML prototype genuinely does not produce a value
// (spec section 16: represent unsupported information as UNKNOWN / NOT_IMPLEMENTED).
export const NOT_IMPLEMENTED = 'NOT_IMPLEMENTED'
export const UNKNOWN = 'UNKNOWN'
