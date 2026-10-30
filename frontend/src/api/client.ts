import axios from 'axios'
import { normalizeError } from '@/api/errors'
import { clearAuthSession, readAuthSession } from '@/lib/storage'
import { AI_BASE, DEMO_MODE } from '@/lib/constants'

export const api = axios.create({
  baseURL: (import.meta.env.VITE_API_BASE_URL as string | undefined) || '',
  timeout: 20_000,
})

export const aiApi = axios.create({
  baseURL: AI_BASE,
  timeout: 60_000,
})

api.interceptors.request.use((config) => {
  const session = readAuthSession()
  if (session?.accessToken) {
    config.headers.Authorization = `Bearer ${session.accessToken}`
    config.headers['X-Demo-User'] = session.id
  }
  return config
})

api.interceptors.response.use(
  (response) => response,
  (error: unknown) => {
    const normalized = normalizeError(error)
    const isLogin = axios.isAxiosError(error) && error.config?.url?.includes('/auth/login')
    const session = readAuthSession()
    const isDemoSession = DEMO_MODE && session?.accessToken.startsWith('mock-token-')
    if (normalized.status === 401 && !isLogin && !isDemoSession) {
      clearAuthSession()
      window.dispatchEvent(new Event('eakwp:unauthorized'))
    }
    return Promise.reject(normalized)
  },
)
