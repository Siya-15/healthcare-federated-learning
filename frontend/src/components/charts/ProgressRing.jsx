// Simple circular progress ring with a centered label.
export default function ProgressRing({ value, max = 1, size = 96, color = '#34d399', center, sub }) {
  const frac = Math.max(0, Math.min(1, (Number(value) || 0) / max))
  const stroke = 8
  const r = (size - stroke) / 2
  const c = 2 * Math.PI * r
  return (
    <div className="relative inline-flex" style={{ width: size, height: size }}>
      <svg width={size} height={size} className="-rotate-90">
        <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="rgba(255,255,255,0.08)" strokeWidth={stroke} />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={r}
          fill="none"
          stroke={color}
          strokeWidth={stroke}
          strokeLinecap="round"
          strokeDasharray={c}
          strokeDashoffset={c * (1 - frac)}
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className="text-sm font-bold text-slate-100">{center ?? `${Math.round(frac * 100)}%`}</span>
        {sub && <span className="text-[10px] text-slate-500">{sub}</span>}
      </div>
    </div>
  )
}
