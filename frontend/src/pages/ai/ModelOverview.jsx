import { useApi } from '../../hooks/useApi'
import { getModelOverview } from '../../services/modelApi'
import { PageHeader, DataState, InfoNote } from '../../components/common/ui'
import { Bento, Tile } from '../../components/common/Bento'
import PipelineStrip from '../../components/clinical/PipelineStrip'
import MiniBars from '../../components/charts/MiniBars'

const KIND_COLOR = { data: '#5b8def', rules: '#94a3b8', config: '#a78bfa', context: '#38bdf8', model: '#34d399', explain: '#eab308', rank: '#fb923c' }

export default function ModelOverview() {
  const query = useApi(({ signal }) => getModelOverview({ signal }), [])
  return (
    <div className="mx-auto max-w-6xl px-6 py-6">
      <PageHeader title="Model Overview" subtitle="Treatment-advisor pipeline E1 → E12" />
      <DataState query={query} feature="the model overview">
        {(d) => (
          <>
            <Bento>
              <Tile col={6} title="Pipeline">
                <PipelineStrip />
                <div className="mt-3 grid gap-1.5 sm:grid-cols-3 lg:grid-cols-4">
                  {d.pipeline.map((s) => (
                    <div key={s.stage} className="flex items-center gap-2 rounded-lg bg-white/5 px-2.5 py-1.5 text-xs">
                      <span className="h-2 w-2 rounded-full" style={{ background: KIND_COLOR[s.kind] || '#94a3b8' }} />
                      <span className="font-mono font-semibold text-slate-300">{s.stage}</span>
                      <span className="text-slate-400">{s.name}</span>
                    </div>
                  ))}
                </div>
              </Tile>
              <Tile col={3} title="E12 ranking weights">
                <MiniBars
                  max={0.4}
                  items={Object.entries(d.ranking_weights).map(([k, v]) => ({
                    label: k,
                    value: v,
                    display: `${(v * 100).toFixed(0)}%`,
                    color: k === 'success' ? '#34d399' : '#5b8def',
                  }))}
                />
              </Tile>
              <Tile col={3} title="Note" plain>
                <InfoNote>{d.note}</InfoNote>
              </Tile>
            </Bento>
          </>
        )}
      </DataState>
    </div>
  )
}
