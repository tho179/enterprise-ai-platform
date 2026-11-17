import { useQuery } from '@tanstack/react-query'
import { healthApi } from '@/api/health'
import { DEMO_MODE } from '@/lib/constants'
import { formatNumber } from '@/lib/format'

export function StatusBar() {
  const healthQuery = useQuery({
    queryKey: ['health'],
    queryFn: healthApi.get,
    refetchInterval: 60_000,
    retry: 0,
  })

  const health = healthQuery.data
  const dotClass = healthQuery.isLoading
    ? ''
    : health?.ai === 'healthy'
      ? 'status-dot--ok'
      : 'status-dot--down'

  return (
    <footer className="status-bar" aria-label="Trạng thái hệ thống">
      <span className="status-bar__item">
        <span className={`status-dot ${dotClass}`} />
        AI service{' '}
        {healthQuery.isLoading
          ? 'đang kiểm tra'
          : health?.ai === 'healthy'
            ? 'ổn định'
            : 'không phản hồi'}
      </span>
      {health?.latencyMs !== undefined ? (
        <span className="status-bar__item">{health.latencyMs} ms</span>
      ) : null}
      {health?.qdrantVectors !== undefined ? (
        <span className="status-bar__item hide-mobile">
          Qdrant {formatNumber(health.qdrantVectors)} vector
        </span>
      ) : null}
      {health?.model ? (
        <span className="status-bar__item status-bar__item--soft hide-tablet" title={health.model}>
          {health.model}
        </span>
      ) : null}
      <span className="status-bar__spacer" />
      <span className="status-bar__item">{DEMO_MODE ? 'Mock mode' : 'Live API'}</span>
      <span className="status-bar__item hide-tablet">v1.0</span>
    </footer>
  )
}
