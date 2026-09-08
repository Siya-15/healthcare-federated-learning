// Tiny inline sparkline (bars or line) for KPI cards. Pure SVG - no recharts,
// so it stays crisp at small sizes.
export default function Sparkline({ data = [], variant = 'bars', color = '#34d399', width = 96, height = 34 }) {
  const nums = data.map(Number).filter((n) => !Number.isNaN(n))
  if (nums.length < 2) return <svg width={width} height={height} aria-hidden="true" />

  const min = Math.min(...nums)
  const max = Math.max(...nums)
  const span = max - min || 1
  const y = (v) => height - 3 - ((v - min) / span) * (height - 6)

  if (variant === 'line') {
    const step = width / (nums.length - 1)
    const d = nums.map((v, i) => `${i ? 'L' : 'M'}${(i * step).toFixed(1)} ${y(v).toFixed(1)}`).join(' ')
    return (
      <svg width={width} height={height} aria-hidden="true">
        <path d={d} fill="none" stroke={color} strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
    )
  }

  const gap = 2
  const bw = (width - gap * (nums.length - 1)) / nums.length
  return (
    <svg width={width} height={height} aria-hidden="true">
      {nums.map((v, i) => {
        const h = Math.max(2, height - 3 - y(v) + 3)
        return (
          <rect
            key={i}
            x={(i * (bw + gap)).toFixed(1)}
            y={(height - h - 1).toFixed(1)}
            width={Math.max(1.5, bw).toFixed(1)}
            height={h.toFixed(1)}
            rx="1"
            fill={color}
            opacity={i === nums.length - 1 ? 1 : 0.55}
          />
        )
      })}
    </svg>
  )
}
