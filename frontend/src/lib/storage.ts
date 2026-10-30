import type { AuthSession } from '@/api/types'
import { ROLES } from '@/api/types'

const AUTH_KEY = 'eakwp.auth'
const CHAT_PREFIX = 'eakwp.chat.'

function isRole(value: unknown): value is AuthSession['role'] {
  return typeof value === 'string' && (ROLES as readonly string[]).includes(value)
}

export function readAuthSession(): AuthSession | null {
  try {
    const raw = localStorage.getItem(AUTH_KEY)
    if (!raw) return null
    const parsed = JSON.parse(raw) as Partial<AuthSession>
    if (
      typeof parsed.id !== 'string' ||
      typeof parsed.fullName !== 'string' ||
      typeof parsed.email !== 'string' ||
      typeof parsed.accessToken !== 'string' ||
      !isRole(parsed.role)
    ) {
      return null
    }
    return parsed as AuthSession
  } catch {
    return null
  }
}

export function writeAuthSession(session: AuthSession): void {
  localStorage.setItem(AUTH_KEY, JSON.stringify(session))
}

export function clearAuthSession(): void {
  localStorage.removeItem(AUTH_KEY)
}

export function readChatStorage<T>(userId: string): T | null {
  try {
    const raw = localStorage.getItem(`${CHAT_PREFIX}${userId}`)
    return raw ? (JSON.parse(raw) as T) : null
  } catch {
    return null
  }
}

export function writeChatStorage<T>(userId: string, value: T): void {
  localStorage.setItem(`${CHAT_PREFIX}${userId}`, JSON.stringify(value))
}
