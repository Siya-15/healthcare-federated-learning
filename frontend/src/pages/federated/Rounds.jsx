import { useApi } from '../../hooks/useApi'
import { getRounds } from '../../services/federatedApi'
import { PageHeader, DataState, LevelBadge } from '../../components/common/ui'
import { Bento, Tile } from '../../components/common/Bento'
import DataTable from '../../components/tables/DataTable'
import TrendChart from '../../components/charts/TrendChart'

export default function FederatedRounds() {
  const query = useApi(({ signal }) => getRounds({ signal }), [])
  return (
    <div className="mx-auto max-w-6xl px-6 py-6">
      <PageHeader title="Federated Rounds" subtitle="Round history and aggregate metrics" />
      <DataState query={query} feature="round history">
        {(d) => {
          const rows = d.items || []
          const chart = rows.map((r) => ({
            x: `R${r.round}`,
            Accuracy: r.metrics.accuracy,
            'Micro-F1': r.metrics.micro_f1,
            'Macro-F1': r.metrics.macro_f1,
          }))
          return (
            <Bento>
              <Tile col={3} title="Metric progression">
                <TrendChart height={200} data={chart} series={[{ key: 'Accuracy' }, { key: 'Micro-F1' }, { key: 'Macro-F1' }]} />
                <p className="mt-1 text-[11px] text-slate-500">Micro-F1 not monotonic; Macro-F1 stays very low.</p>
              </Tile>
              <Tile col={3} title="Rounds" scroll>
                <DataTable
                  minWidth={480}
                  rows={rows}
                  rowKey={(r) => r.round}
                  columns={[
                    { key: 'round', header: 'R' },
                    { key: 'participating_nodes', header: 'Nodes', align: 'right' },
                    { key: 'status', header: 'Status', render: (r) => <LevelBadge value={r.status} /> },
                    { key: 'acc', header: 'Acc', align: 'right', render: (r) => r.metrics.accuracy.toFixed(3) },
                    { key: 'mic', header: 'Micro', align: 'right', render: (r) => r.metrics.micro_f1.toFixed(3) },
                    { key: 'mac', header: 'Macro', align: 'right', render: (r) => r.metrics.macro_f1.toFixed(3) },
                    { key: 'ham', header: 'Ham', align: 'right', render: (r) => r.metrics.hamming_loss.toFixed(3) },
                  ]}
                />
              </Tile>
            </Bento>
          )
        }}
      </DataState>
    </div>
  )
}
