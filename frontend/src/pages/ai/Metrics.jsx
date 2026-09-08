import { useApi } from '../../hooks/useApi'
import { getModelMetrics } from '../../services/modelApi'
import { PageHeader, DataState, NotImplemented } from '../../components/common/ui'
import { Bento, Tile } from '../../components/common/Bento'
import MiniBars from '../../components/charts/MiniBars'

// Parse a metric string like "0.8782" or "1.9" into a number when possible.
const num = (v) => {
  const n = parseFloat(String(v))
  return Number.isNaN(n) ? null : n
}

export default function Metrics() {
  const query = useApi(({ signal }) => getModelMetrics({ signal }), [])
  return (
    <div className="mx-auto max-w-6xl px-6 py-6">
      <PageHeader title="Model Metrics" subtitle="Stored evaluation results — reported honestly" />
      <DataState query={query} feature="model metrics">
        {(d) => {
          const fl = d.federated.filter((m) => num(m.value) != null && num(m.value) <= 1)
          return (
            <Bento>
              <Tile col={3} title="Federated global model" subtitle="round 3">
                <MiniBars
                  max={1}
                  items={fl.map((m) => ({
                    label: m.metric,
                    value: num(m.value),
                    display: m.value,
                    color: /macro/i.test(m.metric) ? '#f87171' : '#5b8def',
                  }))}
                />
                <p className="mt-2 text-[11px] text-slate-500">
                  Macro-F1 is very low; Micro-F1 not monotonic across rounds.
                </p>
              </Tile>

              <Tile col={3} title="Treatment advisor (E6–E9)" scroll>
                <ul className="space-y-1.5 text-xs">
                  {d.treatment_advisor.map((m, i) => (
                    <li key={i} className="flex items-center justify-between gap-3 rounded-lg bg-white/5 px-2.5 py-1.5">
                      <span className="text-slate-400">
                        <span className="text-slate-300">{m.metric}</span> · {m.model}
                      </span>
                      <span className="shrink-0 font-mono font-semibold text-slate-200">{m.value}</span>
                    </li>
                  ))}
                </ul>
              </Tile>

              <Tile col={6} title="Not measured in the prototype">
                <div className="flex flex-wrap gap-2">
                  {d.not_implemented.map((x) => (
                    <NotImplemented key={x} detail={x} />
                  ))}
                </div>
              </Tile>
            </Bento>
          )
        }}
      </DataState>
    </div>
  )
}
