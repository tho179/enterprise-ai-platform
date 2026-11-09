import { useState } from 'react'
import {
  ArrowRightOutlined,
  CheckSquareOutlined,
  ClockCircleOutlined,
  CustomerServiceOutlined,
  DatabaseOutlined,
  ExclamationCircleOutlined,
  FileTextOutlined,
  MessageOutlined,
} from '@ant-design/icons'
import { useQuery } from '@tanstack/react-query'
import { Button, Input, Skeleton, Tag } from 'antd'
import { Link, useNavigate } from 'react-router-dom'
import { documentsApi } from '@/api/documents'
import { healthApi } from '@/api/health'
import { leaveApi } from '@/api/leave'
import { DEMO_MODE } from '@/lib/constants'
import { notificationsApi } from '@/api/notifications'
import { ticketsApi } from '@/api/tickets'
import { usersApi } from '@/api/users'
import { useAuth } from '@/auth/AuthContext'
import { KpiCard } from '@/components/ui/KpiCard'
import { PageHeader } from '@/components/ui/PageHeader'
import { Panel } from '@/components/ui/Panel'
import { ErrorState } from '@/components/ui/States'
import { StatusTag } from '@/components/ui/Tags'
import { CHAT_SUGGESTIONS } from '@/components/layout/navConfig'
import { DOCUMENT_CATEGORIES, ROLE_LABELS, TICKET_PRIORITY_LABELS } from '@/lib/constants'
import { formatDate, formatDateTime, formatRelative } from '@/lib/dates'
import { formatNumber } from '@/lib/format'
import { usePageTitle } from '@/lib/usePageTitle'
import type { Ticket } from '@/api/types'

const ACTIVE_TICKET_STATUSES: Ticket['status'][] = ['OPEN', 'REOPENED', 'IN_PROGRESS']
const PRIORITY_ORDER: Record<Ticket['priority'], number> = {
  URGENT: 0,
  HIGH: 1,
  MEDIUM: 2,
  LOW: 3,
}

