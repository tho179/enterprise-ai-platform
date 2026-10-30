import { api } from '@/api/client'
import type {
  Classification,
  Ticket,
  TicketCategory,
  TicketPriority,
  TicketSuggestion,
} from '@/api/types'

interface ListParams {
  mine?: boolean
  status?: string
  priority?: string
  q?: string
}

interface CreateTicketInput {
  title: string
  description: string
  category: TicketCategory
  priority: TicketPriority
  attachmentName?: string | null
  aiConfidence?: number | null
}

export const ticketsApi = {
  async list(params: ListParams = {}): Promise<Ticket[]> {
    const { data } = await api.get<Ticket[]>('/api/it-requests', { params })
    return data
  },

  async classify(title: string, description: string): Promise<Classification> {
    const { data } = await api.post<Classification>('/api/it-requests/classify-preview', {
      title,
      description,
    })
    return data
  },

  async create(input: CreateTicketInput): Promise<Ticket> {
    const { data } = await api.post<Ticket>('/api/it-requests', input)
    return data
  },

  async assign(id: string): Promise<Ticket> {
    const { data } = await api.patch<Ticket>(`/api/it-requests/${id}/assign`)
    return data
  },

  async suggestions(id: string): Promise<TicketSuggestion> {
    const { data } = await api.get<TicketSuggestion>(`/api/it-requests/${id}/suggestions`)
    return data
  },

  async resolve(id: string, resolutionNote: string): Promise<Ticket> {
    const { data } = await api.patch<Ticket>(`/api/it-requests/${id}/resolve`, {
      resolutionNote,
    })
    return data
  },

  async close(id: string): Promise<Ticket> {
    const { data } = await api.patch<Ticket>(`/api/it-requests/${id}/close`)
    return data
  },

  async reopen(id: string): Promise<Ticket> {
    const { data } = await api.patch<Ticket>(`/api/it-requests/${id}/reopen`)
    return data
  },
}
