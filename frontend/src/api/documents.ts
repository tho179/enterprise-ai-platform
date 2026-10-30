import { api } from '@/api/client'
import type {
  DocumentChunk,
  DocumentDetail,
  DocumentListParams,
  DocumentSummary,
  DocumentVersion,
  IngestionStatus,
  UploadTicket,
} from '@/api/types'

interface DocumentListResponse {
  items: DocumentSummary[]
  total: number
}

type RawList = DocumentListResponse | DocumentSummary[] | { content?: DocumentSummary[]; totalElements?: number }

function normalizeList(data: RawList): DocumentListResponse {
  if (Array.isArray(data)) return { items: data, total: data.length }
  if ('items' in data && Array.isArray(data.items)) return data
  if ('content' in data && Array.isArray(data.content)) {
    return { items: data.content, total: data.totalElements ?? data.content.length }
  }
  return { items: [], total: 0 }
}

export const documentsApi = {
  async list(params: DocumentListParams): Promise<DocumentListResponse> {
    const { data } = await api.get<RawList>('/api/documents', { params })
    return normalizeList(data)
  },

  async get(id: string): Promise<DocumentDetail> {
    const { data } = await api.get<DocumentDetail>(`/api/documents/${id}`)
    return data
  },

  async versions(id: string): Promise<DocumentVersion[]> {
    const { data } = await api.get<DocumentVersion[]>(`/api/documents/${id}/versions`)
    return data
  },

  async chunks(id: string, q?: string): Promise<DocumentChunk[]> {
    const { data } = await api.get<DocumentChunk[]>(`/api/documents/${id}/chunks`, {
      params: q ? { q } : undefined,
    })
    return data
  },

  async upload(formData: FormData): Promise<UploadTicket> {
    const { data } = await api.post<UploadTicket>('/api/documents/upload', formData)
    return data
  },

  async uploadVersion(id: string, formData: FormData): Promise<UploadTicket> {
    const { data } = await api.post<UploadTicket>(`/api/documents/${id}/versions`, formData)
    return data
  },

  async ingestionStatus(taskId: string): Promise<IngestionStatus> {
    const { data } = await api.get<IngestionStatus>(`/api/ai/status/${taskId}`)
    return data
  },

  async retry(versionId: string): Promise<UploadTicket> {
    const { data } = await api.post<UploadTicket>(`/api/documents/versions/${versionId}/retry`)
    return data
  },

  async setCurrent(versionId: string): Promise<DocumentVersion> {
    const { data } = await api.patch<DocumentVersion>(
      `/api/documents/versions/${versionId}/current`,
    )
    return data
  },

  async delete(ids: string[]): Promise<number> {
    const { data } = await api.delete<{ deleted: number }>('/api/documents', {
      data: ids,
    })
    return data.deleted
  },

  /**
   * Ảnh trang PDF chứa đoạn trích (đã tô vàng vùng dẫn chứng) dưới dạng object URL.
   * Người gọi chịu trách nhiệm revoke URL khi không còn dùng.
   */
  async chunkPreviewUrl(id: string, chunkId: string): Promise<string> {
    const { data } = await api.get(`/api/documents/${id}/chunks/${chunkId}/preview`, {
      responseType: 'blob',
    })
    return URL.createObjectURL(data as Blob)
  },

  /** File PDF gốc (phiên bản hiện hành) dưới dạng object URL. */
  async fileUrl(id: string): Promise<string> {
    const { data } = await api.get(`/api/documents/${id}/file`, {
      responseType: 'blob',
    })
    return URL.createObjectURL(data as Blob)
  },
}
