import { useApi } from '../../hooks/useApi'
import { getAudit } from '../../services/privacyApi'
import { PageHeader, DataState, NotImplemented } from '../../components/common/ui'
import { Bento, Tile } from '../../components/common/Bento'
import ProgressRing from '../../components/charts/ProgressRing'

function ResultChip({ value }) {
  if (value === 'PASS') return <span className="rounded bg-emerald-500/15 px-1.5 py-0.5 text-xs font-bold text-emerald-300">PASS</span>
  if (value === 'FAIL') return <span className="rounded bg-red-500/15 px-1.5 py-0.5 text-xs font-bold text-red-300">FAIL</span>
  return <NotImplemented label={value} />
}

export default function PrivacyAudit() {
  const query = useApi(({ signal }) => getAudit({ signal }), [])
  return (
    <div className="mx-auto max-w-6xl px-6 py-6">
      <PageHeader title="Privacy Audit" subtitle="Verification evidence (Objective C)" />
      <DataState query={query} feature="the privacy audit">
        {(d) => {
          const pass = d.checks.filter((c) => c.result === 'PASS').length
          const total = d.checks.filter((c) => c.result === 'PASS' || c.result === 'FAIL').length
          return (
            <Bento>
              <Tile col={2} title="Result">
                <div className="flex items-center gap-3">
                  <ProgressRing value={pass} max={total || 1} center={`${pass}/${total}`} sub="checks pass" />
                  <p className="text-xs text-slate-400">Ran {new Date(d.ran_at).toLocaleString()}</p>
                </div>
              </Tile>
              <Tile col={4} title="Checks">
                <ul className="space-y-1.5">
                  {d.checks.map((c) => (
                    <li key={c.check} className="flex items-center justify-between gap-3 rounded-lg bg-white/5 px-2.5 py-1.5 text-xs text-slate-300">
                      <span>{c.check}</span>
                      <ResultChip value={c.result} />
                    </li>
                  ))}
                </ul>
              </Tile>
            </Bento>
          )
        }}
      </DataState>
    </div>
  )
}