export function DashboardPage() {
  usePageTitle('Tổng quan')
  const { session } = useAuth()
  const navigate = useNavigate()
  const [quickQuestion, setQuickQuestion] = useState('')

  const role = session?.role ?? 'EMPLOYEE'
  const isEmployeeLike = role === 'EMPLOYEE' || role === 'MANAGER'

  const documentsQuery = useQuery({
    queryKey: ['documents'],
    queryFn: () => documentsApi.list({}),
  })
  const leaveQuery = useQuery({
    queryKey: ['leave', 'mine'],
    queryFn: () => leaveApi.list({ mine: true }),
    enabled: DEMO_MODE && isEmployeeLike,
  })
  const balanceQuery = useQuery({
    queryKey: ['leave', 'balance'],
    queryFn: leaveApi.balance,
    enabled: DEMO_MODE && isEmployeeLike,
  })
  const pendingApprovalsQuery = useQuery({
    queryKey: ['leave', 'pending'],
    queryFn: () => leaveApi.list({ status: 'PENDING' }),
    enabled: DEMO_MODE && role === 'MANAGER',
  })
  const myTicketsQuery = useQuery({
    queryKey: ['tickets', 'mine'],
    queryFn: () => ticketsApi.list({ mine: true }),
    enabled: DEMO_MODE && role !== 'ADMIN',
  })
  const queueQuery = useQuery({
    queryKey: ['tickets', 'queue'],
    queryFn: () => ticketsApi.list(),
    enabled: DEMO_MODE && role === 'IT_SUPPORT',
  })
  const usersQuery = useQuery({
    queryKey: ['users'],
    queryFn: usersApi.list,
    enabled: role === 'ADMIN',
  })
  const notificationsQuery = useQuery({
    queryKey: ['notifications'],
    queryFn: notificationsApi.list,
    enabled: DEMO_MODE,
  })
  const healthQuery = useQuery({
    queryKey: ['health'],
    queryFn: healthApi.get,
  })

  const documents = documentsQuery.data?.items ?? []
  const ingested = documents.filter(
    (document) => document.currentVersion.status === 'INGESTED',
  ).length
  const failed = documents.filter(
    (document) => document.currentVersion.status === 'FAILED',
  ).length
  const processing = documents.filter(
    (document) => document.currentVersion.status === 'PROCESSING',
  ).length
  const myLeave = leaveQuery.data ?? []
  const pendingMine = myLeave.filter((item) => item.status === 'PENDING').length
  const myTickets = myTicketsQuery.data ?? []
  const mineOpen = myTickets.filter((item) =>
    ACTIVE_TICKET_STATUSES.includes(item.status),
  ).length
  const pendingApprovals = pendingApprovalsQuery.data ?? []
  const queue = queueQuery.data ?? []
  const queueActive = queue.filter(
    (ticket) => ticket.status === 'OPEN' || ticket.status === 'REOPENED',
  )
  const myAssigned = queue.filter(
    (ticket) =>
      ticket.assigneeId === session?.id && ticket.status === 'IN_PROGRESS',
  ).length
  const resolved = queue.filter((ticket) => ticket.status === 'RESOLVED').length
  const users = usersQuery.data ?? []
  const activeUsers = users.filter((user) => user.active).length
  const health = healthQuery.data

  const categories = DOCUMENT_CATEGORIES.map((category) => ({
    category,
    count: documents.filter((document) => document.category === category).length,
  })).filter((item) => item.count > 0)
  const maxCategory = Math.max(1, ...categories.map((item) => item.count))

  const recentDocuments = [...documents]
    .sort((a, b) => b.updatedAt.localeCompare(a.updatedAt))
    .slice(0, 5)

  const prepareLeaves = pendingApprovals.slice(0, 4)
  const itTasks = [...queueActive]
    .sort((a, b) => PRIORITY_ORDER[a.priority] - PRIORITY_ORDER[b.priority])
    .slice(0, 4)
  const adminTasks = documents
    .filter((document) =>
      ['FAILED', 'PROCESSING'].includes(document.currentVersion.status),
    )
    .slice(0, 4)
  const employeeTasks = [
    ...myLeave
      .filter((item) => item.status === 'PENDING')
      .slice(0, 2)
      .map((item) => ({
        key: `leave-${item.id}`,
        icon: <ClockCircleOutlined />,
        title: `Đơn nghỉ ${formatDate(item.startDate)} – ${formatDate(item.endDate)}`,
        meta: `${item.totalDays} ngày · Chờ duyệt`,
        to: '/leave?tab=mine',
      })),
    ...myTickets
      .filter((item) => ACTIVE_TICKET_STATUSES.includes(item.status))
      .slice(0, 2)
      .map((item) => ({
        key: `ticket-${item.id}`,
        icon: <CustomerServiceOutlined />,
        title: item.title,
        meta: `${item.ticketCode} · ${item.status === 'IN_PROGRESS' ? 'Đang xử lý' : 'Mới'}`,
        to: '/tickets',
      })),
  ]

  const kpis =
    role === 'ADMIN'
      ? [
          {
            label: 'Tài liệu đã nạp',
            value: ingested,
            hint: `${documents.length} tài liệu trong kho`,
          },
          {
            label: 'Tài liệu nạp lỗi',
            value: failed,
            hint: 'Cần kiểm tra pipeline',
          },
          {
            label: 'Người dùng hoạt động',
            value: activeUsers,
            hint: `${users.length} tài khoản`,
          },
          {
            label: 'Phiên bản đang xử lý',
            value: processing,
            hint: 'Pipeline đang chạy',
          },
        ]
      : role === 'MANAGER'
        ? [
            {
              label: 'Đơn chờ duyệt',
              value: pendingApprovals.length,
              hint: 'Cần quản lý xử lý',
            },
            {
              label: 'Ngày phép còn lại',
              value: balanceQuery.data?.remaining ?? '—',
              hint: balanceQuery.data
                ? `Đã dùng ${balanceQuery.data.used}/${balanceQuery.data.total} ngày`
                : 'Đang tải số dư',
            },
            {
              label: 'Ticket đang mở',
              value: mineOpen,
              hint: 'Yêu cầu của tôi',
            },
            {
              label: 'Tài liệu đã nạp',
              value: ingested,
              hint: `${documents.length} tài liệu trong kho`,
            },
          ]
        : role === 'IT_SUPPORT'
          ? [
              {
                label: 'Ticket cần xử lý',
                value: queueActive.length,
                hint: 'Mới hoặc mở lại',
              },
              {
                label: 'Đang xử lý của tôi',
                value: myAssigned,
                hint: 'Được gán cho bạn',
              },
              {
                label: 'Đã xử lý',
                value: resolved,
                hint: 'Chờ đóng ticket',
              },
              {
                label: 'Tài liệu đã nạp',
                value: ingested,
                hint: `${documents.length} tài liệu trong kho`,
              },
            ]
          : [
              {
                label: 'Ngày phép còn lại',
                value: balanceQuery.data?.remaining ?? '—',
                hint: balanceQuery.data
                  ? `Đã dùng ${balanceQuery.data.used}/${balanceQuery.data.total} ngày`
                  : 'Đang tải số dư',
              },
              {
                label: 'Đơn nghỉ chờ duyệt',
                value: pendingMine,
                hint: 'Đơn của tôi',
              },
              {
                label: 'Ticket đang mở',
                value: mineOpen,
                hint: 'Yêu cầu IT của tôi',
              },
              {
                label: 'Tài liệu đã nạp',
                value: ingested,
                hint: `${documents.length} tài liệu trong kho`,
              },
            ]

  const tasks =
    role === 'MANAGER'
      ? prepareLeaves.map((item) => ({
          key: item.id,
          icon: <CheckSquareOutlined />,
          title: `${item.employeeName} · ${formatDate(item.startDate)} – ${formatDate(item.endDate)}`,
          meta: `${item.totalDays} ngày · ${item.reason}`,
          to: '/approvals',
        }))
      : role === 'IT_SUPPORT'
        ? itTasks.map((item) => ({
            key: item.id,
            icon: <CustomerServiceOutlined />,
            title: item.title,
            meta: `${item.ticketCode} · ${TICKET_PRIORITY_LABELS[item.priority]}`,
            to: '/tickets/queue',
          }))
        : role === 'ADMIN'
          ? adminTasks.map((item) => ({
              key: item.id,
              icon:
                item.currentVersion.status === 'FAILED' ? (
                  <ExclamationCircleOutlined />
                ) : (
                  <ClockCircleOutlined />
                ),
              title: item.title,
              meta: `${item.documentCode} · ${
                item.currentVersion.status === 'FAILED' ? 'Nạp lỗi' : 'Đang xử lý'
              }`,
              to: `/documents/${item.id}`,
            }))
          : employeeTasks

  return (
    <div>
      <PageHeader
        eyebrow="Không gian làm việc"
        title={`Chào ${session?.fullName?.split(' ').slice(-1)[0] ?? 'bạn'}`}
        description={`${ROLE_LABELS[role]} · Đây là những việc đang cần bạn xử lý hôm nay.`}
        actions={
          <>
            <Button icon={<MessageOutlined />} onClick={() => navigate('/chat')}>
              Hỏi trợ lý AI
            </Button>
            <Button type="primary" onClick={() => navigate('/search')}>
              Tìm kiếm tri thức
            </Button>
          </>
        }
      />

      {documentsQuery.isError ? (
        <ErrorState
          message="Không tải được dữ liệu tổng quan."
          onRetry={() => documentsQuery.refetch()}
        />
      ) : documentsQuery.isLoading ? (
        <Skeleton active paragraph={{ rows: 8 }} />
      ) : (
        <>
          <div className="kpi-grid">
            {kpis.map((kpi) => (
              <KpiCard
                key={kpi.label}
                label={kpi.label}
                value={kpi.value}
                hint={kpi.hint}
              />
            ))}
          </div>

          <div className="dashboard-grid">
            <div className="stack">
              <Panel
                title="Việc cần xử lý"
                extra={
                  <Link to={role === 'MANAGER' ? '/approvals' : role === 'IT_SUPPORT' ? '/tickets/queue' : role === 'ADMIN' ? '/documents' : '/leave?tab=mine'}>
                    Xem tất cả <ArrowRightOutlined />
                  </Link>
                }
                flush
              >
                {tasks.length > 0 ? (
                  <div className="list">
                    {tasks.map((task) => (
                      <Link key={task.key} to={task.to} className="list-row">
                        <span className="list-row__icon">{task.icon}</span>
                        <span className="list-row__body">
                          <span className="list-row__title">{task.title}</span>
                          <span className="list-row__meta">{task.meta}</span>
                        </span>
                        <ArrowRightOutlined className="list-row__arrow" />
                      </Link>
                    ))}
                  </div>
                ) : (
                  <div className="panel-empty">Không có việc cần xử lý. Bạn đã hoàn tất hàng đợi.</div>
                )}
              </Panel>

              <Panel
                title="Tài liệu cập nhật gần đây"
                extra={
                  <Link to="/documents">
                    Kho tài liệu <ArrowRightOutlined />
                  </Link>
                }
                flush
              >
                {recentDocuments.length > 0 ? (
                  <div className="list">
                    {recentDocuments.map((document) => (
                      <Link
                        key={document.id}
                        to={`/documents/${document.id}`}
                        className="list-row"
                      >
                        <span className="list-row__icon">
                          <FileTextOutlined />
                        </span>
                        <span className="list-row__body">
                          <span className="list-row__title">{document.title}</span>
                          <span className="list-row__meta">
                            {document.documentCode} · {document.category} ·{' '}
                            {formatRelative(document.updatedAt)}
                          </span>
                        </span>
                        <StatusTag status={document.currentVersion.status} />
                      </Link>
                    ))}
                  </div>
                ) : (
                  <div className="panel-empty">Kho tài liệu đang trống.</div>
                )}
              </Panel>
            </div>

            <div className="stack">
              <Panel title="Hỏi nhanh trợ lý AI">
                <p className="muted text-sm" style={{ marginTop: 0 }}>
                  Câu trả lời sẽ kèm trích dẫn tới tài liệu nội bộ.
                </p>
                <Input.TextArea
                  placeholder="Ví dụ: Nhân viên được nghỉ phép bao nhiêu ngày?"
                  autoSize={{ minRows: 2, maxRows: 4 }}
                  value={quickQuestion}
                  onChange={(event) => setQuickQuestion(event.target.value)}
                  aria-label="Câu hỏi nhanh"
                />
                <Button
                  type="primary"
                  block
                  className="mt-8"
                  icon={<MessageOutlined />}
                  disabled={!quickQuestion.trim()}
                  onClick={() =>
                    navigate(`/chat?q=${encodeURIComponent(quickQuestion.trim())}`)
                  }
                >
                  Hỏi trợ lý
                </Button>
                <div className="quick-suggestions">
                  {CHAT_SUGGESTIONS.slice(0, 3).map((suggestion) => (
                    <button
                      key={suggestion.label}
                      type="button"
                      className="quick-suggestion"
                      onClick={() =>
                        navigate(`/chat?q=${encodeURIComponent(suggestion.question)}`)
                      }
                    >
                      {suggestion.label}
                    </button>
                  ))}
                </div>
              </Panel>

              <Panel title="Trạng thái hệ thống" extra={<Tag color={health?.ai === 'healthy' ? 'success' : 'red'}>{health?.ai === 'healthy' ? 'Ổn định' : 'Cần kiểm tra'}</Tag>}>
                <div className="detail-list">
                  <div className="detail-row">
                    <span className="detail-row__label">AI service</span>
                    <span className="detail-row__value">
                      {health?.ai === 'healthy' ? 'Đang phản hồi' : 'Không phản hồi'}
                      {health?.latencyMs !== undefined ? ` · ${health.latencyMs} ms` : ''}
                    </span>
                  </div>
                  <div className="detail-row">
                    <span className="detail-row__label">Vector store</span>
                    <span className="detail-row__value">
                      {health?.qdrantVectors !== undefined
                        ? `${formatNumber(health.qdrantVectors)} vector`
                        : 'Chưa có dữ liệu'}
                    </span>
                  </div>
                  <div className="detail-row">
                    <span className="detail-row__label">Model</span>
                    <span className="detail-row__value mono" title={health?.model}>
                      {health?.model ?? '—'}
                    </span>
                  </div>
                  <div className="detail-row">
                    <span className="detail-row__label">Phiên bản</span>
                    <span className="detail-row__value">EAKWP Console v1.0</span>
                  </div>
                </div>
              </Panel>

              <Panel title="Danh mục tài liệu" extra={<Tag icon={<DatabaseOutlined />}>{documents.length}</Tag>}>
                <div className="bar-list">
                  {categories.map((item) => (
                    <Link
                      key={item.category}
                      to={`/documents?category=${encodeURIComponent(item.category)}`}
                      className="bar-row"
                    >
                      <span className="bar-row__label">{item.category}</span>
                      <span className="bar-row__track">
                        <span
                          className="bar-row__fill"
                          style={{ width: `${(item.count / maxCategory) * 100}%` }}
                        />
                      </span>
                      <span className="bar-row__value">{item.count}</span>
                    </Link>
                  ))}
                </div>
              </Panel>

              <Panel
                title="Thông báo gần đây"
                extra={<span className="muted text-sm">{notificationsQuery.data?.length ?? 0} mục</span>}
                flush
              >
                {notificationsQuery.data && notificationsQuery.data.length > 0 ? (
                  <div className="list">
                    {notificationsQuery.data.slice(0, 4).map((item) => (
                      <Link
                        key={item.id}
                        to={item.href ?? '/dashboard'}
                        className="list-row"
                      >
                        <span className="list-row__icon">
                          {item.read ? <CheckSquareOutlined /> : <ClockCircleOutlined />}
                        </span>
                        <span className="list-row__body">
                          <span className="list-row__title">{item.title}</span>
                          <span className="list-row__meta">
                            {formatDateTime(item.createdAt)} · {formatRelative(item.createdAt)}
                          </span>
                        </span>
                      </Link>
                    ))}
                  </div>
                ) : (
                  <div className="panel-empty">Không có thông báo.</div>
                )}
              </Panel>
            </div>
          </div>
        </>
      )}
    </div>
  )
}
