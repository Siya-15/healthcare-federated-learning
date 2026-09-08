import { useApi } from '../../hooks/useApi'
import { getNetwork, getModel } from '../../services/federatedApi'
import { PageHeader, DataState, LevelBadge, Field } from '../../components/common/ui'
import { Bento, Tile } from '../../components/common/Bento'
import ProgressRing from '../../components/charts/ProgressRing'
import MiniBars from '../../components/charts/MiniBars'

export default function FederatedOverview() {
  const net = useApi(({ signal }) => getNetwork({ signal }), [])
  const model = useApi(({ signal }) => getModel({ signal }), [])
  const m = model.data

  return (
    <div className="mx-auto max-w-6xl px-6 py-6">
      <PageHeader title="Federated Overview" subtitle="Flower / FedAvg coordination metadata" />
      <DataState query={net} feature="federated status">
        {(d) => (
          <Bento>
            <Tile col={2} title="Rounds complete">
              <div className="flex items-center gap-3">
                <ProgressRing
                  value={d.current_round}
                  max={d.total_rounds}
                  center={`${d.current_round}/${d.total_rounds}`}
                  sub="rounds"
                />
                <div className="text-xs text-slate-400">
                  <div>{d.participating_hospitals}/{d.total_hospitals} hospitals</div>
                  <div className="mt-1"><LevelBadge value={d.aggregation_status} /></div>
                </div>
              </div>
            </Tile>
            <Tile col={4} title="Configuration">
              <dl className="grid grid-cols-2 gap-3 text-sm">
                <Field label="Framework">{d.framework}</Field>
                <Field label="Model">{d.model}</Field>
                <Field label="Global version">{d.global_model_version}</Field>
                <Field label="Last run">{new Date(d.last_run).toLocaleString()}</Field>
              </dl>
            </Tile>

            {m && (
              <>
                <Tile col={3} title="Global model — honest metrics" subtitle={`${m.global_model_version} · round ${m.training_round}`}>
                  <MiniBars
                    max={1}
                    items={Object.entries(m.honest_metrics).map(([k, v]) => ({
                      label: k.replace(/_/g, ' '),
                      value: v,
                      display: typeof v === 'number' ? v.toFixed(4) : v,
                      color: k === 'macro_f1' ? '#f87171' : '#5b8def',
                    }))}
                  />
                </Tile>
                <Tile col={3} title="Caveats" className="border-amber-500/25">
                  <ul className="list-disc space-y-1 pl-4 text-xs text-amber-200">
                    {m.caveats.map((c, i) => (
                      <li key={i}>{c}</li>
                    ))}
                  </ul>
                </Tile>
              </>
            )}
          </Bento>
        )}
      </DataState>
    </div>
  )
}
