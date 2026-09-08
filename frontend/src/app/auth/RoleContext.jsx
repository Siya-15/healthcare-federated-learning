import { createContext, useContext, useEffect, useMemo, useState } from 'react'
import { setDemoIdentity } from '../../services/api'

// RBAC is enforced server-side (spec section 16). This context only drives which
// portals are shown and sends the chosen role/hospital to the backend as
// headers. There is no real auth backend on this branch, so the role is a
// "demo identity" the user can switch.

export const ROLES = {
  DOCTOR: 'Doctor / Clinician',
  HOSPITAL_ADMIN: 'Hospital Administrator',
  PUBLIC_HEALTH_ADMIN: 'Central / Public-health Admin',
  TECH_REVIEWER: 'Technical Reviewer / Admin',
}

// Portal -> which roles may open it (mirrors spec sections 2 & 3).
export const PORTALS = [
  {
    key: 'doctor',
    label: 'Doctor Portal',
    base: '/doctor',
    roles: ['DOCTOR'],
    nav: [
      { to: '/doctor', label: 'Dashboard', end: true },
      { to: '/doctor/new-encounter', label: 'New Encounter' },
      { to: '/doctor/advisor', label: 'Treatment Advisor' },
      { to: '/doctor/history', label: 'History' },
    ],
  },
  {
    key: 'surveillance',
    label: 'Surveillance Portal',
    base: '/surveillance',
    roles: ['HOSPITAL_ADMIN', 'PUBLIC_HEALTH_ADMIN', 'TECH_REVIEWER'],
    nav: [
      { to: '/surveillance', label: 'Overview', end: true },
      { to: '/surveillance/alerts', label: 'Alerts' },
      { to: '/surveillance/emerging', label: 'Emerging Symptoms' },
      { to: '/surveillance/trends', label: 'Trends' },
    ],
  },
  {
    key: 'federated',
    label: 'Federated & Privacy',
    base: '/federated',
    roles: ['HOSPITAL_ADMIN', 'PUBLIC_HEALTH_ADMIN', 'TECH_REVIEWER'],
    nav: [
      { to: '/federated', label: 'Federated Overview', end: true },
      { to: '/federated/hospitals', label: 'Hospital Participation' },
      { to: '/federated/rounds', label: 'Rounds' },
      { to: '/federated/data-flow', label: 'Data Flow' },
      { to: '/federated/privacy/controls', label: 'Privacy Controls' },
      { to: '/federated/privacy/audit', label: 'Privacy Audit' },
      { to: '/federated/privacy/minimization', label: 'Data Minimization' },
    ],
  },
  {
    key: 'ai',
    label: 'AI Operations',
    base: '/ai',
    roles: ['TECH_REVIEWER', 'PUBLIC_HEALTH_ADMIN'],
    nav: [
      { to: '/ai', label: 'Model Overview', end: true },
      { to: '/ai/metrics', label: 'Metrics' },
      { to: '/ai/versions', label: 'Versions' },
      { to: '/ai/explanations', label: 'SHAP Explanations' },
    ],
  },
]

const RoleContext = createContext(null)
const LS_KEY = 'hfl.demoIdentity'

function loadIdentity() {
  try {
    const raw = localStorage.getItem(LS_KEY)
    if (raw) return JSON.parse(raw)
  } catch {
    /* ignore */
  }
  return { role: 'DOCTOR', hospitalId: 'H001' }
}

export function RoleProvider({ children }) {
  const [identity, setIdentity] = useState(loadIdentity)

  useEffect(() => {
    setDemoIdentity(identity)
    try {
      localStorage.setItem(LS_KEY, JSON.stringify(identity))
    } catch {
      /* ignore */
    }
  }, [identity])

  const value = useMemo(
    () => ({
      role: identity.role,
      hospitalId: identity.hospitalId,
      setRole: (role) => setIdentity((i) => ({ ...i, role })),
      setHospitalId: (hospitalId) => setIdentity((i) => ({ ...i, hospitalId })),
      portals: PORTALS,
      allowedPortals: PORTALS.filter((p) => p.roles.includes(identity.role)),
      can: (portalKey) => {
        const p = PORTALS.find((x) => x.key === portalKey)
        return Boolean(p && p.roles.includes(identity.role))
      },
    }),
    [identity]
  )

  return <RoleContext.Provider value={value}>{children}</RoleContext.Provider>
}

export function useRole() {
  const ctx = useContext(RoleContext)
  if (!ctx) throw new Error('useRole must be used inside <RoleProvider>')
  return ctx
}
