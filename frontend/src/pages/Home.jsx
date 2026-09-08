import { Link } from 'react-router-dom'
import { useRole, ROLES } from '../app/auth/RoleContext'
import { PageHeader, Card, InfoNote } from '../components/common/ui'

export default function Home() {
  const { role, allowedPortals } = useRole()
  return (
    <div className="mx-auto max-w-4xl px-4 py-8">
      <PageHeader
        title="Healthcare FL — Application"
        subtitle={`Signed in (demo) as: ${ROLES[role]}`}
      />
      <div className="grid gap-4 sm:grid-cols-2">
        {allowedPortals.map((p) => (
          <Link key={p.key} to={p.base}>
            <Card title={p.label} className="transition hover:border-brand/30">
              <ul className="text-sm text-slate-400">
                {p.nav.map((n) => (
                  <li key={n.to}>· {n.label}</li>
                ))}
              </ul>
            </Card>
          </Link>
        ))}
      </div>
      <div className="mt-4">
        <InfoNote tone="amber">
          No backend runs on this branch, so every screen shows clearly-labelled sample data. RBAC is
          enforced server-side in production; here the top-bar role switcher stands in for auth.
        </InfoNote>
      </div>
    </div>
  )
}
