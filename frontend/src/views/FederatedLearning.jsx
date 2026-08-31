import { api } from '../api/client'
import { useApi } from '../components/useApi'
import { Card, ErrorBox, Loading, Stat } from '../components/ui'

const FLOW = ['Local Data', 'Local Training', 'Model Update', 'FedAvg', 'Global Model']

export default function FederatedLearning() {
  const { data, error, loading } = useApi(api.flStatus)

  if (loading) return <Loading what="federated learning status" />
  if (error) return <ErrorBox error={error} />

  const m = data.global_metrics

  return (
    <div className="space-y-5">
      <div className="rounded-xl border border-slate-800 bg-slate-900 p-5 text-white">
        <div className="text-sm font-semibold uppercase tracking-wide text-slate-400">
          Privacy guarantee
        </div>
        <p className="mt-1 text-lg font-bold">Raw patient data remains at hospital level.</p>
        <p className="mt-1 text-sm text-slate-300">
          Each hospital trains locally on its own encounters. Only model parameters are sent to the
          server for aggregation — no patient rows leave the site.
        </p>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Card>
          <Stat label="Status" value={data.status} tone="good" />
        </Card>
        <Card>
          <Stat
            label="Rounds"
            value={`${data.rounds_completed} / ${data.rounds_configured}`}
            hint={data.strategy}
          />
        </Card>
        <Card>
          <Stat label="Hospitals" value={data.hospitals_participating} hint="H001 – H010" />
        </Card>
        <Card>
          <Stat label="Labels" value={data.label_count} hint={`${data.feature_count} input features`} />
        </Card>
      </div>

      <Card title="Aggregation flow" subtitle={data.model}>
        <div className="flex flex-wrap items-center gap-2">
          {FLOW.map((step, i) => (
            <div key={step} className="flex items-center gap-2">
              <div className="rounded-lg border border-slate-300 bg-slate-50 px-4 py-2 text-sm font-medium">
                {step}
              </div>
              {i < FLOW.length - 1 && <span className="text-slate-400">→</span>}
            </div>
          ))}
        </div>
        <div className="mt-4 flex flex-wrap gap-1.5">
          {data.hospital_ids.map((h) => (
            <span
              key={h}
              className="rounded bg-blue-50 px-2 py-1 font-mono text-xs text-blue-800"
            >
              {h}
            </span>
          ))}
        </div>
      </Card>

      <Card title="Global metrics" subtitle="Final values from the last validated run">
        <div className="grid grid-cols-2 gap-5 lg:grid-cols-4">
          <Stat label="Accuracy" value={`${m.accuracy}%`} tone="good" />
          <Stat label="Micro-F1" value={`${m.micro_f1}%`} tone="warn" />
          <Stat label="Macro-F1" value={`${m.macro_f1}%`} tone="bad" />
          <Stat label="Hamming loss" value={`${m.hamming_loss}%`} />
        </div>
      </Card>

      <Card title="Stated limitations">
        <ul className="space-y-2">
          {data.limitations.map((l) => (
            <li key={l} className="flex gap-2 text-sm text-slate-700">
              <span className="text-amber-600">•</span>
              <span>{l}</span>
            </li>
          ))}
        </ul>
        <p className="mt-4 rounded bg-slate-50 p-2 text-xs text-slate-500">{data.note}</p>
      </Card>
    </div>
  )
}
