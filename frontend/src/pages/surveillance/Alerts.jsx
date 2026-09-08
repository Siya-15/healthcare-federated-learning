import { useState } from 'react'
import { useApi } from '../../hooks/useApi'
import { getAlerts } from '../../services/surveillanceApi'
import { PageHeader, DataState, LevelBadge, Field } from '../../components/common/ui'
import { Bento, Tile } from '../../components/common/Bento'
import DataTable from '../../components/tables/DataTable'

const LEVEL_COLOR = { GREEN: '#34d399', YELLOW: '#eab308', ORANGE: '#fb923c', RED: '#f87171' }

function ScoreBar({ value, level }) {
  return (
    <div className="flex items-center gap-2">
      <div className="h-1.5 w-16 overflow-hidden rounded-full bg-white/8">
        <div className="h-full rounded-full" style={{ width: `${value * 100}%`, background: LEVEL_COLOR[level] || '#5b8def' }} />
      </div>
      <span className="font-mono text-xs text-slate-400">{value.toFixed(2)}</span>
    </div>
  )
}

export default function SurveillanceAlerts() {
  const query = useApi(({ signal }) => getAlerts({ signal }), [])
  const [openId, setOpenId] = useState(null)

  return (
    <div className="mx-auto max-w-6xl px-6 py-6">
      <PageHeader title="Alerts" subtitle="Current surveillance alerts and their evidence" />
      <DataState query={query} feature="alerts">
        {(d) => {
          const rows = d.items || []
          const open = rows.find((r) => r.id === openId)
          const counts = rows.reduce((m, r) => ({ ...m, [r.alert_level]: (m[r.alert_level] || 0) + 1 }), {})
          return (
            <Bento>
              <Tile col={2} title="By level">
                <div className="space-y-2">
                  {['RED', 'ORANGE', 'YELLOW', 'GREEN'].map((lv) => (
                    <div key={lv} className="flex items-center gap-2">
                      <LevelBadge value={lv} />
                      <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-white/8">
                        <div
                          className="h-full rounded-full"
                          style={{ width: `${((counts[lv] || 0) / Math.max(rows.length, 1)) * 100}%`, background: LEVEL_COLOR[lv] }}
                        />
                      </div>
                      <span className="w-4 text-right text-xs text-slate-400">{counts[lv] || 0}</span>
                    </div>
                  ))}
                </div>
              </Tile>

              <Tile col={4} title="Active alerts">
                <DataTable
                  minWidth={480}
                  rows={rows}
                  rowKey={(r) => r.id}
                  selectedKey={openId}
                  onSelect={(k) => setOpenId(k === openId ? null : k)}
                  columns={[
                    { key: 'hospital_id', header: 'Hosp' },
                    { key: 'disease_name', header: 'Disease' },
                    { key: 'alert_level', header: 'Level', render: (r) => <LevelBadge value={r.alert_level} /> },
                    { key: 'score', header: 'Score', render: (r) => <ScoreBar value={r.score} level={r.alert_level} /> },
                    { key: 'persistence_weeks', header: 'Wks', align: 'right' },
                  ]}
                />
                <p className="mt-2 text-[11px] text-slate-500">Select a row for evidence.</p>
              </Tile>

              {open ? (
                <Tile col={6} title={`Alert ${open.id}`} right={<LevelBadge value={open.alert_level} />}>
                  <div className="grid gap-3 md:grid-cols-2">
                    <dl className="grid grid-cols-2 gap-2">
                      <Field label="Hospital">{open.hospital_id}</Field>
                      <Field label="Disease">{open.disease_name}</Field>
                      <Field label="Persistence">{open.persistence_weeks} week(s)</Field>
                      <Field label="Spatial">{open.spatial_note}</Field>
                    </dl>
                    <div>
                      <div className="text-xs font-medium uppercase tracking-wide text-slate-500">Drivers</div>
                      <ul className="mt-1 list-disc space-y-0.5 pl-4 text-sm text-slate-200">
                        {open.drivers.map((x, i) => (
                          <li key={i}>{x}</li>
                        ))}
                      </ul>
                    </div>
                  </div>
                  <div className="mt-3 rounded-lg bg-white/5 p-3 text-sm text-slate-300">
                    <span className="font-semibold">Recommended action: </span>
                    {open.recommended_action}
                  </div>
                  <p className="mt-2 text-[11px] text-slate-500">
                    Prototype surveillance signal. Not a confirmed outbreak or pathogen identification.
                  </p>
                </Tile>
              ) : null}
            </Bento>
          )
        }}
      </DataState>
    </div>
  )
}
