import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
  CartesianGrid,
} from 'recharts'

const PALETTE = ['#5b8def', '#34d399', '#fb923c', '#a78bfa', '#38bdf8', '#eab308']

const AXIS = { fontSize: 12, fill: '#8b8b93' }
const TOOLTIP_STYLE = {
  background: '#16171a',
  border: '1px solid rgba(255,255,255,0.1)',
  borderRadius: 10,
  color: '#e2e8f0',
  fontSize: 12,
}

// `data` = [{ x, [seriesKey]: number, ... }]. `series` = [{ key, name?, dashed? }].
export default function TrendChart({ data, series, height = 260, yLabel }) {
  return (
    <div style={{ height }}>
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data} margin={{ top: 8, right: 16, bottom: 4, left: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" vertical={false} />
          <XAxis dataKey="x" tick={AXIS} axisLine={{ stroke: 'rgba(255,255,255,0.08)' }} tickLine={false} />
          <YAxis
            tick={AXIS}
            axisLine={false}
            tickLine={false}
            label={yLabel ? { value: yLabel, angle: -90, position: 'insideLeft', fontSize: 11, fill: '#8b8b93' } : undefined}
          />
          <Tooltip contentStyle={TOOLTIP_STYLE} cursor={{ stroke: 'rgba(255,255,255,0.12)' }} />
          <Legend wrapperStyle={{ fontSize: 12, color: '#8b8b93' }} />
          {series.map((s, i) => (
            <Line
              key={s.key}
              type="monotone"
              dataKey={s.key}
              name={s.name || s.key}
              stroke={PALETTE[i % PALETTE.length]}
              strokeDasharray={s.dashed ? '5 4' : undefined}
              dot={false}
              strokeWidth={2}
            />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}

export { PALETTE as TREND_PALETTE, AXIS, TOOLTIP_STYLE }
