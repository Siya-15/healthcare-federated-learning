import { useApi } from '../../hooks/useApi'
import { getDataFlow } from '../../services/privacyApi'
import { PageHeader, DataState, InfoNote } from '../../components/common/ui'
import { Bento, Tile } from '../../components/common/Bento'
import DataFlowDiagram from '../../components/federated/DataFlowDiagram'

export default function DataFlow() {
  const query = useApi(({ signal }) => getDataFlow({ signal }), [])
  return (
    <div className="mx-auto max-w-6xl px-6 py-6">
      <PageHeader title="Data Flow" subtitle="Local clinical data → local processing → model update → aggregation → global model" />
      <DataState query={query} feature="the data-flow description">
        {(d) => (
          <>
            <Bento>
              <Tile col={4} title="Where data lives and what moves">
                <DataFlowDiagram steps={d.steps} />
              </Tile>
              <Tile col={2} title="Boundary">
                <ul className="space-y-2 text-xs">
                  <li className="rounded-lg bg-emerald-500/10 px-2.5 py-2 text-emerald-200">
                    <span className="font-semibold">Stays local:</span> encounters, symptoms, vitals,
                    treatments, labs, imaging, identifiers.
                  </li>
                  <li className="rounded-lg bg-orange-500/10 px-2.5 py-2 text-orange-200">
                    <span className="font-semibold">Leaves the hospital:</span> TabNet parameter
                    tensors only — no rows, no identifiers.
                  </li>
                </ul>
              </Tile>
            </Bento>
            <InfoNote tone="amber">{d.guarantee_note}</InfoNote>
          </>
        )}
      </DataState>
    </div>
  )
}
