// Local clinical data -> local processing -> model update -> aggregation ->
// global model (spec section 11). Emphasises that raw data stays local.
export default function DataFlowDiagram({ steps = [] }) {
  return (
    <ol className="space-y-3">
      {steps.map((s, i) => {
        const leaves = /leaves|central|coordinator|shared/i.test(s.scope || '')
        return (
          <li key={i} className="flex gap-3">
            <div className="flex flex-col items-center">
              <div
                className={`flex h-8 w-8 items-center justify-center rounded-full text-xs font-bold ${
                  leaves ? 'bg-orange-500/15 text-orange-300' : 'bg-emerald-500/15 text-emerald-300'
                }`}
              >
                {i + 1}
              </div>
              {i < steps.length - 1 && <div className="my-1 w-px flex-1 bg-white/10" />}
            </div>
            <div className="pb-1">
              <div className="flex items-center gap-2">
                <span className="text-sm font-semibold text-slate-100">{s.step}</span>
                <span
                  className={`rounded px-1.5 py-0.5 text-[11px] font-medium ${
                    leaves ? 'bg-orange-500/15 text-orange-300' : 'bg-emerald-500/15 text-emerald-300'
                  }`}
                >
                  {s.scope}
                </span>
              </div>
              <p className="mt-0.5 text-xs text-slate-400">{s.detail}</p>
            </div>
          </li>
        )
      })}
    </ol>
  )
}
