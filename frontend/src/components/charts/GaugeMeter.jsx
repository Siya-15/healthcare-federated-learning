// Radial arc gauge (270°) for a single 0..1 or 0..100 value. Pure SVG.
export default function GaugeMeter({
  value,
  max = 1,
  label,
  sublabel,
  color = '#34d399',
  size = 120,
}) {
  const pct = Math.max(0, Math.min(1, (Number(value) || 0) / max))
  const r = size / 2 - 10
  const cx = size / 2
  const cy = size / 2
  const startAngle = 135
  const sweep = 270
  const toXY = (a) => {
    const rad = (a * Math.PI) / 180
    return [cx + r * Math.cos(rad), cy + r * Math.sin(rad)]
  }
  const arc = (frac) => {
    const end = startAngle + sweep * frac
    const [x1, y1] = toXY(startAngle)
    const [x2, y2] = toXY(end)
    const large = sweep * frac > 180 ? 1 : 0
    return `M ${x1} ${y1} A ${r} ${r} 0 ${large} 1 ${x2} ${y2}`
  }
  const display =
    max === 1 ? `${Math.round(pct * 100)}%` : `${Number(value).toLocaleString()}`

  return (
    <div className="flex flex-col items-center">
      <svg width={size} height={size * 0.82} viewBox={`0 0 ${size} ${size * 0.82}`}>
        <path d={arc(1)} fill="none" stroke="rgba(255,255,255,0.08)" strokeWidth="9" strokeLinecap="round" />
        {pct > 0 && (
          <path d={arc(pct)} fill="none" stroke={color} strokeWidth="9" strokeLinecap="round" />
        )}
        <text x={cx} y={cy + 2} textAnchor="middle" className="fill-slate-50" style={{ fontSize: 20, fontWeight: 700 }}>
          {display}
        </text>
        {sublabel && (
          <text x={cx} y={cy + 20} textAnchor="middle" className="fill-slate-500" style={{ fontSize: 10 }}>
            {sublabel}
          </text>
        )}
      </svg>
      {label && <div className="-mt-1 text-xs text-slate-400">{label}</div>}
    </div>
  )
}
