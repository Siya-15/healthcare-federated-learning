import { useApi } from '../../hooks/useApi'
import { getEmergingSymptoms } from '../../services/surveillanceApi'
import { PageHeader, DataState, LevelBadge, InfoNote } from '../../components/common/ui'
import { Bento, Tile } from '../../components/common/Bento'
import MiniBars from '../../components/charts/MiniBars'
import DataTable from '../../components/tables/DataTable'

export default function EmergingSymptoms() {
  const query = useApi(({ signal }) => getEmergingSymptoms({ signal }), [])
  return (
    <div className="mx-auto max-w-6xl px-6 py-6">
      <PageHeader title="Emerging Symptoms" subtitle="Unusual / recurring symptom combinations vs baseline (Objective A)" />
      <DataState query={query} feature="emerging-symptom analysis">
        {(d) => (
          <>
            <Bento>
              <Tile col={2} title="Emergence score" subtitle="higher = more anomalous">
                <MiniBars
                  max={1}
                  items={d.patterns.map((p) => ({
                    label: p.pattern.split(' + ').slice(0, 2).join(' + ') + '…',
                    value: p.emergence_score,
                    display: p.emergence_score.toFixed(2),
                    color: p.emergence_score > 0.6 ? '#fb923c' : '#5b8def',
                  }))}
                />
              </Tile>
              <Tile col={4} title="Patterns under watch" scroll>
                <DataTable
                  minWidth={520}
                  rows={d.patterns}
                  rowKey={(r) => r.pattern}
                  columns={[
                    { key: 'pattern', header: 'Symptom pattern' },
                    { key: 'hospital_count', header: 'Hosp', align: 'right' },
                    { key: 'frequency', header: 'Freq', align: 'right' },
                    { key: 'emergence_score', header: 'Emrg', align: 'right', render: (r) => r.emergence_score.toFixed(2) },
                    { key: 'status', header: 'Status', render: (r) => <LevelBadge value={r.status} /> },
                    { key: 'first_seen', header: 'Since' },
                  ]}
                />
              </Tile>
            </Bento>
            <InfoNote tone="amber">
              {d.scope_note} An atypical pattern is <strong>not</strong> a newly identified pathogen or variant.
            </InfoNote>
          </>
        )}
      </DataState>
    </div>
  )
}
