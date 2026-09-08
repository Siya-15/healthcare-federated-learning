import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip } from 'recharts'

const PALETTE = ['#5b8def', '#34d399', '#fb923c', '#a78bfa', '#eab308', '#f0a4c8', '#38bdf8', '#94a3b8']

// `data` = [{ name, value }]. Center shows `centerValue` / `centerLabel`.
export default function DonutChart({ data = [], centerValue, centerLabel, height = 220 }) {
  const total = data.reduce((s, d) => s + (Number(d.value) || 0), 0)
  return (
    <div className="relative" style={{ height }}>
      <ResponsiveContainer width="100%" height="100%">
        <PieChart>
          <Pie
            data={data}
            dataKey="value"
            nameKey="name"
            innerRadius="66%"
            outerRadius="92%"
            paddingAngle={2}
            stroke="none"
          >
            {data.map((_, i) => (
              <Cell key={i} fill={PALETTE[i % PALETTE.length]} />
            ))}
          </Pie>
          <Tooltip
            contentStyle={{
              background: '#16171a',
              border: '1px solid rgba(255,255,255,0.1)',
              borderRadius: 10,
              color: '#e2e8f0',
              fontSize: 12,
            }}
          />
        </PieChart>
      </ResponsiveContainer>
      <div className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center">
        <div className="text-2xl font-bold text-slate-100">
          {centerValue ?? total.toLocaleString()}
        </div>
        {centerLabel && <div className="text-xs text-slate-500">{centerLabel}</div>}
      </div>
    </div>
  )
}

export { PALETTE as DONUT_PALETTE }
