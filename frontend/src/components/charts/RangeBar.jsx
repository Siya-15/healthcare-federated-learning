// A track showing a [lo, hi] band and an optional point marker, scaled to
// [domainMin, domainMax]. Used for recovery-day ranges and predictive intervals.
export default function RangeBar({
  lo,
  hi,
  point,
  domainMin,
  domainMax,
  unit = '',
  color = '#5b8def',
  formatValue = (v) => v,
}) {
  const dMin = domainMin ?? Math.min(lo, hi, point ?? lo)
  const dMax = domainMax ?? Math.max(lo, hi, point ?? hi)
  const span = dMax - dMin || 1
  const pos = (v) => `${(((v - dMin) / span) * 100).toFixed(1)}%`

  return (
    <div>
      <div className="relative h-2 rounded-full bg-white/8">
        <div
          className="absolute inset-y-0 rounded-full"
          style={{ left: pos(lo), width: `calc(${pos(hi)} - ${pos(lo)})`, background: `${color}66` }}
        />
        {point != null && (
          <div
            className="absolute top-1/2 h-3 w-3 -translate-x-1/2 -translate-y-1/2 rounded-full border-2 border-ink-850"
            style={{ left: pos(point), background: color }}
          />
        )}
      </div>
      <div className="mt-1 flex justify-between text-[11px] text-slate-500">
        <span>{formatValue(lo)}{unit && ` ${unit}`}</span>
        {point != null && <span className="font-semibold text-slate-300">{formatValue(point)}{unit && ` ${unit}`}</span>}
        <span>{formatValue(hi)}{unit && ` ${unit}`}</span>
      </div>
    </div>
  )
}
