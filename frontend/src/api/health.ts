import { api } from '@/api/client'
import type { HealthSnapshot } from '@/api/types'
import { DEMO_MODE } from '@/lib/constants'
import { demoHealth } from '@/mocks/fixtures'

interface AiHealthResponse {
  status?: string
  total_points?: number
  embedding_model?: string
}

export const healthApi = {
  async get(): Promise<HealthSnapshot> {
    const started = performance.now()
    try {
      const { data } = await api.get<AiHealthResponse>('/api/ai/health')
      return {
        ai: data.status === 'healthy' ? 'healthy' : 'down',
        qdrantVectors: data.total_points,
        model: data.embedding_model,
        latencyMs: Math.round(performance.now() - started),
      }
    } catch {
      if (DEMO_MODE) return demoHealth
      return { ai: 'down' }
    }
  },
}
