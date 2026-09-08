import { Link } from 'react-router-dom'
import { useApi } from '../../hooks/useApi'
import { useRole } from '../../app/auth/RoleContext'
import { getDoctorDashboard } from '../../services/clinicalApi'
import { PageHeader, KpiCard, LevelBadge, StatusPill, DataState } from '../../components/common/ui'
import { Bento, Tile } from '../../components/common/Bento'
import BarCompareChart from '../../components/charts/BarCompareChart'
import DonutChart from '../../components/charts/DonutChart'
import DataTable from '../../components/tables/DataTable'

function greeting() {
  const h = new Date().getHours()
  if (h < 12) return 'Good morning'
  if (h < 18) return 'Good afternoon'
  return 'Good evening'
}
const dateLabel = new Date().toLocaleDateString(undefined, { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' })

export default function DoctorDashboard() {
  const { hospitalId } = useRole()
  const query = useApi(({ signal }) => getDoctorDashboard({ signal }), [hospitalId])

  return (
    <div className="mx-auto max-w-6xl px-6 py-6">
      <PageHeader title={`${greeting()}, Dr. Rivera ☀`} subtitle={`${dateLabel} · Hospital ${hospitalId}`}>
        <StatusPill>Live Monitoring</StatusPill>
      </PageHeader>

      <DataState query={query} feature="the dashboard">
        {(d) => (
          <Bento>
            <div className="md:col-span-6 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
              <KpiCard label="Active Patients" value={d.kpis.active_patients.value.toLocaleString()} delta={d.kpis.active_patients.delta} deltaTone="up" spark={d.kpis.active_patients.spark} icon="👥" iconTone="brand" sparkColor="#34d399" />
              <KpiCard label="Critical Alerts" value={d.kpis.critical_alerts.value} delta={d.kpis.critical_alerts.delta} deltaTone="warn" spark={d.kpis.critical_alerts.spark} icon="⚠" iconTone="orange" sparkColor="#fb923c" />
              <KpiCard label="Avg Recovery Score" value={d.kpis.avg_recovery_score.value} delta={d.kpis.avg_recovery_score.delta} deltaTone="warn" spark={d.kpis.avg_recovery_score.spark} icon="↺" iconTone="orange" sparkColor="#fb923c" />
              <KpiCard label="Advisor Runs" value={d.kpis.advisor_runs.value} delta={d.kpis.advisor_runs.delta} deltaTone="up" spark={d.kpis.advisor_runs.spark} icon="✦" iconTone="purple" sparkColor="#a78bfa" />
            </div>

            <Tile col={4} title="Weekly Admissions" subtitle="Emergency vs Scheduled">
              <BarCompareChart
                height={220}
                data={d.weekly_admissions}
                series={[
                  { key: 'Emergency', name: 'Emergency', hatch: true },
                  { key: 'Scheduled', name: 'Scheduled', color: '#5b8def' },
                ]}
              />
              <div className="mt-1 flex gap-5 text-xs text-slate-400">
                <span className="flex items-center gap-1.5"><span className="inline-block h-2.5 w-2.5 rounded-sm bg-ink-600" /> Emergency</span>
                <span className="flex items-center gap-1.5"><span className="inline-block h-2.5 w-2.5 rounded-sm bg-accent-blue" /> Scheduled</span>
              </div>
            </Tile>

            <Tile col={2} title="Diagnosis Mix" subtitle="Current cohort">
              <DonutChart data={d.diagnosis_mix} centerValue={d.kpis.active_patients.value.toLocaleString()} centerLabel="patients" height={180} />
            </Tile>

            <Tile col={4} title="Priority Patient Queue" subtitle="Sorted by AI risk score">
              <DataTable
                minWidth={0}
                rows={d.priority_queue}
                rowKey={(r) => r.patient_token}
                columns={[
                  { key: 'patient_token', header: 'Patient', render: (r) => <span className="font-mono text-xs">{r.patient_token}</span> },
                  { key: 'disease_name', header: 'Dx' },
                  { key: 'risk', header: 'Risk', render: (r) => <LevelBadge value={r.risk} /> },
                  { key: 'reason', header: 'Signal', className: 'text-xs text-slate-500' },
                ]}
              />
            </Tile>

            <Tile col={2} title="At a glance">
              <div className="space-y-3">
                <div className="rounded-lg bg-white/5 p-2.5">
                  <div className="flex items-center justify-between">
                    <span className="text-xs text-slate-500">Local alert</span>
                    <LevelBadge value={d.local_alert?.alert_level} />
                  </div>
                  <p className="mt-1 text-xs text-slate-300">
                    {d.local_alert?.disease_name} at {d.local_alert?.hospital_id}
                  </p>
                </div>
                <div className="flex flex-col gap-1.5 text-sm">
                  <Link className="text-accent-blue hover:underline" to="/doctor/new-encounter">→ New encounter → advisor</Link>
                  <Link className="text-accent-blue hover:underline" to="/doctor/advisor">→ Advisor by encounter ID</Link>
                  <Link className="text-accent-blue hover:underline" to="/doctor/history">→ Encounter history</Link>
                </div>
              </div>
            </Tile>

            <Tile col={6} plain>
              <p className="text-[11px] text-slate-500">
                Treatment-success probabilities are model-based observational associations, not causal
                effect estimates. Decision support only — the clinician decides. All figures are sample data.
              </p>
            </Tile>
          </Bento>
        )}
      </DataState>
    </div>
  )
}
