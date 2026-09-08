import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useApi } from '../../hooks/useApi'
import { getTreatmentAdvisor } from '../../services/clinicalApi'
import { PageHeader, DataState, LoadingAdvisor } from '../../components/common/ui'
import AdvisorView from '../../components/clinical/AdvisorView'

const DEFAULT_ENCOUNTER = 'ENC-7B7DEBF90A'

function EncounterPicker({ value, onSubmit }) {
  const [draft, setDraft] = useState(value)
  useEffect(() => setDraft(value), [value])
  return (
    <form
      onSubmit={(e) => {
        e.preventDefault()
        if (draft.trim()) onSubmit(draft.trim())
      }}
      className="flex items-center gap-2"
    >
      <input
        value={draft}
        onChange={(e) => setDraft(e.target.value)}
        placeholder="ENC-…"
        className="w-44 rounded-md border border-white/15 px-2 py-1 text-sm"
      />
      <button className="rounded-md bg-accent-blue px-3 py-1 text-sm font-semibold text-white hover:bg-accent-blue/90">
        Load
      </button>
    </form>
  )
}

export default function TreatmentAdvisor() {
  const { encounterId: routeId } = useParams()
  const navigate = useNavigate()
  const encounterId = routeId || DEFAULT_ENCOUNTER
  const query = useApi(({ signal }) => getTreatmentAdvisor(encounterId, { signal }), [encounterId])

  return (
    <div className="mx-auto max-w-6xl px-4 py-6">
      <PageHeader title="Treatment Advisor" subtitle="E1–E12 advisor for an existing encounter">
        <EncounterPicker
          value={encounterId}
          onSubmit={(id) => navigate(`/doctor/advisor/${encodeURIComponent(id)}`)}
        />
      </PageHeader>
      <DataState query={query} feature="the advisor" loader={<LoadingAdvisor />}>
        {(data) => <AdvisorView data={data} />}
      </DataState>
    </div>
  )
}
