import { useState } from 'react'
import { useApi } from '../../hooks/useApi'
import { getTreatmentAdvisor } from '../../services/clinicalApi'
import { PageHeader, DataState } from '../../components/common/ui'
import { Bento, Tile } from '../../components/common/Bento'
import ExplainabilityPanel from '../../components/clinical/ExplainabilityPanel'
import GaugeMeter from '../../components/charts/GaugeMeter'

// SHAP explanation viewer (E11). Pick an encounter + ranked treatment.
export default function Explanations() {
  const [encounterId, setEncounterId] = useState('ENC-7B7DEBF90A')
  const [submitted, setSubmitted] = useState('ENC-7B7DEBF90A')
  const [idx, setIdx] = useState(0)
  const query = useApi(({ signal }) => getTreatmentAdvisor(submitted, { signal }), [submitted])

  return (
    <div className="mx-auto max-w-5xl px-6 py-6">
      <PageHeader title="SHAP Explanations" subtitle="E11 feature attributions for a treatment inference">
        <form
          onSubmit={(e) => {
            e.preventDefault()
            setSubmitted(encounterId.trim())
          }}
          className="flex items-center gap-2"
        >
          <input value={encounterId} onChange={(e) => setEncounterId(e.target.value)} className="w-44 rounded-md border px-2 py-1 text-sm" />
          <button className="rounded-md bg-accent-blue px-3 py-1 text-sm font-semibold text-white hover:bg-accent-blue/90">Load</button>
        </form>
      </PageHeader>

      <DataState query={query} feature="the explanation">
        {(d) => {
          const recs = d.recommendations || []
          const rec = recs[Math.min(idx, recs.length - 1)] || null
          return (
            <Bento>
              <Tile col={2} title="Treatment">
                <select
                  value={idx}
                  onChange={(e) => setIdx(Number(e.target.value))}
                  className="w-full rounded-md border px-2 py-1.5 text-sm"
                >
                  {recs.map((r, i) => (
                    <option key={r.treatment_id} value={i}>
                      #{r.rank} — {r.treatment_name}
                    </option>
                  ))}
                </select>
                {rec && (
                  <div className="mt-3 flex justify-center">
                    <GaugeMeter value={rec.treatment_success?.calibrated_probability} label="modelled success" size={104} />
                  </div>
                )}
              </Tile>
              <Tile col={4} title="Feature attributions" subtitle={rec?.explainability?.method || 'SHAP (E11)'}>
                <ExplainabilityPanel explainability={rec?.explainability} />
              </Tile>
            </Bento>
          )
        }}
      </DataState>
    </div>
  )
}
