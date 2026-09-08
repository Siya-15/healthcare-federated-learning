import { LevelBadge } from '../common/ui'
import MiniBars from '../charts/MiniBars'
import { trendArrow, formatDate } from '../../utils/format'

// E5 regional epidemiology — content for a bento tile. Explicit "unavailable"
// state; never synthesise regional data (§13).
export default function RegionalContextPanel({ regional }) {
  if (!regional || regional.available === false) {
    return (
      <p className="text-sm text-slate-500">
        Regional epidemiology context is not available for this encounter. No regional activity or
        trend is shown.
      </p>
    )
  }

  const { disease_name, activity_level, trend, recent_case_count, baseline_case_count, as_of, note } = regional

  return (
    <div className="space-y-2.5">
      <div className="flex items-center justify-between">
        <span className="text-sm text-slate-200">{disease_name ?? '—'}</span>
        <LevelBadge value={activity_level} />
      </div>
      <div className="text-xs text-slate-400">
        Trend <span className="font-medium text-slate-200">{trendArrow(trend)} {trend ?? '—'}</span>
        <span className="mx-1.5 text-slate-600">·</span>
        as of {formatDate(as_of)}
      </div>
      {(recent_case_count != null || baseline_case_count != null) && (
        <MiniBars
          items={[
            { label: 'Baseline', value: baseline_case_count ?? 0, display: baseline_case_count ?? 0, color: '#64748b' },
            { label: 'Recent', value: recent_case_count ?? 0, display: recent_case_count ?? 0, color: '#fb923c' },
          ]}
        />
      )}
      {note && <p className="text-[10px] leading-tight text-slate-600">{note}</p>}
    </div>
  )
}
