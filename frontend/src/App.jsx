import { RoleProvider } from './app/auth/RoleContext'
import AppRouter from './app/router'

export default function App() {
  return (
    <RoleProvider>
      <AppRouter />
    </RoleProvider>
  )
}
