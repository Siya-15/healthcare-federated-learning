import { useApi } from '../../hooks/useApi'
import { getNetwork } from '../../services/federatedApi'
import { PageHeader, DataState, LevelBadge } from '../../components/common/ui'
import { Bento, Tile } from '../../components/common/Bento'
import DataTable from '../../components/tables/DataTable'

export default function FederatedHospitals() {
  const query = useApi(({ signal }) => getNetwork({ signal }), [])
  return (
    <div className="mx-auto max-w-6xl px-6 py-6">
      <PageHeader title="Hospital Participation" subtitle="H001–H010 local training and update status" />
      <DataState query={query} feature="hospital participation">
        {(d) => (
          <Bento>
            <Tile col={2} title="Nodes">
              <div className="grid grid-cols-5 gap-1.5">
                {d.hospitals.map((h) => {
                  const ok = h.update_approved && h.local_training === 'COMPLETE'
                  return (
                    <div
                      key={h.hospital_id}
                      title={`${h.hospital_id} · ${h.local_training} · ${h.examples} ex`}
                      className={`rounded-md py-2 text-center text-[11px] font-semibold ${
                        ok ? 'bg-emerald-500/15 text-emerald-300' : 'bg-white/5 text-slate-400'
                      }`}
                    >
                      {h.hospital_id.replace('H0', '')}
                    </div>
                  )
                })}
              </div>
              <p className="mt-2 text-[11px] text-slate-500">10/10 submitted &amp; approved</p>
            </Tile>

            <Tile col={4} title="Detail" scroll>
              <DataTable
                minWidth={520}
                rows={d.hospitals}
                rowKey={(r) => r.hospital_id}
                columns={[
                  { key: 'hospital_id', header: 'Hospital' },
                  { key: 'local_training', header: 'Training', render: (r) => <LevelBadge value={r.local_training} /> },
                  { key: 'update_submitted', header: 'Submitted', render: (r) => (r.update_submitted ? '✓' : '—') },
                  { key: 'update_approved', header: 'Approved', render: (r) => (r.update_approved ? '✓' : '—') },
                  { key: 'local_epochs', header: 'Epochs', align: 'right' },
                  { key: 'examples', header: 'Examples', align: 'right' },
                ]}
              />
            </Tile>
            <Tile col={6} plain>
              <p className="text-[11px] text-slate-500">
                Counts are metadata. Raw local datasets and parameter arrays are never exposed here.
              </p>
            </Tile>
          </Bento>
        )}
      </DataState>
    </div>
  )
}
