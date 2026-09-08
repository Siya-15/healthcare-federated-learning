import { useRole, PORTALS } from '../auth/RoleContext'

// Client-side portal guard. This is navigation hygiene only - the backend is
// the authority on access (spec section 16). Renders an explicit "access
// denied" state (mirrors HTTP 403) rather than silently hiding routes.
export default function RoleGuard({ portalKey, children }) {
  const { role, can } = useRole()
  if (can(portalKey)) return children

  const portal = PORTALS.find((p) => p.key === portalKey)
  return (
    <div className="mx-auto max-w-2xl px-4 py-16 text-center">
      <div className="rounded-xl border border-red-200 bg-red-50 p-6">
        <h2 className="text-lg font-semibold text-red-800">Access denied</h2>
        <p className="mt-2 text-sm text-red-700">
          Your current role (<span className="font-mono">{role}</span>) cannot open the{' '}
          <span className="font-semibold">{portal?.label || portalKey}</span>. The backend enforces
          this; the menu is filtered to match.
        </p>
        <p className="mt-2 text-xs text-red-600">
          Switch the demo role from the top bar to explore other portals.
        </p>
      </div>
    </div>
  )
}
