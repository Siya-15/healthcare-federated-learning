import SegmentMeter from '../charts/SegmentMeter'

// E10 risk & complications — content for a bento tile.
export default function RiskPanel({ risk }) {
  if (!risk) return <p className="text-sm text-slate-500">No risk information provided.</p>
  return (
    <div className="space-y-2">
      <SegmentMeter value={risk.level} goodIsLow />
      {risk.complication_flags?.length ? (
        <ul className="list-disc space-y-0.5 pl-4 text-xs text-slate-300">
          {risk.complication_flags.map((f, i) => (
            <li key={i}>{f}</li>
          ))}
        </ul>
      ) : (
        <p className="text-xs text-slate-500">No complication flags for this profile.</p>
      )}
      <p className="text-[10px] leading-tight text-slate-600">Project-defined rule-based indicators (E10). Not a contraindication list.</p>
    </div>
  )
}
