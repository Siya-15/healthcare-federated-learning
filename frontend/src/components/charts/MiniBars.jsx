// Compact labelled horizontal bars. `items` = [{ label, value, display?, color? }].
// `max` defaults to the largest value. Good for weights, scores, small metrics.
export default function MiniBars({ items = [], max, unit = '', height = 'sm' }) {
  const hi = max ?? Math.max(...items.map((i) => Number(i.value) || 0), 0.0001)
  const barH = height === 'xs' ? 'h-1.5' : 'h-2'
  return (
    <ul className="space-y-2">
      {items.map((it, i) => {
        const v = Number(it.value) || 0
        const w = `${Math.max(2, (v / hi) * 100).toFixed(1)}%`
        return (
          <li key={it.label ?? i}>
            <div className="flex items-baseline justify-between text-xs">
              <span className="truncate text-slate-400">{it.label}</span>
              <span className="ml-2 shrink-0 font-medium text-slate-200">
                {it.display ?? v}
                {unit}
              </span>
            </div>
            <div className={`mt-1 ${barH} w-full overflow-hidden rounded-full bg-white/8`}>
              <div className={`${barH} rounded-full`} style={{ width: w, background: it.color || '#5b8def' }} />
            </div>
          </li>
        )
      })}
    </ul>
  )
}
