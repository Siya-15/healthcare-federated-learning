import { useApi } from '../../hooks/useApi'
import { getTrends } from '../../services/surveillanceApi'
import { PageHeader, DataState, InfoNote } from '../../components/common/ui'
import { Bento, Tile } from '../../components/common/Bento'
import TrendChart from '../../components/charts/TrendChart'
import { pctChange, fmtDelta } from '../../utils/format'

export default function SurveillanceTrends() {
  const query = useApi(({ signal }) => getTrends({ signal }), [])
  return (
    <div className="mx-auto max-w-6xl px-6 py-6">
      <PageHeader title="Trends" subtitle="Weekly observed counts vs rolling baseline" />
      <DataState query={query} feature="trend data">
        {(d) => (
          <Bento>
            {d.series.map((s) => {
              const last = s.observed[s.observed.length - 1]
              const base = s.baseline[s.baseline.length - 1]
              const chg = pctChange(last, base)
              return (
                <Tile
                  key={s.disease_name}
                  col={2}
                  title={s.disease_name}
                  right={
                    chg != null && (
                      <span className={`text-xs font-semibold ${chg > 5 ? 'text-orange-300' : 'text-slate-400'}`}>
                        {fmtDelta(chg, 0)}% vs baseline
                      </span>
                    )
                  }
                >
                  <TrendChart
                    height={160}
                    data={d.weeks.map((w, i) => ({ x: w.replace('2026-', ''), Observed: s.observed[i], Baseline: s.baseline[i] }))}
                    series={[{ key: 'Observed' }, { key: 'Baseline', dashed: true }]}
                  />
                </Tile>
              )
            })}
            <Tile col={6} plain>
              <InfoNote>{d.growth_note}</InfoNote>
            </Tile>
          </Bento>
        )}
      </DataState>
    </div>
  )
}
