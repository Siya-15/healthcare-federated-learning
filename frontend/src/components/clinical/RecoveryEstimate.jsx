import RangeBar from '../charts/RangeBar'
import { formatDays } from '../../utils/format'

// E9 recovery estimate — big number + range band.
export default function RecoveryEstimate({ recovery }) {
  if (!recovery) return <p className="text-sm text-slate-500">No recovery estimate provided.</p>
  const iv = recovery.interval_days || []
  return (
    <div className="space-y-2">
      <div>
        <span className="text-2xl font-bold text-slate-50">{formatDays(recovery.expected_days)}</span>
        <span className="ml-1 text-xs text-slate-500">expected</span>
      </div>
      {iv.length === 2 && (
        <RangeBar lo={iv[0]} hi={iv[1]} point={recovery.expected_days} color="#5b8def" unit="d" />
      )}
      <p className="text-[10px] leading-tight text-slate-600">
        {recovery.basis ? `${recovery.basis}. ` : ''}Model-derived estimate, not a guaranteed outcome.
      </p>
    </div>
  )
}
