import { NavLink, Navigate, Route, Routes } from 'react-router-dom'

import Clinical from './views/Clinical'
import Dashboard from './views/Dashboard'
import FederatedLearning from './views/FederatedLearning'
import Privacy from './views/Privacy'
import Surveillance from './views/Surveillance'
import TreatmentAdvisor from './views/TreatmentAdvisor'

// The six core views named in md_files/04_BACKEND_FRONTEND_INTEGRATION.md.
const NAV = [
  { to: '/dashboard', label: 'Dashboard' },
  { to: '/clinical', label: 'Clinical' },
  { to: '/surveillance', label: 'Surveillance' },
  { to: '/federated-learning', label: 'Federated Learning' },
  { to: '/treatment', label: 'Treatment Advisor' },
  { to: '/privacy', label: 'Privacy / Audit' },
]

export default function App() {
  return (
    <div className="min-h-screen">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto max-w-7xl px-6 py-4">
          <h1 className="text-lg font-bold text-slate-900">
            Healthcare Federated Learning
          </h1>
          <p className="text-xs text-slate-500">
            Review 2 prototype · 10 simulated hospitals · decision support only
          </p>
        </div>
        <nav className="mx-auto flex max-w-7xl gap-1 overflow-x-auto px-6">
          {NAV.map((n) => (
            <NavLink
              key={n.to}
              to={n.to}
              className={({ isActive }) =>
                `whitespace-nowrap border-b-2 px-3 py-2 text-sm font-medium transition ${
                  isActive
                    ? 'border-slate-900 text-slate-900'
                    : 'border-transparent text-slate-500 hover:text-slate-800'
                }`
              }
            >
              {n.label}
            </NavLink>
          ))}
        </nav>
      </header>

      <main className="mx-auto max-w-7xl px-6 py-6">
        <Routes>
          <Route path="/" element={<Navigate to="/dashboard" replace />} />
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/clinical" element={<Clinical />} />
          <Route path="/surveillance" element={<Surveillance />} />
          <Route path="/federated-learning" element={<FederatedLearning />} />
          <Route path="/treatment" element={<TreatmentAdvisor />} />
          <Route path="/privacy" element={<Privacy />} />
        </Routes>
      </main>

      <footer className="mx-auto max-w-7xl px-6 pb-8 pt-2 text-xs text-slate-400">
        Simulated data. Not for clinical use.
      </footer>
    </div>
  )
}
