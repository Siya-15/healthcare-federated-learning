import { NavLink, Outlet, useLocation } from 'react-router-dom'
import { useRole, ROLES } from '../../app/auth/RoleContext'
import { HOSPITALS } from '../../mocks/master'

// Small glyphs so the sidebar reads like the design without an icon dependency.
const GLYPH = {
  Dashboard: '▣',
  'New Encounter': '＋',
  'Treatment Advisor': '✦',
  History: '⟲',
  Overview: '◉',
  Alerts: '△',
  'Emerging Symptoms': '❋',
  Trends: '📈',
  'Federated Overview': '⇄',
  'Hospital Participation': '🏥',
  Rounds: '↻',
  'Data Flow': '⋔',
  'Privacy Controls': '🛡',
  'Privacy Audit': '☑',
  'Data Minimization': '▤',
  'Model Overview': '⧉',
  Metrics: '📊',
  Versions: '⌗',
  'SHAP Explanations': '✦',
}

function Logo() {
  return (
    <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-white text-ink-900">
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round">
        <path d="M12 13a1 1 0 0 0 1-1V6" />
        <path d="M4.5 19a9 9 0 1 1 15 0" />
      </svg>
    </div>
  )
}

function DemoIdentityBar() {
  const { role, setRole, hospitalId, setHospitalId } = useRole()
  const needsHospital = role === 'DOCTOR' || role === 'HOSPITAL_ADMIN'
  return (
    <div className="flex flex-wrap items-center gap-2 text-xs">
      <span className="rounded bg-amber-500/15 px-1.5 py-0.5 font-semibold text-amber-300">DEMO</span>
      <label className="text-slate-500">Role</label>
      <select
        value={role}
        onChange={(e) => setRole(e.target.value)}
        className="rounded-md border px-2 py-1 text-xs"
      >
        {Object.entries(ROLES).map(([k, label]) => (
          <option key={k} value={k}>
            {label}
          </option>
        ))}
      </select>
      {needsHospital && (
        <>
          <label className="text-slate-500">Hospital</label>
          <select
            value={hospitalId}
            onChange={(e) => setHospitalId(e.target.value)}
            className="rounded-md border px-2 py-1 text-xs"
          >
            {HOSPITALS.map((h) => (
              <option key={h.hospital_id} value={h.hospital_id}>
                {h.hospital_id}
              </option>
            ))}
          </select>
        </>
      )}
    </div>
  )
}

function NavItem({ to, end, label }) {
  return (
    <NavLink
      to={to}
      end={end}
      className={({ isActive }) =>
        `group flex items-center gap-2.5 rounded-lg px-2.5 py-2 text-sm transition-colors ${
          isActive
            ? 'bg-brand/12 font-semibold text-brand-fg'
            : 'text-slate-400 hover:bg-white/[0.04] hover:text-slate-200'
        }`
      }
    >
      <span className="w-4 text-center text-[13px] opacity-80">{GLYPH[label] || '·'}</span>
      <span className="truncate">{label}</span>
    </NavLink>
  )
}

function Sidebar() {
  const { allowedPortals } = useRole()

  return (
    <aside className="flex w-64 shrink-0 flex-col border-r border-line bg-ink-900">
      <div className="flex items-center gap-2.5 px-5 py-4">
        <Logo />
        <div>
          <div className="text-sm font-bold text-slate-100">Healthcare FL</div>
          <div className="text-[11px] text-slate-500">Surveillance &amp; treatment</div>
        </div>
      </div>

      <nav className="flex-1 space-y-5 overflow-y-auto px-3 pb-6">
        {allowedPortals.map((p) => (
          <div key={p.key}>
            <div className="mb-1 px-2.5 text-[11px] font-semibold uppercase tracking-[0.12em] text-slate-600">
              {p.label}
            </div>
            <div className="space-y-0.5">
              {p.nav.map((n) => (
                <NavItem key={n.to} to={n.to} end={n.end} label={n.label} />
              ))}
            </div>
          </div>
        ))}
      </nav>
    </aside>
  )
}

export default function AppLayout() {
  const { pathname } = useLocation()
  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex items-center justify-between border-b border-line bg-ink-900/60 px-6 py-2.5 backdrop-blur">
          <div className="hidden text-xs text-slate-600 sm:block">
            Federated AI-enabled Healthcare Surveillance &amp; Treatment Recommendation System
          </div>
          <DemoIdentityBar />
        </header>
        <main key={pathname} className="min-w-0 flex-1">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
