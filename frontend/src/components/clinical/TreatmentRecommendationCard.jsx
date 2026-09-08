import { LevelBadge } from '../common/ui'
import { formatScore, humanizeEnum } from '../../utils/format'
import GaugeMeter from '../charts/GaugeMeter'

// Detail for the selected recommendation — compact, gauge-led.
export default function TreatmentRecommendationCard({ recommendation }) {
  if (!recommendation) return <p className="text-sm text-slate-500">Select a row to see details.</p>

  const r = recommendation
  const cfg = r.clinical_configuration || {}
  const s = r.treatment_success || {}

  return (
    <div className="space-y-3">
      <div>
        <div className="flex items-start justify-between gap-2">
          <h3 className="text-sm font-semibold text-slate-100">{r.treatment_name}</h3>
          <span className="shrink-0 rounded bg-white/10 px-1.5 py-0.5 text-[11px] font-semibold text-slate-400">
            rank {r.rank}
          </span>
        </div>
        <div className="mt-0.5 flex items-center gap-1.5 text-[11px] text-slate-500">
          <span>{r.treatment_id}</span>
          {r.first_line && <span className="rounded bg-accent-blue/15 px-1 text-accent-blue">first-line</span>}
        </div>
      </div>

      <div className="flex items-center gap-3">
        <GaugeMeter value={s.calibrated_probability} label="modelled success" size={104} />
        <div className="space-y-1 text-xs">
          <div>
            <span className="text-slate-500">E12 score </span>
            <span className="font-mono font-semibold text-slate-200">{formatScore(r.final_score)}</span>
          </div>
          <div>
            <span className="text-slate-500">raw p </span>
            <span className="font-mono text-slate-300">{s.raw_probability != null ? s.raw_probability.toFixed(2) : '—'}</span>
          </div>
        </div>
      </div>

      {cfg.safety_review_required && (
        <div className="rounded-lg border border-amber-500/25 bg-amber-500/10 px-2.5 py-1.5 text-[11px] font-medium text-amber-200">
          Safety review required — do not action without clinician sign-off.
        </div>
      )}

      <div className="grid grid-cols-3 gap-2 text-center text-[11px]">
        <div className="rounded-lg bg-white/5 py-1.5">
          <div className="text-slate-500">Availability</div>
          <div className="mt-0.5"><LevelBadge value={cfg.availability} /></div>
        </div>
        <div className="rounded-lg bg-white/5 py-1.5">
          <div className="text-slate-500">Guideline</div>
          <div className="mt-0.5 font-medium text-slate-300">{humanizeEnum(cfg.guideline_status)}</div>
        </div>
        <div className="rounded-lg bg-white/5 py-1.5">
          <div className="text-slate-500">Resource</div>
          <div className="mt-0.5"><LevelBadge value={cfg.resource_tier} /></div>
        </div>
      </div>
    </div>
  )
}
