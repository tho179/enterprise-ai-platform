import { describe, expect, it } from 'vitest'
import type { AuthSession } from '@/api/types'
import {
  clearAuthSession,
  readAuthSession,
  readChatStorage,
  writeAuthSession,
  writeChatStorage,
} from '@/lib/storage'

const session: AuthSession = {
  id: 'u-1',
  fullName: 'Nguyễn Văn An',
  email: 'nva@congty.vn',
  role: 'EMPLOYEE',
  accessToken: 'mock-token-u-1',
}

describe('storage', () => {
  it('round-trips a valid session', () => {
    writeAuthSession(session)
    expect(readAuthSession()).toEqual(session)
  })

  it('rejects malformed or invalid sessions', () => {
    localStorage.setItem('eakwp.auth', '{bad json')
    expect(readAuthSession()).toBeNull()

    localStorage.setItem('eakwp.auth', JSON.stringify({ ...session, role: 'SUPERUSER' }))
    expect(readAuthSession()).toBeNull()
  })

  it('clears the session', () => {
    writeAuthSession(session)
    clearAuthSession()
    expect(readAuthSession()).toBeNull()
  })

  it('stores chat history per user', () => {
    writeChatStorage('u-1', [{ id: 'chat-1' }])
    writeChatStorage('u-2', [])
    expect(readChatStorage<{ id: string }[]>('u-1')).toEqual([{ id: 'chat-1' }])
    expect(readChatStorage('u-2')).toEqual([])
    expect(readChatStorage('u-3')).toBeNull()
  })
})
