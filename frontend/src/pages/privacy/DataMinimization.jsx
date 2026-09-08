import { useApi } from '../../hooks/useApi'
import { getAudit } from '../../services/privacyApi'
import { PageHeader, DataState, InfoNote } from '../../components/common/ui'
import { Bento, Tile } from '../../components/common/Bento'

const STAGES = [
  ['local_db', 'Local DB'],
  ['local_processing', 'Local proc.'],
  ['transmitted', 'Transmitted'],
  ['aggregate_view', 'Aggregate'],
]

export default function DataMinimization() {
  const query = useApi(({ signal }) => getAudit({ signal }), [])
  return (
    <div className="mx-auto max-w-6xl px-6 py-6">
      <PageHeader title="Data Minimization" subtitle="Field-level policy: where each field is allowed to exist" />
      <DataState query={query} feature="the minimization matrix">
        {(d) => (
          <>
            <Bento>
              <Tile col={6} title="Minimization matrix" subtitle="filled = field present at that stage">
                <div className="overflow-x-auto">
                  <div className="min-w-[520px]">
                    <div className="grid grid-cols-[1.4fr_repeat(4,1fr)] gap-1 text-[11px] uppercase tracking-wide text-slate-500">
                      <div />
                      {STAGES.map(([, label]) => (
                        <div key={label} className="px-1 text-center">{label}</div>
                      ))}
                    </div>
                    {d.minimization_matrix.map((row) => (
                      <div key={row.field} className="mt-1 grid grid-cols-[1.4fr_repeat(4,1fr)] items-center gap-1">
                        <div className="truncate text-xs text-slate-300">{row.field}</div>
                        {STAGES.map(([key]) => {
                          const on = row[key]
                          const leak = key === 'transmitted' && on
                          return (
                            <div
                              key={key}
                              className={`h-7 rounded ${
                                on
                                  ? leak
                                    ? 'bg-orange-500/40'
                                    : 'bg-emerald-500/30'
                                  : 'bg-white/5'
                              }`}
                            />
                          )
                        })}
                      </div>
                    ))}
                  </div>
                </div>
              </Tile>
            </Bento>
            <InfoNote>
              Only <strong>model parameters</strong> are ever transmitted (orange). Identifiers and
              vitals stay in the hospital; aggregate views expose only pseudonymised / coarsened
              fields.
            </InfoNote>
          </>
        )}
      </DataState>
    </div>
  )
}
