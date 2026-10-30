import { Button, Result } from 'antd'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '@/auth/AuthContext'
import { defaultRouteForRole } from '@/lib/constants'
import { usePageTitle } from '@/lib/usePageTitle'

export function ForbiddenPage() {
  usePageTitle('Không có quyền truy cập')
  const navigate = useNavigate()
  const { session } = useAuth()

  return (
    <Result
      status="403"
      title="Không có quyền truy cập"
      subTitle="Vai trò hiện tại của bạn không được phép mở trang này. Liên hệ quản trị viên nếu cần thay đổi quyền."
      extra={
        <Button
          type="primary"
          onClick={() => navigate(defaultRouteForRole(session?.role))}
        >
          Về trang mặc định
        </Button>
      }
    />
  )
}
