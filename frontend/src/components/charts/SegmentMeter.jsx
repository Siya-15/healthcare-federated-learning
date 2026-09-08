// Ordinal level meter: LOW / MODERATE / HIGH (or any ordered list). The active
// segment lights up; earlier segments are dimmed-filled to read as a scale.
const DEFAULT_LEVELS = ['LOW', 'MODERATE', 'HIGH']

const TONE = {
  LOW: '#34d399',
  MODERATE: '#eab308',
  MEDIUM: '#eab308',
  HIGH: '#f87171',
  AVAILABLE: '#34d399',
  LIMITED: '#eab308',
  UNAVAILABLE: '#f87171',
}

export default function SegmentMeter({ value, levels = DEFAULT_LEVELS, label, goodIsLow = true }) {
  const idx = levels.findIndex((l) => String(l).toUpperCase() === String(value).toUpperCase())
  const color = TONE[String(value).toUpperCase()] || '#94a3b8'
  return (
    <div>
      {label && <div className="mb-1 text-xs font-medium uppercase tracking-wide text-slate-500">{label}</div>}
      <div className="flex gap-1">
        {levels.map((l, i) => {
          const active = i === idx
          const filled = goodIsLow ? i <= idx : i >= idx
          return (
            <div
              key={l}
              className="h-2 flex-1 rounded-full"
              style={{
                background: active ? color : filled ? `${color}55` : 'rgba(255,255,255,0.08)',
              }}
            />
          )
        })}
      </div>
      <div className="mt-1 flex justify-between text-[10px] uppercase tracking-wide text-slate-600">
        {levels.map((l) => (
          <span key={l} className={String(l).toUpperCase() === String(value).toUpperCase() ? 'font-bold text-slate-300' : ''}>
            {l}
          </span>
        ))}
      </div>
    </div>
  )
}
