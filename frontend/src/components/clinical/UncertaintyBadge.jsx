import SegmentMeter from '../charts/SegmentMeter'
import RangeBar from '../charts/RangeBar'
import { formatPct } from '../../utils/format'

// E8 uncertainty — level meter + predictive-interval band. Never a CI (§13).
export default function UncertaintyBadge({ uncertainty }) {
  if (!uncertainty) return <p className="text-sm text-slate-500">No uncertainty estimate.</p>
  const iv = uncertainty.predictive_interval
  return (
    <div className="space-y-2">
      <SegmentMeter value={uncertainty.level} goodIsLow />
      {Array.isArray(iv) && (
        <RangeBar
          lo={iv[0]}
          hi={iv[1]}
          domainMin={0}
          domainMax={1}
          color="#a78bfa"
          formatValue={(v) => formatPct(v, 0)}
        />
      )}
      <p className="text-[10px] leading-tight text-slate-600">
        Model-derived predictive spread (E8), not a formal statistical confidence interval.
      </p>
    </div>
  )
}
