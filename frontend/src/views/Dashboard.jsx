import { api } from '../api/client'
import { useApi } from '../components/useApi'
import { AlertBadge, Card, ErrorBox, Loading, PassFail, Stat } from '../components/ui'

export default function Dashboard() {
  const { data, error, loading } = useApi(api.dashboard)

  if (loading) return <Loading what="dashboard" />
  if (error) return <ErrorBox error={error} />

  const { outbreak, federated_learning: fl, privacy, symptom_patterns: sp } = data
  const tone = { GREEN: 'good', YELLOW: 'warn', ORANGE: 'warn', RED: 'bad' }[
    outbreak.overall_alert
  ]

  return (
    <div className="space-y-5">
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Card>
          <Stat label="Hospitals monitored" value={data.hospitals_monitored} />
        </Card>
        <Card>
          <Stat
            label="Encounters"
            value={data.total_encounters.toLocaleString()}
            hint="across all hospitals"
          />
        </Card>
        <Card>
          <Stat
            label="Outbreak status"
            value={outbreak.overall_alert}
            tone={tone}
            hint={`${outbreak.affected_percentage}% of hospitals at ORANGE or above`}
          />
        </Card>
        <Card>
          <Stat
            label="Hospitals at RED"
            value={`${outbreak.red_hospitals} / ${outbreak.total_hospitals}`}
            tone={outbreak.red_hospitals > 0 ? 'bad' : 'good'}
          />
        </Card>
      </div>

      <div className="grid gap-5 lg:grid-cols-2">
        <Card
          title="Federated learning"
          subtitle="Latest completed run — opening this page does not start a simulation"
        >
          <div className="mb-4 flex items-center gap-3 text-sm">
            <span className="rounded bg-green-100 px-2 py-0.5 text-xs font-bold text-green-800">
              {fl.status}
            </span>
            <span className="text-slate-600">
              {fl.rounds_completed} rounds · {fl.strategy} · {fl.hospitals_participating} hospitals
            </span>
          </div>
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
            <Stat label="Accuracy" value={`${fl.global_metrics.accuracy}%`} />
            <Stat label="Micro-F1" value={`${fl.global_metrics.micro_f1}%`} />
            <Stat label="Macro-F1" value={`${fl.global_metrics.macro_f1}%`} tone="warn" />
            <Stat label="Hamming loss" value={`${fl.global_metrics.hamming_loss}%`} />
          </div>
          <p className="mt-4 rounded bg-slate-50 p-2 text-xs text-slate-600">
            Raw patient data remains at hospital level. Only model parameters are exchanged.
          </p>
        </Card>

        <Card title="Privacy" subtitle={`${privacy.audited_columns} audited columns`}>
          <div className="mb-3 flex items-center gap-2">
            <span className="text-sm text-slate-600">Overall</span>
            <PassFail status={privacy.overall} />
          </div>
          <ul className="space-y-2">
            {privacy.checks.map((c) => (
              <li key={c.check} className="flex items-center justify-between gap-3 text-sm">
                <span className="text-slate-700">{c.check}</span>
                <PassFail status={c.status} />
              </li>
            ))}
          </ul>
        </Card>
      </div>

      <Card
        title="Top cross-hospital symptom patterns"
        subtitle={`${sp.total_anomalies_flagged} anomalous encounters flagged in total`}
      >
        <ul className="divide-y divide-slate-100">
          {sp.top_cross_hospital.map((p) => (
            <li key={p.symptom_pattern} className="flex items-center justify-between gap-4 py-2">
              <span className="text-sm text-slate-700">{p.symptom_pattern}</span>
              <span className="whitespace-nowrap text-xs text-slate-500">
                {p.hospitals_affected} hospitals · {p.total_occurrences} cases
              </span>
            </li>
          ))}
        </ul>
      </Card>
    </div>
  )
}
