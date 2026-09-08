import { useNavigate } from 'react-router-dom'
import { useApi } from '../../hooks/useApi'
import { useRole } from '../../app/auth/RoleContext'
import { listEncounters } from '../../services/clinicalApi'
import { PageHeader, DataState, Tag } from '../../components/common/ui'
import { Bento, Tile } from '../../components/common/Bento'
import DataTable from '../../components/tables/DataTable'
import MiniBars from '../../components/charts/MiniBars'
import { formatDateTime } from '../../utils/format'

export default function EncounterHistory() {
  const { hospitalId } = useRole()
  const navigate = useNavigate()
  const query = useApi(({ signal }) => listEncounters({ hospital_id: hospitalId }, { signal }), [hospitalId])

  const columns = [
    { key: 'patient_token', header: 'Patient', render: (r) => <span className="font-mono text-xs">{r.patient_token}</span> },
    { key: 'visit_timestamp', header: 'Visit', render: (r) => formatDateTime(r.visit_timestamp) },
    { key: 'age', header: 'Age' },
    { key: 'disease_name', header: 'Disease' },
    { key: 'severity_label', header: 'Severity' },
    { key: 'symptoms', header: 'Sx', render: (r) => `${r.symptoms?.length ?? 0}` },
    { key: 'discharge_status', header: 'Status', render: (r) => <Tag>{r.discharge_status}</Tag> },
    {
      key: 'go',
      header: '',
      align: 'right',
      render: (r) => (
        <button
          onClick={() => navigate(`/doctor/advisor/${encodeURIComponent(r.encounter_id)}`)}
          className="rounded border border-white/15 px-2 py-0.5 text-xs font-medium text-slate-300 hover:bg-white/5"
        >
          Advisor →
        </button>
      ),
    },
  ]

  return (
    <div className="mx-auto max-w-6xl px-6 py-6">
      <PageHeader title="Encounter History" subtitle={`Hospital ${hospitalId} — authorised records only`} />
      <DataState query={query} feature="encounter history">
        {(d) => {
          const rows = d.items || []
          const byDx = Object.entries(
            rows.reduce((m, r) => ({ ...m, [r.disease_name]: (m[r.disease_name] || 0) + 1 }), {})
          ).map(([label, value]) => ({ label, value, display: value }))
          const byStatus = Object.entries(
            rows.reduce((m, r) => ({ ...m, [r.discharge_status]: (m[r.discharge_status] || 0) + 1 }), {})
          ).map(([label, value]) => ({ label, value, display: value, color: label === 'Referred' ? '#fb923c' : '#34d399' }))
          return (
            <Bento>
              <Tile col={2} title="Cohort by diagnosis">
                <MiniBars items={byDx} />
              </Tile>
              <Tile col={2} title="Discharge status">
                <MiniBars items={byStatus} />
              </Tile>
              <Tile col={2} title="Total">
                <div className="text-3xl font-bold text-slate-50">{rows.length}</div>
                <div className="text-xs text-slate-500">encounters in scope</div>
              </Tile>
              <Tile col={6} title="Encounters" subtitle="Keyed by patient_token — raw patient_id is never shown">
                <DataTable columns={columns} rows={rows} rowKey={(r) => r.encounter_id} minWidth={720} />
              </Tile>
            </Bento>
          )
        }}
      </DataState>
    </div>
  )
}
