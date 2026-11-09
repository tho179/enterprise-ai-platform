import { Result } from 'antd'
import type { ReactNode } from 'react'
import { DEMO_MODE } from '@/lib/constants'

/** Guards screens that only have browser mock data behind them. */
export function DemoOnly({ children }: { children: ReactNode }) {
  if (DEMO_MODE) return <>{children}</>
  return (
    <Result
      status="info"
      title="Mô-đun đang ở giai đoạn thiết kế"
      subTitle="Chức năng này mới có giao diện mẫu, chưa có API thật. Chạy VITE_USE_MOCKS=true để xem bản minh họa."
    />
  )
}
