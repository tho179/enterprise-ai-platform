import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'
import type { ReactNode } from 'react'
import { authApi } from '@/api/auth'
import type { AuthSession } from '@/api/types'
import { clearAuthSession, readAuthSession, writeAuthSession } from '@/lib/storage'

interface AuthContextValue {
  session: AuthSession | null
  isAuthenticated: boolean
  login: (email: string, password: string) => Promise<AuthSession>
  logout: () => void
}

const AuthContext = createContext<AuthContextValue | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [session, setSession] = useState<AuthSession | null>(() => readAuthSession())

  const login = useCallback(async (email: string, password: string) => {
    const next = await authApi.login({ email, password })
    writeAuthSession(next)
    setSession(next)
    return next
  }, [])

  const logout = useCallback(() => {
    clearAuthSession()
    setSession(null)
  }, [])

  useEffect(() => {
    const onUnauthorized = () => setSession(null)
    window.addEventListener('eakwp:unauthorized', onUnauthorized)
    return () => window.removeEventListener('eakwp:unauthorized', onUnauthorized)
  }, [])

  const value = useMemo<AuthContextValue>(
    () => ({ session, isAuthenticated: session !== null, login, logout }),
    [session, login, logout],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext)
  if (!context) throw new Error('useAuth must be used inside AuthProvider')
  return context
}
