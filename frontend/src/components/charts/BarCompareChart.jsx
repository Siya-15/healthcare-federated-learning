import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
} from 'recharts'
import { AXIS, TOOLTIP_STYLE } from './TrendChart'

// Grouped bars. `series` = [{ key, name, color, hatch? }].
// Matches the mockup's "Weekly Admissions" (hatched dark + solid blue).
export default function BarCompareChart({ data, series, height = 300 }) {
  return (
    <div style={{ height }}>
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} margin={{ top: 8, right: 8, bottom: 4, left: -8 }} barGap={4} barCategoryGap="28%">
          <defs>
            <pattern id="bc-hatch" width="6" height="6" patternTransform="rotate(45)" patternUnits="userSpaceOnUse">
              <rect width="6" height="6" fill="#2a2b30" />
              <line x1="0" y1="0" x2="0" y2="6" stroke="#3a3b42" strokeWidth="3" />
            </pattern>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" vertical={false} />
          <XAxis dataKey="x" tick={AXIS} axisLine={{ stroke: 'rgba(255,255,255,0.08)' }} tickLine={false} />
          <YAxis tick={AXIS} axisLine={false} tickLine={false} width={40} />
          <Tooltip contentStyle={TOOLTIP_STYLE} cursor={{ fill: 'rgba(255,255,255,0.04)' }} />
          {series.map((s) => (
            <Bar
              key={s.key}
              dataKey={s.key}
              name={s.name}
              fill={s.hatch ? 'url(#bc-hatch)' : s.color}
              radius={[5, 5, 0, 0]}
              maxBarSize={26}
            />
          ))}
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}
