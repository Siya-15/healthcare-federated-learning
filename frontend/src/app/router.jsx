import { Navigate, Route, Routes } from 'react-router-dom'
import AppLayout from '../components/layout/AppLayout'
import RoleGuard from './roleGuard/RoleGuard'

import Home from '../pages/Home'

import DoctorDashboard from '../pages/doctor/Dashboard'
import NewEncounter from '../pages/doctor/NewEncounter'
import TreatmentAdvisor from '../pages/doctor/TreatmentAdvisor'
import EncounterHistory from '../pages/doctor/EncounterHistory'

import SurveillanceOverview from '../pages/surveillance/Overview'
import SurveillanceAlerts from '../pages/surveillance/Alerts'
import EmergingSymptoms from '../pages/surveillance/EmergingSymptoms'
import SurveillanceTrends from '../pages/surveillance/Trends'

import FederatedOverview from '../pages/federated/Overview'
import FederatedHospitals from '../pages/federated/Hospitals'
import FederatedRounds from '../pages/federated/Rounds'
import DataFlow from '../pages/federated/DataFlow'
import PrivacyControls from '../pages/privacy/Controls'
import PrivacyAudit from '../pages/privacy/Audit'
import DataMinimization from '../pages/privacy/DataMinimization'

import ModelOverview from '../pages/ai/ModelOverview'
import Metrics from '../pages/ai/Metrics'
import Versions from '../pages/ai/Versions'
import Explanations from '../pages/ai/Explanations'

const g = (key, el) => <RoleGuard portalKey={key}>{el}</RoleGuard>

export default function AppRouter() {
  return (
    <Routes>
      <Route element={<AppLayout />}>
        <Route index element={<Home />} />

        <Route path="doctor">
          <Route index element={g('doctor', <DoctorDashboard />)} />
          <Route path="new-encounter" element={g('doctor', <NewEncounter />)} />
          <Route path="advisor" element={g('doctor', <TreatmentAdvisor />)} />
          <Route path="advisor/:encounterId" element={g('doctor', <TreatmentAdvisor />)} />
          <Route path="history" element={g('doctor', <EncounterHistory />)} />
        </Route>

        <Route path="surveillance">
          <Route index element={g('surveillance', <SurveillanceOverview />)} />
          <Route path="alerts" element={g('surveillance', <SurveillanceAlerts />)} />
          <Route path="emerging" element={g('surveillance', <EmergingSymptoms />)} />
          <Route path="trends" element={g('surveillance', <SurveillanceTrends />)} />
        </Route>

        <Route path="federated">
          <Route index element={g('federated', <FederatedOverview />)} />
          <Route path="hospitals" element={g('federated', <FederatedHospitals />)} />
          <Route path="rounds" element={g('federated', <FederatedRounds />)} />
          <Route path="data-flow" element={g('federated', <DataFlow />)} />
          <Route path="privacy/controls" element={g('federated', <PrivacyControls />)} />
          <Route path="privacy/audit" element={g('federated', <PrivacyAudit />)} />
          <Route path="privacy/minimization" element={g('federated', <DataMinimization />)} />
        </Route>

        <Route path="ai">
          <Route index element={g('ai', <ModelOverview />)} />
          <Route path="metrics" element={g('ai', <Metrics />)} />
          <Route path="versions" element={g('ai', <Versions />)} />
          <Route path="explanations" element={g('ai', <Explanations />)} />
        </Route>

        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  )
}
