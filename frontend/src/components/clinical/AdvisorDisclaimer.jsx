// Clinical decision-support disclaimer — shown verbatim, never hidden (§§12–13).
export default function AdvisorDisclaimer({ text }) {
  return (
    <div className="rounded-xl border border-amber-500/25 bg-amber-500/10 p-3 text-[11px] leading-relaxed text-amber-200">
      <span className="font-semibold uppercase tracking-wide">Clinical decision support only — </span>
      {text ||
        'not an autonomous prescription and not a clinical guideline. A qualified clinician is responsible for the final treatment decision.'}
    </div>
  )
}
