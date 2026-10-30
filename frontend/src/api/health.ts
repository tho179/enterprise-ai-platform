import { aiApi } from '@/api/client'
import type { HealthSnapshot } from '@/api/types'
import { DEMO_MODE } from '@/lib/constants'
import { demoHealth } from '@/mocks/fixtures'

interface StatsResponse {
  total_points?: number
  embedding_model?: string
}

export const healthApi = {
  async get(): Promise<HealthSnapshot> {
    const started = performance.now()
    try {
      const [health, stats] = await Promise.all([
        aiApi.get<{ status?: string }>('/health'),
        aiApi.get<StatsResponse>('/api/v1/search/stats'),
      ])
      return {
        ai: health.data.status === 'healthy' ? 'healthy' : 'down',
        qdrantVectors: stats.data.total_points,
        model: stats.data.embedding_model,
        latencyMs: Math.round(performance.now() - started),
      }
    } catch {
      if (DEMO_MODE) return demoHealth
      return { ai: 'down' }
    }
  },
}
