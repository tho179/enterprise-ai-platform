import { api } from '@/api/client'
import type { LeaveRequest, LeaveStatus } from '@/api/types'

export interface LeaveBalance {
  total: number
  used: number
  remaining: number
}

interface ListParams {
  mine?: boolean
  status?: LeaveStatus
}

interface CreateLeaveInput {
  startDate: string
  endDate: string
  totalDays: number
  reason: string
}

export const leaveApi = {
  async list(params: ListParams = {}): Promise<LeaveRequest[]> {
    const { data } = await api.get<LeaveRequest[]>('/api/leave-requests', { params })
    return data
  },

  async balance(): Promise<LeaveBalance> {
    const { data } = await api.get<LeaveBalance>('/api/leave-requests/balance')
    return data
  },

  async create(input: CreateLeaveInput): Promise<LeaveRequest> {
    const { data } = await api.post<LeaveRequest>('/api/leave-requests', input)
    return data
  },

  async approve(id: string, comment: string): Promise<LeaveRequest> {
    const { data } = await api.patch<LeaveRequest>(`/api/leave-requests/${id}/approve`, { comment })
    return data
  },

  async reject(id: string, comment: string): Promise<LeaveRequest> {
    const { data } = await api.patch<LeaveRequest>(`/api/leave-requests/${id}/reject`, { comment })
    return data
  },

  async cancel(id: string): Promise<LeaveRequest> {
    const { data } = await api.patch<LeaveRequest>(`/api/leave-requests/${id}/cancel`)
    return data
  },
}
