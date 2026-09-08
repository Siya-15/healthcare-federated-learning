// E11 SHAP feature attributions — diverging bars. Associational, not causal (§13).
export default function ExplainabilityPanel({ explainability }) {
  const features = (explainability?.top_features || []).slice(0, 6)
  const maxAbs = features.reduce((m, f) => Math.max(m, Math.abs(Number(f.contribution) || 0)), 0) || 1

  if (!features.length) return <p className="text-sm text-slate-500">No feature attributions provided.</p>

  return (
    <div className="space-y-2">
      <ul className="space-y-1.5">
        {features.map((f, i) => {
          const c = Number(f.contribution) || 0
          const w = (Math.abs(c) / maxAbs) * 50
          const pos = c >= 0
          return (
            <li key={i} className="text-xs">
              <div className="flex items-center justify-between">
                <span className="truncate font-medium text-slate-300">
                  {f.feature}
                  {f.value != null && <span className="ml-1 text-slate-500">= {String(f.value)}</span>}
                </span>
                <span className={`ml-2 shrink-0 tabular-nums ${pos ? 'text-emerald-300' : 'text-red-300'}`}>
                  {c > 0 ? '+' : ''}
                  {c.toFixed(2)}
                </span>
              </div>
              <div className="mt-1 flex h-1.5">
                <div className="flex w-1/2 justify-end">
                  {!pos && <div className="rounded-l-full bg-red-400" style={{ width: `${w * 2}%` }} />}
                </div>
                <div className="flex w-1/2">
                  {pos && <div className="rounded-r-full bg-emerald-500" style={{ width: `${w * 2}%` }} />}
                </div>
              </div>
            </li>
          )
        })}
      </ul>
      <p className="text-[10px] leading-tight text-slate-600">
        {explainability?.disclaimer || 'Feature attributions are associational, not causal.'} They
        explain the model score, not the patient outcome.
      </p>
    </div>
  )
}
