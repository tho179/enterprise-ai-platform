import { api } from '@/api/client'
import { normalizeError } from '@/api/errors'
import type { Role, User } from '@/api/types'
import { DEMO_MODE } from '@/lib/constants'
import { demoUsers } from '@/mocks/fixtures'

let fallbackUsers: User[] = [...demoUsers]

function backendUnavailable(error: unknown): boolean {
  return DEMO_MODE && normalizeError(error).status === 0
}

interface CreateUserInput {
  fullName: string
  email: string
  password: string
  role: Role
}

export const usersApi = {
  async list(): Promise<User[]> {
    try {
      const { data } = await api.get<User[] | { content?: User[] }>('/api/users')
      const items: User[] = Array.isArray(data)
        ? data
        : Array.isArray(data?.content)
        ? data.content
        : []
      return items.map((user) => ({ ...user, active: user.active ?? true }))
    } catch (error) {
      if (backendUnavailable(error)) return fallbackUsers
      throw normalizeError(error)
    }
  },

  async create(input: CreateUserInput): Promise<User> {
    try {
      const { data } = await api.post<User>('/api/users', input)
      return { ...data, active: data.active ?? true }
    } catch (error) {
      if (backendUnavailable(error)) {
        const created: User = {
          id: `u-local-${Date.now()}`,
          fullName: input.fullName,
          email: input.email,
          role: input.role,
          active: true,
          createdAt: new Date().toISOString(),
        }
        fallbackUsers = [created, ...fallbackUsers]
        return created
      }
      throw normalizeError(error)
    }
  },

  async updateRole(id: string, role: Role): Promise<User> {
    try {
      const { data } = await api.patch<User>(`/api/users/${id}/role`, { role })
      return data
    } catch (error) {
      if (backendUnavailable(error)) {
        fallbackUsers = fallbackUsers.map((item) => (item.id === id ? { ...item, role } : item))
        const found = fallbackUsers.find((item) => item.id === id)
        if (found) return found
      }
      throw normalizeError(error)
    }
  },

  async setActive(id: string, active: boolean): Promise<User> {
    try {
      const { data } = await api.patch<User>(`/api/users/${id}/status`, { active })
      return data
    } catch (error) {
      if (backendUnavailable(error)) {
        fallbackUsers = fallbackUsers.map((item) => (item.id === id ? { ...item, active } : item))
        const found = fallbackUsers.find((item) => item.id === id)
        if (found) return found
      }
      throw normalizeError(error)
    }
  },
}
