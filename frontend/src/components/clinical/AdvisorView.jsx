import { useEffect, useMemo, useState } from 'react'
import { Bento, Tile } from '../common/Bento'
import { StatusPill, Tag } from '../common/ui'
import { formatDateTime } from '../../utils/format'

import PatientContextCard from './PatientContextCard'
import RecommendationTable from './RecommendationTable'
import TreatmentRecommendationCard from './TreatmentRecommendationCard'
import RiskPanel from './RiskPanel'
import RecoveryEstimate from './RecoveryEstimate'
import RegionalContextPanel from './RegionalContextPanel'
import ExplainabilityPanel from './ExplainabilityPanel'
import AdvisorDisclaimer from './AdvisorDisclaimer'
import UncertaintyBadge from './UncertaintyBadge'
import PipelineStrip from './PipelineStrip'

function HeaderStrip({ data }) {
  const p = data?.patient_context || {}
  const cells = [
    ['Hospital', p.hospital_name || p.hospital_id],
    ['Encounter', data?.encounter_id],
    ['Disease', p.disease_name],
    ['Severity', p.severity_label],
  ]
  return (
    <div className="flex flex-wrap items-center justify-between gap-x-6 gap-y-2 rounded-2xl border border-line bg-ink-850 px-5 py-3">
      <div className="flex flex-wrap gap-x-6 gap-y-1">
        {cells.map(([label, value]) => (
          <div key={label}>
            <div className="text-[10px] font-medium uppercase tracking-wide text-slate-500">{label}</div>
            <div className="text-sm font-semibold text-slate-100">{value || '—'}</div>
          </div>
        ))}
      </div>
      <div className="flex items-center gap-3">
        <span className="hidden text-[11px] text-slate-500 lg:inline">
          {data?.advisor_version} · {data?.model_version} · {formatDateTime(data?.generated_at)}
        </span>
        <StatusPill tone={data?.advisor_status === 'COMPLETED' ? 'brand' : 'amber'}>
          {data?.advisor_status || '—'}
        </StatusPill>
      </div>
    </div>
  )
}

// Full E13 payload as a dense bento — fits ~1 screen, minimal scroll.
export default function AdvisorView({ data }) {
  const [selectedRank, setSelectedRank] = useState(1)
  useEffect(() => setSelectedRank(1), [data?.encounter_id])

  const selected = useMemo(() => {
    const recs = data?.recommendations || []
    return recs.find((r) => r.rank === selectedRank) || recs[0] || null
  }, [data, selectedRank])

  const noCandidates =
    data && (data.advisor_status === 'NO_CANDIDATES' || (data.recommendations || []).length === 0)

  if (noCandidates) {
    return (
      <div className="space-y-3">
        <HeaderStrip data={data} />
        <Bento>
          <Tile col={6} title="No recommendation">
            <p className="text-sm text-slate-400">
              The advisor produced no treatment candidates for this encounter (status{' '}
              <span className="font-mono">{data.advisor_status}</span>). No treatment is being suggested —
              only that no configured mapping applied.
            </p>
          </Tile>
        </Bento>
        <AdvisorDisclaimer text={data.disclaimer} />
      </div>
    )
  }

  return (
    <div className="space-y-3">
      <HeaderStrip data={data} />

      <Bento>
        <Tile col={2} title="Patient context" subtitle="E1">
          <PatientContextCard context={data.patient_context} />
        </Tile>

        <Tile col={4} row={2} title="Ranked options" subtitle="E12 weighted score — select a row">
          <RecommendationTable
            recommendations={data.recommendations}
            selectedRank={selected?.rank}
            onSelect={setSelectedRank}
          />
        </Tile>

        <Tile col={2} title="Selected treatment" right={selected?.first_line ? <Tag tone="blue">first-line</Tag> : null}>
          <TreatmentRecommendationCard recommendation={selected} />
        </Tile>

        <Tile col={2} title="Risk" subtitle="E10">
          <RiskPanel risk={selected?.risk} />
        </Tile>
        <Tile col={2} title="Uncertainty" subtitle="E8">
          <UncertaintyBadge uncertainty={selected?.uncertainty} />
        </Tile>
        <Tile col={2} title="Recovery" subtitle="E9">
          <RecoveryEstimate recovery={selected?.recovery} />
        </Tile>

        <Tile col={3} title="Why this scored" subtitle={`${selected?.explainability?.method || 'SHAP (E11)'} · ${selected?.treatment_name || ''}`}>
          <ExplainabilityPanel explainability={selected?.explainability} />
        </Tile>
        <Tile col={3} title="Regional context" subtitle="E5 — aggregate, not patient data">
          <RegionalContextPanel regional={data.regional_epidemiology} />
        </Tile>

        <Tile col={4} title="Excluded options" subtitle="Removed before ranking — shown for transparency">
          {data.excluded_treatments?.length ? (
            <ul className="space-y-1.5">
              {data.excluded_treatments.map((x, i) => (
                <li key={i} className="rounded-lg bg-white/5 px-2.5 py-1.5 text-xs">
                  <span className="font-medium text-slate-200">{x.treatment_name}</span>
                  <span className="ml-1.5 text-slate-500">{x.treatment_id}{x.stage ? ` · ${x.stage}` : ''}</span>
                  <p className="mt-0.5 text-[11px] text-slate-400">{x.reason}</p>
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-sm text-slate-500">No treatments were excluded.</p>
          )}
        </Tile>
        <Tile col={2} title="Pipeline" subtitle="E1 → E12">
          <PipelineStrip highlight="E12" compact />
        </Tile>
      </Bento>

      <AdvisorDisclaimer text={data.disclaimer} />
    </div>
  )
}
