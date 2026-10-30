import { useEffect, useMemo, useState } from 'react'
import {
  BulbOutlined,
  CheckCircleOutlined,
  ClockCircleOutlined,
  CustomerServiceOutlined,
  ExclamationCircleOutlined,
  FileSearchOutlined,
  ToolOutlined,
} from '@ant-design/icons'
import {
  App as AntApp,
  Button,
  Form,
  Input,
  Modal,
  Select,
  Skeleton,
  Table,
  Tag,
} from 'antd'
import type { TableProps } from 'antd'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useSearchParams } from 'react-router-dom'
import { ticketsApi } from '@/api/tickets'
import type { Citation, Ticket } from '@/api/types'
import { useAuth } from '@/auth/AuthContext'
import { CitationCard, CitationModal } from '@/components/citations/CitationList'
import { KpiCard } from '@/components/ui/KpiCard'
import { PageHeader } from '@/components/ui/PageHeader'
import { Panel } from '@/components/ui/Panel'
import { EmptyState, ErrorState } from '@/components/ui/States'
import { PriorityTag, StatusTag } from '@/components/ui/Tags'
import {
  STATUS_LABELS,
  TICKET_CATEGORY_LABELS,
  TICKET_PRIORITY_LABELS,
} from '@/lib/constants'
import { formatDateTime } from '@/lib/dates'
import { formatPercent } from '@/lib/format'
import { usePageTitle } from '@/lib/usePageTitle'

const PRIORITY_ORDER: Record<Ticket['priority'], number> = {
  URGENT: 0,
  HIGH: 1,
  MEDIUM: 2,
  LOW: 3,
}

const ACTIVE_STATUSES: Ticket['status'][] = ['OPEN', 'REOPENED', 'IN_PROGRESS']
const STATUS_OPTIONS: Ticket['status'][] = [
  'OPEN',
  'IN_PROGRESS',
  'RESOLVED',
  'CLOSED',
  'REOPENED',
]

