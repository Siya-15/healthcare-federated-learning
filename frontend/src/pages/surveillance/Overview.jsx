import { useApi } from '../../hooks/useApi'
import { getOverview } from '../../services/surveillanceApi'
import { PageHeader, LevelBadge, DataState, InfoNote, Stat } from '../../components/common/ui'
import { Bento, Tile } from '../../components/common/Bento'
import GaugeMeter from '../../components/charts/GaugeMeter'
import DataTable from '../../components/tables/DataTable'

const LEVEL_VAL = { GREEN: 0.2, YELLOW: 0.5, ORANGE: 0.75, RED: 1 }
const LEVEL_COLOR = { GREEN: '#34d399', YELLOW: '#eab308', ORANGE: '#fb923c', RED: '#f87171' }

export default function SurveillanceOverview() {
  const query = useApi(({ signal }) => getOverview({ signal }), [])
  return (
    <div className="mx-auto max-w-6xl px-6 py-6">
      <PageHeader title="Surveillance Overview" subtitle="Aggregate signals across the hospital network — no patient records" />
      <DataState query={query} feature="the surveillance overview">
        {(d) => (
          <>
            <Bento>
              <Tile col={2} title="Network alert level">
                <div className="flex items-center justify-center">
                  <GaugeMeter
                    value={LEVEL_VAL[d.current_alert_level] ?? 0.2}
                    color={LEVEL_COLOR[d.current_alert_level] || '#34d399'}
                    label={d.current_alert_level}
                  />
                </div>
              </Tile>
              <Tile col={2} title="Monitored hospitals">
                <Stat label="Hospitals" value={d.monitored_hospitals} hint={`period ${d.surveillance_period}`} />
              </Tile>
              <Tile col={2} title="Active signals">
                <Stat label="Signals" value={d.active_signals} hint={`updated ${d.updated_at}`} />
              </Tile>

              <Tile col={6} title="Headline signals">
                <DataTable
                  minWidth={520}
                  rows={d.headline_signals}
                  rowKey={(r) => r.hospital_id + r.disease_name}
                  columns={[
                    { key: 'hospital_id', header: 'Hospital' },
                    { key: 'disease_name', header: 'Disease' },
                    { key: 'alert_level', header: 'Level', render: (r) => <LevelBadge value={r.alert_level} /> },
                    { key: 'driver', header: 'Main driver', className: 'text-slate-400' },
                  ]}
                />
              </Tile>
            </Bento>
            <InfoNote tone="amber">{d.scope_note}</InfoNote>
          </>
        )}
      </DataState>
    </div>
  )
}
