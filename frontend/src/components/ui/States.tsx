import type { ReactNode } from 'react'
import { Button, Empty } from 'antd'
import { ReloadOutlined } from '@ant-design/icons'

export function EmptyState({
  title = 'Chưa có dữ liệu',
  description,
  action,
}: {
  title?: string
  description?: ReactNode
  action?: ReactNode
}) {
  return (
    <div className="empty-state">
      <Empty
        image={Empty.PRESENTED_IMAGE_SIMPLE}
        description={
          <div>
            <div style={{ color: 'var(--text-2)', fontWeight: 500 }}>{title}</div>
            {description ? <div className="muted text-sm mt-8">{description}</div> : null}
          </div>
        }
      >
        {action}
      </Empty>
    </div>
  )
}

export function ErrorState({
  message = 'Không tải được dữ liệu.',
  onRetry,
}: {
  message?: string
  onRetry?: () => void
}) {
  return (
    <div className="error-state">
      <Empty
        image={Empty.PRESENTED_IMAGE_SIMPLE}
        description={
          <div>
            <div style={{ color: 'var(--text-2)', fontWeight: 500 }}>{message}</div>
            <div className="muted text-sm mt-8">
              Kiểm tra kết nối backend hoặc thử lại sau.
            </div>
          </div>
        }
      >
        {onRetry ? (
          <Button icon={<ReloadOutlined />} onClick={onRetry}>
            Thử lại
          </Button>
        ) : null}
      </Empty>
    </div>
  )
}
