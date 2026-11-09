import { AI_TIMEOUT_MS, api } from '@/api/client'
import { normalizeError } from '@/api/errors'
import type { SearchResponse } from '@/api/types'
import { DEMO_MODE } from '@/lib/constants'

interface SearchInput {
  query: string
  topK?: number
  minScore?: number
  documentId?: string
}

export const searchApi = {
  async search(input: SearchInput): Promise<SearchResponse> {
    try {
      const { data } = await api.post<SearchResponse>(
        '/api/ai/search',
        {
          query: input.query,
          top_k: input.topK ?? 10,
          min_score: input.minScore ?? 0.3,
          document_id: input.documentId || undefined,
        },
        { timeout: AI_TIMEOUT_MS },
      )
      return data
    } catch (error) {
      const normalized = normalizeError(error)
      if (
        DEMO_MODE &&
        (normalized.status === 0 ||
          normalized.status === 404 ||
          normalized.status >= 500)
      ) {
        const { mockSearchResponse } = await import('@/mocks/chat-fallback')
        return mockSearchResponse(
          input.query,
          input.topK ?? 10,
          input.minScore ?? 0.3,
          input.documentId,
        )
      }
      throw normalized
    }
  },
}
