import { api } from '@/api/client'
import type { AppNotification } from '@/api/types'

export const notificationsApi = {
  async list(): Promise<AppNotification[]> {
    try {
      const { data } = await api.get<AppNotification[]>('/api/notifications')
      return Array.isArray(data) ? data : []
    } catch {
      return []
    }
  },

  async markRead(id: string): Promise<void> {
    try {
      await api.patch(`/api/notifications/${id}/read`)
    } catch {
      // Ignored if backend notification endpoint is not yet implemented
    }
  },

  async markAllRead(): Promise<void> {
    try {
      await api.patch('/api/notifications/read-all')
    } catch {
      // Ignored if backend notification endpoint is not yet implemented
    }
  },
}