export function TicketQueuePage() {
  usePageTitle('Hàng đợi IT')
  const { message } = AntApp.useApp()
  const { session } = useAuth()
  const queryClient = useQueryClient()
  const [searchParams, setSearchParams] = useSearchParams()
  const [resolveForm] = Form.useForm<{ note: string }>()
  const [query, setQuery] = useState('')
  const [priorityFilter, setPriorityFilter] = useState('')
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [resolveOpen, setResolveOpen] = useState(false)
  const [selectedCitation, setSelectedCitation] = useState<Citation | null>(null)
  const statusFilter = searchParams.get('status') ?? ''

  const ticketsQuery = useQuery({
    queryKey: ['tickets', 'queue'],
    queryFn: () => ticketsApi.list(),
  })

  const tickets = ticketsQuery.data ?? []
  const selectedTicket = tickets.find((ticket) => ticket.id === selectedId) ?? null

  const filtered = useMemo(() => {
    const search = query.trim().toLowerCase()
    return tickets
      .filter((ticket) =>
        statusFilter
          ? ticket.status === statusFilter
          : ACTIVE_STATUSES.includes(ticket.status),
      )
      .filter((ticket) => !priorityFilter || ticket.priority === priorityFilter)
      .filter(
        (ticket) =>
          !search ||
          ticket.title.toLowerCase().includes(search) ||
          ticket.ticketCode.toLowerCase().includes(search) ||
          ticket.requesterName.toLowerCase().includes(search),
      )
      .sort((a, b) => {
        const aActive = ACTIVE_STATUSES.includes(a.status) ? 0 : 1
        const bActive = ACTIVE_STATUSES.includes(b.status) ? 0 : 1
        if (aActive !== bActive) return aActive - bActive
        const priority = PRIORITY_ORDER[a.priority] - PRIORITY_ORDER[b.priority]
        if (priority !== 0) return priority
        return b.createdAt.localeCompare(a.createdAt)
      })
  }, [tickets, statusFilter, priorityFilter, query])

  useEffect(() => {
    if (filtered.length === 0) {
      setSelectedId(null)
      return
    }
    if (!filtered.some((ticket) => ticket.id === selectedId)) {
      setSelectedId(filtered[0].id)
    }
  }, [filtered, selectedId])

  const suggestionsQuery = useQuery({
    queryKey: ['ticket-suggestions', selectedId],
    queryFn: () => ticketsApi.suggestions(selectedId as string),
    enabled: Boolean(selectedId),
    staleTime: 5 * 60_000,
    retry: 0,
  })

  const refreshQueue = () => {
    void queryClient.invalidateQueries({ queryKey: ['tickets', 'queue'] })
    void queryClient.invalidateQueries({ queryKey: ['tickets', 'mine'] })
    void queryClient.invalidateQueries({ queryKey: ['notifications'] })
  }

  const assignMutation = useMutation({
    mutationFn: ticketsApi.assign,
    onSuccess: () => {
      message.success('Đã nhận xử lý ticket.')
      refreshQueue()
    },
    onError: (error) => {
      message.error(error.message)
      refreshQueue()
    },
  })

  const resolveMutation = useMutation({
    mutationFn: ({ id, note }: { id: string; note: string }) =>
      ticketsApi.resolve(id, note),
    onSuccess: () => {
      message.success('Đã đánh dấu ticket xử lý xong.')
      setResolveOpen(false)
      resolveForm.resetFields()
      refreshQueue()
    },
    onError: (error) => message.error(error.message),
  })

  const closeMutation = useMutation({
    mutationFn: ticketsApi.close,
    onSuccess: () => {
      message.success('Đã đóng ticket.')
      refreshQueue()
    },
    onError: (error) => message.error(error.message),
  })

  const openCount = tickets.filter(
    (ticket) => ticket.status === 'OPEN' || ticket.status === 'REOPENED',
  ).length
  const inProgress = tickets.filter(
    (ticket) => ticket.status === 'IN_PROGRESS',
  ).length
  const resolved = tickets.filter(
    (ticket) => ticket.status === 'RESOLVED' || ticket.status === 'CLOSED',
  ).length
  const urgent = tickets.filter(
    (ticket) => ticket.priority === 'URGENT' && ticket.status !== 'CLOSED',
  ).length

  const setStatusFilter = (value: string) => {
    const next = new URLSearchParams(searchParams)
    if (value) next.set('status', value)
    else next.delete('status')
    setSearchParams(next, { replace: true })
  }

  const columns: TableProps<Ticket>['columns'] = [
    {
      title: 'Ticket',
      key: 'ticket',
      render: (_, ticket) => (
        <div className="table-title-cell">
          <span className="table-title">{ticket.title}</span>
          <span className="table-sub">
            {ticket.ticketCode} · {ticket.requesterName}
          </span>
        </div>
      ),
    },
    {
      title: 'Ưu tiên',
      key: 'priority',
      width: 100,
      render: (_, ticket) => <PriorityTag priority={ticket.priority} />,
    },
    {
      title: 'Trạng thái',
      key: 'status',
      width: 110,
      render: (_, ticket) => <StatusTag status={ticket.status} />,
    },
    {
      title: 'Phụ trách',
      key: 'assignee',
      width: 150,
      render: (_, ticket) => ticket.assigneeName ?? '—',
    },
  ]

  const suggestion = suggestionsQuery.data

  return (
    <div>
      <PageHeader
        title="Hàng đợi IT"
        description="Tiếp nhận, ưu tiên và xử lý yêu cầu hỗ trợ. Gợi ý xử lý được tổng hợp từ kho tri thức nội bộ."
        actions={
          <Tag icon={<ToolOutlined />} color="blue">
            {session?.fullName}
          </Tag>
        }
      />

      <div className="kpi-grid">
        <KpiCard label="Cần tiếp nhận" value={openCount} hint="Mới hoặc mở lại" />
        <KpiCard label="Đang xử lý" value={inProgress} hint="Đã có người phụ trách" />
        <KpiCard label="Đã xử lý" value={resolved} hint="Chờ đóng hoặc đã đóng" />
        <KpiCard label="Khẩn cấp" value={urgent} hint="Chưa đóng" />
      </div>

      <div className="queue-layout">
        <div className="queue-main">
          <div className="toolbar">
            <Input
              prefix={<FileSearchOutlined />}
              placeholder="Tìm mã ticket, tiêu đề hoặc người gửi"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              allowClear
              style={{ maxWidth: 340 }}
              aria-label="Tìm ticket"
            />
            <Select
              allowClear
              placeholder="Trạng thái"
              value={statusFilter || undefined}
              onChange={(value) => setStatusFilter(value ?? '')}
              options={STATUS_OPTIONS.map((status) => ({
                value: status,
                label: STATUS_LABELS[status],
              }))}
              style={{ minWidth: 160 }}
            />
            <Select
              allowClear
              placeholder="Ưu tiên"
              value={priorityFilter || undefined}
              onChange={(value) => setPriorityFilter(value ?? '')}
              options={(['URGENT', 'HIGH', 'MEDIUM', 'LOW'] as const).map(
                (priority) => ({
                  value: priority,
                  label: TICKET_PRIORITY_LABELS[priority],
                }),
              )}
              style={{ minWidth: 150 }}
            />
            <div className="toolbar__right muted text-sm">
              {filtered.length} ticket
            </div>
          </div>

          {ticketsQuery.isError ? (
            <ErrorState
              message="Không tải được hàng đợi IT."
              onRetry={() => ticketsQuery.refetch()}
            />
          ) : filtered.length > 0 ? (
            <div className="table-card">
              <Table<Ticket>
                rowKey="id"
                columns={columns}
                dataSource={filtered}
                loading={ticketsQuery.isLoading}
                pagination={{ pageSize: 8, hideOnSinglePage: true }}
                scroll={{ x: 560 }}
                rowClassName={(ticket) =>
                  ticket.id === selectedId ? 'table-row--selected' : ''
                }
                onRow={(ticket) => ({
                  onClick: () => setSelectedId(ticket.id),
                  style: { cursor: 'pointer' },
                })}
              />
            </div>
          ) : (
            <EmptyState
              title="Hàng đợi đang trống"
              description="Không có ticket phù hợp bộ lọc hiện tại."
            />
          )}
        </div>

        <aside className="queue-detail">
          {selectedTicket ? (
            <Panel
              title={
                <span className="row" style={{ gap: 8 }}>
                  {selectedTicket.ticketCode}
                  <StatusTag status={selectedTicket.status} />
                </span>
              }
              extra={<PriorityTag priority={selectedTicket.priority} />}
            >
              <div className="stack" style={{ gap: 14 }}>
                <div>
                  <h3 style={{ margin: 0, fontSize: 15 }}>{selectedTicket.title}</h3>
                  <div className="muted text-sm mt-8">
                    {selectedTicket.requesterName} ·{' '}
                    {formatDateTime(selectedTicket.createdAt)}
                  </div>
                </div>

                <div className="row row--wrap">
                  <Tag>{TICKET_CATEGORY_LABELS[selectedTicket.category]}</Tag>
                  {selectedTicket.aiConfidence !== null &&
                  selectedTicket.aiConfidence !== undefined ? (
                    <Tag color="cyan">
                      AI {formatPercent(selectedTicket.aiConfidence)}
                    </Tag>
                  ) : null}
                  <Tag>{selectedTicket.assigneeName ?? 'Chưa phân công'}</Tag>
                </div>

                <div>
                  <div className="muted text-sm">Mô tả</div>
                  <div className="chunk-content mt-8">
                    {selectedTicket.description}
                  </div>
                </div>

                {selectedTicket.resolutionNote ? (
                  <div>
                    <div className="muted text-sm">Kết quả xử lý</div>
                    <div className="chunk-content mt-8">
                      {selectedTicket.resolutionNote}
                    </div>
                  </div>
                ) : null}

                <div className="row row--wrap">
                  {selectedTicket.status === 'OPEN' ||
                  selectedTicket.status === 'REOPENED' ? (
                    <Button
                      type="primary"
                      icon={<CustomerServiceOutlined />}
                      loading={assignMutation.isPending}
                      onClick={() => assignMutation.mutate(selectedTicket.id)}
                    >
                      Nhận xử lý
                    </Button>
                  ) : null}
                  {selectedTicket.status === 'IN_PROGRESS' ? (
                    <Button
                      type="primary"
                      icon={<CheckCircleOutlined />}
                      onClick={() => {
                        resolveForm.resetFields()
                        setResolveOpen(true)
                      }}
                    >
                      Xử lý xong
                    </Button>
                  ) : null}
                  {selectedTicket.status === 'RESOLVED' ? (
                    <Button
                      icon={<CheckCircleOutlined />}
                      loading={closeMutation.isPending}
                      onClick={() => closeMutation.mutate(selectedTicket.id)}
                    >
                      Đóng ticket
                    </Button>
                  ) : null}
                  {selectedTicket.status === 'CLOSED' ? (
                    <Tag color="default" icon={<CheckCircleOutlined />}>
                      Ticket đã đóng
                    </Tag>
                  ) : null}
                </div>

                <div className="queue-suggestion">
                  <div className="queue-suggestion__head">
                    <Tag color="cyan" icon={<BulbOutlined />}>
                      AI gợi ý xử lý
                    </Tag>
                    <span className="muted text-sm">
                      Dựa trên kho tri thức nội bộ
                    </span>
                  </div>
                  {suggestionsQuery.isLoading ? (
                    <Skeleton active paragraph={{ rows: 3 }} />
                  ) : suggestionsQuery.isError ? (
                    <ErrorState
                      message="Không tải được gợi ý xử lý."
                      onRetry={() => suggestionsQuery.refetch()}
                    />
                  ) : suggestion ? (
                    <div className="stack" style={{ gap: 12 }}>
                      <div className="suggestion-steps">
                        {suggestion.steps.map((step, index) => (
                          <div key={step} className="suggestion-step">
                            <span className="suggestion-step__index">{index + 1}</span>
                            <span className="suggestion-step__text">{step}</span>
                          </div>
                        ))}
                      </div>
                      {suggestion.citations.length > 0 ? (
                        <div>
                          <div className="muted text-sm" style={{ marginBottom: 6 }}>
                            Nguồn tham khảo
                          </div>
                          {suggestion.citations.map((citation) => (
                            <CitationCard
                              key={`${citation.index}-${citation.chunk_id}`}
                              citation={citation}
                              onSelect={setSelectedCitation}
                            />
                          ))}
                        </div>
                      ) : (
                        <div className="muted text-sm">
                          Không tìm thấy tài liệu tham khảo phù hợp.
                        </div>
                      )}
                    </div>
                  ) : null}
                </div>
              </div>
            </Panel>
          ) : (
            <Panel title="Chi tiết ticket">
              <EmptyState
                title="Chọn một ticket"
                description="Chọn ticket bên trái để xem chi tiết và gợi ý xử lý."
              />
            </Panel>
          )}
        </aside>
      </div>

      <Modal
        title="Hoàn tất xử lý"
        open={resolveOpen}
        onCancel={() => {
          if (resolveMutation.isPending) return
          setResolveOpen(false)
          resolveForm.resetFields()
        }}
        okText="Đánh dấu đã xử lý"
        cancelText="Hủy"
        confirmLoading={resolveMutation.isPending}
        onOk={() => resolveForm.submit()}
        destroyOnHidden
      >
        <p className="muted text-sm" style={{ marginTop: 0 }}>
          Ghi lại kết quả để người gửi và bộ phận IT có thể tra cứu sau này.
        </p>
        <Form
          form={resolveForm}
          layout="vertical"
          requiredMark={false}
          onFinish={(values) => {
            if (!selectedTicket) return
            resolveMutation.mutate({ id: selectedTicket.id, note: values.note.trim() })
          }}
        >
          <Form.Item
            label="Kết quả xử lý"
            name="note"
            rules={[
              { required: true, message: 'Vui lòng nhập kết quả.' },
              { min: 10, message: 'Kết quả tối thiểu 10 ký tự.' },
              { max: 1000, message: 'Kết quả tối đa 1000 ký tự.' },
            ]}
          >
            <Input.TextArea
              rows={4}
              maxLength={1000}
              showCount
              placeholder="Ví dụ: Đã cấp lại quyền truy cập, xác nhận với người dùng qua điện thoại."
            />
          </Form.Item>
        </Form>
      </Modal>

      <CitationModal
        citation={selectedCitation}
        open={selectedCitation !== null}
        onClose={() => setSelectedCitation(null)}
      />

      <div className="docs-footnote">
        <ClockCircleOutlined /> Ticket khẩn cấp nên được ưu tiên theo thứ tự: Khẩn
        cấp → Cao → Trung bình → Thấp.
        <ExclamationCircleOutlined style={{ marginLeft: 8 }} /> Chỉ đóng ticket sau
        khi người gửi xác nhận.
      </div>
    </div>
  )
}
