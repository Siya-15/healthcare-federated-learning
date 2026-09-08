// Visualises the E1 -> E12 treatment-advisor pipeline (spec sections 5 & 12).
const STAGES = [
  ['E1', 'Context'], ['E2', 'Candidates'], ['E3', 'Eligibility'], ['E4', 'Config'],
  ['E5', 'Regional'], ['E6', 'Success'], ['E7', 'Calibration'], ['E8', 'Uncertainty'],
  ['E9', 'Recovery'], ['E10', 'Risk'], ['E11', 'SHAP'], ['E12', 'Ranking'],
]

export default function PipelineStrip({ highlight, compact }) {
  return (
    <div className="flex flex-wrap items-center gap-1">
      {STAGES.map(([code, label], i) => (
        <span key={code} className="flex items-center gap-1">
          <span
            className={`rounded border px-1.5 py-0.5 text-[11px] ${
              highlight === code
                ? 'border-accent-blue/50 bg-brand/10 text-accent-blue'
                : 'border-line bg-ink-800 text-slate-400'
            }`}
          >
            <span className="font-mono font-semibold">{code}</span>
            {!compact && <span className="ml-1">{label}</span>}
          </span>
          {i < STAGES.length - 1 && <span className="text-slate-600">→</span>}
        </span>
      ))}
    </div>
  )
}
