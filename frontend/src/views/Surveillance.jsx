import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'

import { api } from '../api/client'
import { useApi } from '../components/useApi'
import { AlertBadge, Card, ErrorBox, Loading, Stat } from '../components/ui'

const ALERT_FILL = {
  GREEN: '#16a34a',
  YELLOW: '#ca8a04',
  ORANGE: '#ea580c',
  RED: '#dc2626',
}

export default function Surveillance() {
  const { data, error, loading } = useApi(api.surveillance)

  if (loading) return <Loading what="surveillance" />
  if (error) return <ErrorBox error={error} />

  const { assessment: a, hospitals, weekly_series: weekly, cross_hospital_patterns: patterns } = data

  // Pivot the long weekly series into one row per week, one column per hospital.
  const weeks = [...new Set(weekly.map((w) => w.week))].sort()
  const hospitalIds = [...new Set(weekly.map((w) => w.hospital_id))].sort()
  const series = weeks.map((week) => {
    const row = { week }
    weekly.filter((w) => w.week === week).forEach((w) => {
      row[w.hospital_id] = w.case_count
    })
    return row
  })

  const distribution = Object.entries(
    hospitals.reduce((acc, h) => {
      acc[h.alert_level] = (acc[h.alert_level] || 0) + 1
      return acc
    }, {})
  ).map(([level, count]) => ({ level, count }))

  return (
    <div className="space-y-5">
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Card>
          <Stat
            label="Overall alert"
            value={a.overall_alert}
            tone={a.overall_alert === 'GREEN' ? 'good' : 'bad'}
          />
        </Card>
        <Card>
          <Stat label="Affected hospitals" value={`${a.affected_percentage}%`} hint="ORANGE or above" />
        </Card>
        <Card>
          <Stat label="RED alerts" value={`${a.red_hospitals} / ${a.total_hospitals}`} tone="bad" />
        </Card>
        <Card>
          <Stat
            label="Potential outbreak"
            value={a.potential_outbreak ? 'YES' : 'NO'}
            tone={a.potential_outbreak ? 'bad' : 'good'}
            hint="triggered at ≥50% affected"
          />
        </Card>
      </div>

      <div className="grid gap-5 lg:grid-cols-[2fr_1fr]">
        <Card title="Weekly cases by hospital">
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={series}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
              <XAxis dataKey="week" tick={{ fontSize: 11 }} />
              <YAxis tick={{ fontSize: 11 }} />
              <Tooltip />
              <Legend wrapperStyle={{ fontSize: 11 }} />
              {hospitalIds.map((h, i) => (
                <Line
                  key={h}
                  type="monotone"
                  dataKey={h}
                  stroke={`hsl(${(i * 36) % 360} 65% 45%)`}
                  strokeWidth={1.5}
                  dot={false}
                />
              ))}
            </LineChart>
          </ResponsiveContainer>
        </Card>

        <Card title="Alert distribution">
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={distribution}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
              <XAxis dataKey="level" tick={{ fontSize: 11 }} />
              <YAxis allowDecimals={false} tick={{ fontSize: 11 }} />
              <Tooltip />
              <Bar dataKey="count">
                {distribution.map((d) => (
                  <Cell key={d.level} fill={ALERT_FILL[d.level] || '#64748b'} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </Card>
      </div>

      <Card title="Per-hospital status" subtitle="Latest reporting week">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-200 text-left text-xs uppercase tracking-wide text-slate-500">
                <th className="py-2 pr-4">Hospital</th>
                <th className="py-2 pr-4">Week</th>
                <th className="py-2 pr-4 text-right">Current</th>
                <th className="py-2 pr-4 text-right">Previous</th>
                <th className="py-2 pr-4 text-right">Growth</th>
                <th className="py-2">Alert</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {hospitals.map((h) => (
                <tr key={h.hospital_id}>
                  <td className="py-2 pr-4 font-medium">{h.hospital_id}</td>
                  <td className="py-2 pr-4 text-slate-500">{h.week}</td>
                  <td className="py-2 pr-4 text-right">{h.current_cases}</td>
                  <td className="py-2 pr-4 text-right text-slate-500">
                    {h.previous_cases ?? '—'}
                  </td>
                  <td className="py-2 pr-4 text-right">
                    {h.growth_rate == null ? '—' : `${(h.growth_rate * 100).toFixed(1)}%`}
                  </td>
                  <td className="py-2">
                    <AlertBadge level={h.alert_level} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>

      <Card
        title="Cross-hospital symptom patterns"
        subtitle="Recurring anomalous patterns seen at more than one hospital"
      >
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-200 text-left text-xs uppercase tracking-wide text-slate-500">
                <th className="py-2 pr-4">Pattern</th>
                <th className="py-2 pr-4 text-right">Hospitals</th>
                <th className="py-2 text-right">Occurrences</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {patterns.map((p) => (
                <tr key={p.symptom_pattern}>
                  <td className="py-2 pr-4">{p.symptom_pattern}</td>
                  <td className="py-2 pr-4 text-right font-medium">{p.hospitals_affected}</td>
                  <td className="py-2 text-right text-slate-600">{p.total_occurrences}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="mt-4 text-xs text-slate-400">{data.note}</p>
      </Card>
    </div>
  )
}
