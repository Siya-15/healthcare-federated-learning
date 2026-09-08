import { LevelBadge } from '../common/ui'
import { formatPct, formatScore, formatDays } from '../../utils/format'

// Compare the ranked treatment options (E12). Click a row to select it. The
// ranking is E12's project-defined weighted score — NOT a clinically validated
// ranking (footnote shown, not hidden).
export default function RecommendationTable({ recommendations = [], selectedRank, onSelect }) {
  if (!recommendations.length) {
    return <p className="text-sm text-slate-500">No treatment candidates were produced. Nothing is being recommended.</p>
  }

  const topScore = Math.max(...recommendations.map((r) => r.final_score || 0), 0.0001)

  return (
    <div>
      <div className="overflow-x-auto">
        <table className="w-full min-w-[560px] text-left text-sm">
          <thead>
            <tr className="border-b border-line text-[11px] uppercase tracking-wide text-slate-500">
              <th className="py-1.5 pr-2">#</th>
              <th className="py-1.5 pr-2">Treatment</th>
              <th className="py-1.5 pr-2">Success</th>
              <th className="py-1.5 pr-2">Unc.</th>
              <th className="py-1.5 pr-2">Rec.</th>
              <th className="py-1.5 pr-2">Risk</th>
              <th className="py-1.5 pr-2">Score</th>
            </tr>
          </thead>
          <tbody>
            {recommendations.map((r) => {
              const selected = r.rank === selectedRank
              return (
                <tr
                  key={r.treatment_id ?? r.rank}
                  onClick={() => onSelect?.(r.rank)}
                  className={`cursor-pointer border-b border-white/5 transition-colors ${
                    selected ? 'bg-brand/10' : 'hover:bg-white/[0.04]'
                  }`}
                >
                  <td className="py-2 pr-2 font-semibold text-slate-500">{r.rank}</td>
                  <td className="py-2 pr-2">
                    <div className="font-medium text-slate-100">{r.treatment_name}</div>
                    <div className="flex items-center gap-1.5 text-[11px] text-slate-500">
                      <span>{r.treatment_id}</span>
                      {r.first_line && (
                        <span className="rounded bg-accent-blue/15 px-1 font-medium text-accent-blue">first-line</span>
                      )}
                      {r.clinical_configuration?.safety_review_required && (
                        <span className="rounded bg-amber-500/15 px-1 font-medium text-amber-300">review</span>
                      )}
                    </div>
                  </td>
                  <td className="py-2 pr-2 text-slate-200">{formatPct(r.treatment_success?.calibrated_probability, 0)}</td>
                  <td className="py-2 pr-2">
                    <LevelBadge value={r.uncertainty?.level} />
                  </td>
                  <td className="py-2 pr-2 text-slate-300">{formatDays(r.recovery?.expected_days)}</td>
                  <td className="py-2 pr-2">
                    <LevelBadge value={r.risk?.level} />
                  </td>
                  <td className="py-2 pr-2">
                    <div className="flex items-center gap-1.5">
                      <div className="h-1.5 w-10 overflow-hidden rounded-full bg-white/8">
                        <div
                          className="h-full rounded-full bg-brand"
                          style={{ width: `${((r.final_score || 0) / topScore) * 100}%` }}
                        />
                      </div>
                      <span className="font-mono text-xs text-slate-400">{formatScore(r.final_score, 2)}</span>
                    </div>
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
      <p className="mt-2 text-[11px] leading-tight text-slate-500">
        Ordered by the E12 weighted score (success 40 · uncertainty 15 · recovery 15 · risk 15 ·
        availability 5 · guideline 5 · resource 5). Decision support, not a clinically validated ranking —
        the top row is not necessarily the correct treatment.
      </p>
    </div>
  )
}
