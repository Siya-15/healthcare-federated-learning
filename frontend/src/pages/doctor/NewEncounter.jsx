import { useState } from 'react'
import { useApi } from '../../hooks/useApi'
import { useRole } from '../../app/auth/RoleContext'
import { getFormOptions, runTreatmentAdvisor } from '../../services/clinicalApi'
import { PageHeader, Card, DataState, ErrorState, LoadingAdvisor, MockBanner } from '../../components/common/ui'
import EncounterForm from '../../components/clinical/EncounterForm'
import AdvisorView from '../../components/clinical/AdvisorView'

export default function NewEncounter() {
  const { hospitalId } = useRole()
  const optionsQuery = useApi(({ signal }) => getFormOptions({ signal }), [])

  const [result, setResult] = useState(null)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState(null)

  const handleSubmit = async (context) => {
    setSubmitting(true)
    setError(null)
    try {
      const data = await runTreatmentAdvisor(context)
      setResult(data)
    } catch (e) {
      setError(e)
      setResult(null)
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="mx-auto max-w-5xl px-4 py-6">
      <PageHeader
        title="New Encounter"
        subtitle="Enter clinical context, then run the E1–E12 advisor"
      >
        {result && (
          <button
            onClick={() => setResult(null)}
            className="rounded-md border border-white/15 bg-ink-800 px-3 py-1.5 text-sm font-medium text-slate-300 hover:bg-white/5"
          >
            ← Edit inputs
          </button>
        )}
      </PageHeader>

      {!result && (
        <DataState query={optionsQuery} feature="the form options">
          {(opts) => (
            <>
              <EncounterForm
                options={opts}
                defaultHospital={hospitalId}
                submitting={submitting}
                onSubmit={handleSubmit}
              />
              {error && (
                <div className="mt-4">
                  <ErrorState error={error} />
                </div>
              )}
              {submitting && (
                <div className="mt-4">
                  <LoadingAdvisor />
                </div>
              )}
            </>
          )}
        </DataState>
      )}

      {result && (
        <div className="space-y-4">
          {result._mock && <MockBanner feature="this advisor result" />}
          <Card title="Change an input and re-run">
            <p className="text-xs text-slate-400">
              Adjust severity, SpO₂ or age on the previous screen and analyse again — the ranked
              output responds to patient context (demo step 6).
            </p>
          </Card>
          <AdvisorView data={result} />
        </div>
      )}
    </div>
  )
}
