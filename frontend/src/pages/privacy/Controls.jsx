import { useApi } from '../../hooks/useApi'
import { getPolicy } from '../../services/privacyApi'
import { PageHeader, DataState, InfoNote, NotImplemented } from '../../components/common/ui'
import { Bento, Tile } from '../../components/common/Bento'
import ProgressRing from '../../components/charts/ProgressRing'

export default function PrivacyControls() {
  const query = useApi(({ signal }) => getPolicy({ signal }), [])
  return (
    <div className="mx-auto max-w-6xl px-6 py-6">
      <PageHeader title="Privacy Controls" subtitle="What the audited prototype actually enforces (Objective C)" />
      <DataState query={query} feature="privacy controls">
        {(d) => {
          const impl = d.controls.filter((c) => c.status === 'IMPLEMENTED').length
          return (
            <>
              <Bento>
                <Tile col={2} title="Coverage">
                  <div className="flex items-center gap-3">
                    <ProgressRing value={impl} max={d.controls.length} center={`${impl}/${d.controls.length}`} sub="active" />
                    <p className="text-xs text-slate-400">
                      {d.controls.length - impl} control(s) are conceptual only and render as NOT_IMPLEMENTED.
                    </p>
                  </div>
                </Tile>
                <Tile col={4} title="Controls" subtitle={`Updated ${d.updated_at}`} scroll>
                  <ul className="space-y-1.5">
                    {d.controls.map((c) => (
                      <li key={c.control} className="flex items-start justify-between gap-3 rounded-lg bg-white/5 px-2.5 py-1.5 text-xs">
                        <div>
                          <div className="font-medium text-slate-200">{c.control}</div>
                          <div className="text-slate-500">{c.detail}</div>
                        </div>
                        {c.status === 'IMPLEMENTED' ? (
                          <span className="shrink-0 rounded bg-emerald-500/15 px-1.5 py-0.5 font-semibold text-emerald-300">ACTIVE</span>
                        ) : (
                          <span className="shrink-0"><NotImplemented /></span>
                        )}
                      </li>
                    ))}
                  </ul>
                </Tile>
              </Bento>
              <InfoNote tone="amber">
                Differential privacy and secure aggregation are conceptual architecture only and must
                not be presented as active.
              </InfoNote>
            </>
          )
        }}
      </DataState>
    </div>
  )
}
