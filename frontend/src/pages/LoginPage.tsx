import { useEffect, useState } from 'react'
import {
  ArrowRightOutlined,
  CheckCircleFilled,
  LockOutlined,
  MailOutlined,
} from '@ant-design/icons'
import { Alert, Button, Form, Input, Tag, Typography } from 'antd'
import { useLocation, useNavigate } from 'react-router-dom'
import { loginErrorMessage, normalizeError } from '@/api/errors'
import { useAuth } from '@/auth/AuthContext'
import { DEMO_MODE, ROLE_LABELS, defaultRouteForRole } from '@/lib/constants'
import { usePageTitle } from '@/lib/usePageTitle'
import { demoAccounts, demoUsers } from '@/mocks/fixtures'

interface LoginFormValues {
  email: string
  password: string
}

const DEMO_PASSWORD = 'Demo@123'

export function LoginPage() {
  usePageTitle('Đăng nhập')
  const [form] = Form.useForm<LoginFormValues>()
  const { session, login } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)

  const from = (location.state as { from?: string } | null)?.from

  useEffect(() => {
    if (session) {
      navigate(from && from !== '/login' ? from : defaultRouteForRole(session.role), {
        replace: true,
      })
    }
  }, [session, from, navigate])

  const handleSubmit = async (values: LoginFormValues) => {
    setSubmitting(true)
    setError(null)
    try {
      const next = await login(values.email, values.password)
      navigate(from && from !== '/login' ? from : defaultRouteForRole(next.role), {
        replace: true,
      })
    } catch (caught) {
      setError(loginErrorMessage(normalizeError(caught)))
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="login-page">
      <section className="login-brand">
        <div>
          <div className="login-brand__mark">
            <div className="login-brand__logo">E</div>
            <div>
              <div className="login-brand__name">EAKWP Console</div>
              <div style={{ color: '#7c8ea1', fontSize: 11 }}>
                Enterprise AI Knowledge Workspace
              </div>
            </div>
          </div>

          <div style={{ marginTop: 56 }}>
            <p className="login-brand__kicker">Tri thức có căn cứ</p>
            <h1 className="login-brand__title">
              Mọi câu trả lời nội bộ đều có nguồn để đối chiếu.
            </h1>
            <p className="login-brand__desc">
              Hỏi đáp tài liệu bằng tiếng Việt, tra cứu theo ngữ nghĩa và xử lý quy
              trình nghiệp vụ trên một giao diện vận hành thống nhất.
            </p>

            <ul className="login-brand__points">
              <li className="login-brand__point">
                <CheckCircleFilled />
                <span>
                  Trích dẫn tới đúng mục, trang và đoạn văn trong tài liệu gốc.
                </span>
              </li>
              <li className="login-brand__point">
                <CheckCircleFilled />
                <span>Pipeline nạp tài liệu PDF có kiểm soát phiên bản.</span>
              </li>
              <li className="login-brand__point">
                <CheckCircleFilled />
                <span>Phân quyền theo vai trò và nhật ký trạng thái rõ ràng.</span>
              </li>
            </ul>
          </div>
        </div>
        <div className="login-brand__foot">
          EAKWP Console v1.0 · Đồ án tốt nghiệp · Dữ liệu hiển thị mang tính minh họa
        </div>
      </section>

      <section className="login-form-wrap">
        <div className="login-card">
          <h2 className="login-card__title">Đăng nhập</h2>
          <p className="login-card__desc">
            Sử dụng tài khoản doanh nghiệp để truy cập không gian làm việc.
          </p>

          {error ? (
            <Alert
              type="error"
              showIcon
              title={error}
              style={{ marginBottom: 16 }}
              closable
              onClose={() => setError(null)}
            />
          ) : null}

          <Form
            form={form}
            layout="vertical"
            requiredMark={false}
            onFinish={handleSubmit}
            initialValues={{ email: '', password: '' }}
          >
            <Form.Item
              label="Email"
              name="email"
              rules={[
                { required: true, message: 'Vui lòng nhập email.' },
                { type: 'email', message: 'Email không hợp lệ.' },
              ]}
            >
              <Input
                size="large"
                prefix={<MailOutlined />}
                placeholder="ten.ban@congty.vn"
                autoComplete="username"
                aria-label="Email"
              />
            </Form.Item>
            <Form.Item
              label="Mật khẩu"
              name="password"
              rules={[
                { required: true, message: 'Vui lòng nhập mật khẩu.' },
                { min: 6, message: 'Mật khẩu tối thiểu 6 ký tự.' },
              ]}
            >
              <Input.Password
                size="large"
                prefix={<LockOutlined />}
                placeholder="Nhập mật khẩu"
                autoComplete="current-password"
                aria-label="Mật khẩu"
              />
            </Form.Item>
            <Button
              type="primary"
              htmlType="submit"
              size="large"
              block
              loading={submitting}
              icon={<ArrowRightOutlined />}
              iconPlacement="end"
            >
              Đăng nhập
            </Button>
          </Form>

          {DEMO_MODE ? (
            <div className="login-card__demo">
              <div className="row" style={{ justifyContent: 'space-between' }}>
                <strong style={{ color: 'var(--text-2)', fontSize: 12 }}>
                  Tài khoản demo
                </strong>
                <Tag color="gold" style={{ margin: 0 }}>
                  Mật khẩu: {DEMO_PASSWORD}
                </Tag>
              </div>
              <div className="demo-account-list">
                {demoAccounts.map((account) => {
                  const user = demoUsers.find((item) => item.id === account.userId)
                  if (!user) return null
                  return (
                    <button
                      key={account.email}
                      type="button"
                      className="demo-account"
                      onClick={() => {
                        form.setFieldsValue({
                          email: account.email,
                          password: DEMO_PASSWORD,
                        })
                        setError(null)
                      }}
                    >
                      <span>
                        <span className="demo-account__email">{account.email}</span>
                        <span className="demo-account__name">{user.fullName}</span>
                      </span>
                      <Tag style={{ margin: 0 }}>{ROLE_LABELS[user.role]}</Tag>
                    </button>
                  )
                })}
              </div>
            </div>
          ) : null}

          <Typography.Paragraph className="login-card__meta">
            Bằng việc đăng nhập, bạn đồng ý tuân thủ chính sách an toàn thông tin và
            quy định sử dụng dữ liệu nội bộ của công ty.
          </Typography.Paragraph>
        </div>
      </section>
    </div>
  )
}
