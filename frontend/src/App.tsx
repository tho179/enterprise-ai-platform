import { BrowserRouter } from 'react-router-dom'
import { AppProviders } from '@/app/providers'
import { AppRoutes } from '@/app/router'
import { AuthProvider } from '@/auth/AuthContext'

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <AppProviders>
          <AppRoutes />
        </AppProviders>
      </AuthProvider>
    </BrowserRouter>
  )
}
