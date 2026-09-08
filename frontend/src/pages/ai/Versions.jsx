import { useApi } from '../../hooks/useApi'
import { getModelVersions } from '../../services/modelApi'
import { PageHeader, DataState, Tag } from '../../components/common/ui'
import { Bento, Tile } from '../../components/common/Bento'

export default function Versions() {
  const query = useApi(({ signal }) => getModelVersions({ signal }), [])
  return (
    <div className="mx-auto max-w-6xl px-6 py-6">
      <PageHeader title="Model Versions" subtitle="Component versions, training date and status" />
      <DataState query={query} feature="version metadata">
        {(d) => {
          const active = d.items.filter((x) => x.status === 'ACTIVE').length
          return (
            <Bento>
              <Tile col={2} title="Artifacts">
                <div className="text-3xl font-bold text-slate-50">{active}</div>
                <div className="text-xs text-slate-500">active · {d.items.length - active} superseded</div>
              </Tile>
              <Tile col={4} title="Timeline">
                <ol className="relative space-y-3 border-l border-line pl-4">
                  {d.items.map((r, i) => (
                    <li key={i}>
                      <span className="absolute -left-[5px] mt-1.5 h-2 w-2 rounded-full bg-brand" />
                      <div className="flex items-center justify-between gap-2 text-sm">
                        <span className="text-slate-200">{r.component}</span>
                        <Tag tone={r.status === 'ACTIVE' ? 'green' : 'slate'}>{r.status}</Tag>
                      </div>
                      <div className="text-xs text-slate-500">
                        <span className="font-mono">{r.version}</span> · trained {r.trained}
                      </div>
                    </li>
                  ))}
                </ol>
              </Tile>
            </Bento>
          )
        }}
      </DataState>
    </div>
  )
}
