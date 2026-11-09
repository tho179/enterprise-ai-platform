import { AI_TIMEOUT_MS, api } from '@/api/client'
import { normalizeError } from '@/api/errors'
import type { AskResponse, ChatTurn } from '@/api/types'
import { DEMO_MODE } from '@/lib/constants'

interface AskInput {
  question: string
  history?: ChatTurn[]
}

export const chatApi = {
  async ask(input: AskInput): Promise<AskResponse> {
    try {
      const { data } = await api.post<AskResponse>(
        '/api/ai/chat',
        {
          query: input.question,
          top_k: 3,
          min_score: 0.25,
          history: input.history?.slice(-4) ?? [],
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
        const { mockChatAnswer } = await import('@/mocks/chat-fallback')
        return mockChatAnswer(input.question)
      }
      throw normalized
    }
  },
}
