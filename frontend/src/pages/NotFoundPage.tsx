import { Button, Result } from 'antd'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '@/auth/AuthContext'
import { defaultRouteForRole } from '@/lib/constants'
import { usePageTitle } from '@/lib/usePageTitle'

export function NotFoundPage() {
  usePageTitle('Không tìm thấy trang')
  const navigate = useNavigate()
  const { session } = useAuth()

  return (
    <Result
      status="404"
      title="Không tìm thấy trang"
      subTitle="Đường dẫn không tồn tại hoặc đã được di chuyển."
      extra={
        <Button
          type="primary"
          onClick={() =>
            navigate(session ? defaultRouteForRole(session.role) : '/login')
          }
        >
          Về trang chủ
        </Button>
      }
    />
  )
}
