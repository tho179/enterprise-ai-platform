import { useEffect, useState } from 'react'
import {
  BulbOutlined,
  ClockCircleOutlined,
  CustomerServiceOutlined,
  FileTextOutlined,
  InboxOutlined,
  PaperClipOutlined,
  PlusOutlined,
  ReloadOutlined,
  ThunderboltOutlined,
} from '@ant-design/icons'
import {
  Alert,
  App as AntApp,
  Button,
  Drawer,
  Form,
  Input,
  Progress,
  Select,
  Table,
  Tabs,
  Tag,
  Timeline,
  Upload,
} from 'antd'
import type { TableProps } from 'antd'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useSearchParams } from 'react-router-dom'
import { ticketsApi } from '@/api/tickets'
import type {
  Classification,
  Ticket,
  TicketCategory,
  TicketPriority,
} from '@/api/types'
import { useAuth } from '@/auth/AuthContext'
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
import { formatDateTime, formatRelative } from '@/lib/dates'
import { formatPercent } from '@/lib/format'
import { usePageTitle } from '@/lib/usePageTitle'

interface TicketFormValues {
  title: string
  description: string
  category: TicketCategory
  priority: TicketPriority
}

const FORM_CATEGORIES: TicketCategory[] = [
  'NETWORK',
  'HARDWARE',
  'SOFTWARE',
  'ACCOUNT',
  'OTHER',
]

const FORM_PRIORITIES: TicketPriority[] = ['LOW', 'MEDIUM', 'HIGH', 'URGENT']

const MY_STATUSES = ['OPEN', 'IN_PROGRESS', 'RESOLVED', 'CLOSED', 'REOPENED']

export function TicketsPage() {
  usePageTitle('Yêu cầu IT')
  const { message } = AntApp.useApp()
  const { session } = useAuth()
  const queryClient = useQueryClient()
  const [searchParams, setSearchParams] = useSearchParams()
  const [form] = Form.useForm<TicketFormValues>()
  const [attachment, setAttachment] = useState<File | null>(null)
  const [attachmentError, setAttachmentError] = useState<string | null>(null)
  const [classification, setClassification] = useState<Classification | null>(null)
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [statusFilter, setStatusFilter] = useState('')
  const tab = searchParams.get('tab') === 'new' ? 'new' : 'mine'

  const ticketsQuery = useQuery({
    queryKey: ['tickets', 'mine'],
    queryFn: () => ticketsApi.list({ mine: true }),
    enabled: session !== null,
  })

  const classifyMutation = useMutation({
    mutationFn: ({ title, description }: { title: string; description: string }) =>
      ticketsApi.classify(title, description),
    onSuccess: (result) => setClassification(result),
    onError: (error) => message.error(error.message),
  })

  const createMutation = useMutation({
    mutationFn: (values: TicketFormValues) =>
      ticketsApi.create({
        title: values.title.trim(),
        description: values.description.trim(),
        category: values.category,
        priority: values.priority,
        attachmentName: attachment?.name ?? null,
        aiConfidence: classification?.confidence ?? null,
      }),
    onSuccess: (ticket) => {
      message.success(`Đã gửi yêu cầu ${ticket.ticketCode}.`)
      form.resetFields()
      setAttachment(null)
      setClassification(null)
      setSelectedId(ticket.id)
      void queryClient.invalidateQueries({ queryKey: ['tickets', 'mine'] })
      void queryClient.invalidateQueries({ queryKey: ['tickets', 'queue'] })
      setSearchParams({ tab: 'mine' }, { replace: true })
    },
    onError: (error) => message.error(error.message),
  })

  const reopenMutation = useMutation({
    mutationFn: ticketsApi.reopen,
    onSuccess: () => {
      message.success('Đã mở lại yêu cầu. Bộ phận IT sẽ tiếp tục xử lý.')
      void queryClient.invalidateQueries({ queryKey: ['tickets', 'mine'] })
      void queryClient.invalidateQueries({ queryKey: ['tickets', 'queue'] })
    },
    onError: (error) => message.error(error.message),
  })

  const tickets = ticketsQuery.data ?? []
  const filtered = tickets.filter(
    (ticket) => !statusFilter || ticket.status === statusFilter,
  )
  const selectedTicket = tickets.find((ticket) => ticket.id === selectedId) ?? null
  const openCount = tickets.filter(
    (ticket) => ticket.status === 'OPEN' || ticket.status === 'REOPENED',
  ).length
  const inProgress = tickets.filter(
    (ticket) => ticket.status === 'IN_PROGRESS',
  ).length
  const resolved = tickets.filter(
    (ticket) => ticket.status === 'RESOLVED' || ticket.status === 'CLOSED',
  ).length

  useEffect(() => {
    if (tab === 'new') {
      setSelectedId(null)
    }
  }, [tab])

  const ensureClassification = async () => {
    try {
      const values = await form.validateFields(['title', 'description'])
      classifyMutation.mutate({
        title: values.title,
        description: values.description,
      })
    } catch {
      message.warning('Nhập tiêu đề và mô tả trước khi phân loại bằng AI.')
    }
  }

  const applyClassification = () => {
    if (!classification) return
    form.setFieldsValue({
      category: classification.category,
      priority: classification.priority,
    })
    message.success('Đã áp dụng phân loại do AI đề xuất.')
  }

  const handleCreate = (values: TicketFormValues) => {
    if (attachment && attachment.size > 10 * 1024 * 1024) {
      setAttachmentError('Tệp đính kèm vượt quá 10 MB.')
      return
    }
    createMutation.mutate(values)
  }

  const columns: TableProps<Ticket>['columns'] = [
    {
      title: 'Yêu cầu',
      key: 'title',
      render: (_, ticket) => (
        <div className="table-title-cell">
          <span className="table-title">{ticket.title}</span>
          <span className="table-sub">
            {ticket.ticketCode} · {formatRelative(ticket.createdAt)}
          </span>
        </div>
      ),
    },
    {
      title: 'Phân loại',
      key: 'category',
      width: 130,
      render: (_, ticket) => (
        <Tag>{TICKET_CATEGORY_LABELS[ticket.category]}</Tag>
      ),
    },
    {
      title: 'Ưu tiên',
      key: 'priority',
      width: 130,
      render: (_, ticket) => <PriorityTag priority={ticket.priority} />,
    },
    {
      title: 'Trạng thái',
      key: 'status',
      width: 140,
      render: (_, ticket) => <StatusTag status={ticket.status} />,
    },
    {
      title: 'Người xử lý',
      key: 'assignee',
      width: 170,
      render: (_, ticket) => ticket.assigneeName ?? 'Chưa phân công',
    },
    {
      title: 'Cập nhật',
      key: 'updated',
      width: 150,
      render: (_, ticket) =>
        formatDateTime(ticket.resolvedAt ?? ticket.createdAt),
    },
    {
      title: '',
      key: 'actions',
      width: 80,
      align: 'right',
      render: (_, ticket) => (
        <Button
          size="small"
          onClick={(event) => {
            event.stopPropagation()
            setSelectedId(ticket.id)
          }}
        >
          Xem
        </Button>
      ),
    },
  ]

  const timelineItems = selectedTicket
    ? [
        {
          color: 'blue',
          children: (
            <span>
              Tạo yêu cầu · {formatDateTime(selectedTicket.createdAt)}
            </span>
          ),
        },
        ...(selectedTicket.assigneeName
          ? [
              {
                color: 'blue',
                children: (
                  <span>
                    Tiếp nhận bởi {selectedTicket.assigneeName}
                  </span>
                ),
              },
            ]
          : []),
        ...(selectedTicket.resolvedAt
          ? [
              {
                color: 'green',
                children: (
                  <span>
                    {STATUS_LABELS[selectedTicket.status]} ·{' '}
                    {formatDateTime(selectedTicket.resolvedAt)}
                  </span>
                ),
              },
            ]
          : []),
      ]
    : []

  return (
    <div>
      <PageHeader
        title="Yêu cầu IT"
        description="Gửi yêu cầu hỗ trợ kỹ thuật và theo dõi tiến độ xử lý. Nội dung sẽ được AI phân loại để chuyển đúng nhóm hỗ trợ."
        actions={
          <Button
            type="primary"
            icon={<PlusOutlined />}
            onClick={() => setSearchParams({ tab: 'new' }, { replace: true })}
          >
            Tạo yêu cầu
          </Button>
        }
      />

      <div className="kpi-grid">
        <KpiCard label="Mới / mở lại" value={openCount} hint="Chờ IT tiếp nhận" />
        <KpiCard label="Đang xử lý" value={inProgress} hint="IT đang thực hiện" />
        <KpiCard label="Đã xử lý" value={resolved} hint="Đã xử lý hoặc đóng" />
        <KpiCard label="Tổng yêu cầu" value={tickets.length} hint="Của tôi" />
      </div>

      <Tabs
        activeKey={tab}
        onChange={(key) =>
          setSearchParams(key === 'mine' ? { tab: 'mine' } : { tab: 'new' }, {
            replace: true,
          })
        }
        items={[
          {
            key: 'mine',
            label: 'Yêu cầu của tôi',
            children: (
              <div className="stack">
                <div className="toolbar">
                  <Select
                    allowClear
                    placeholder="Trạng thái"
                    value={statusFilter || undefined}
                    onChange={(value) => setStatusFilter(value ?? '')}
                    options={MY_STATUSES.map((status) => ({
                      value: status,
                      label: STATUS_LABELS[status],
                    }))}
                    style={{ minWidth: 180 }}
                  />
                  <div className="toolbar__right muted text-sm">
                    {filtered.length} yêu cầu
                  </div>
                </div>

                {ticketsQuery.isError ? (
                  <ErrorState
                    message="Không tải được danh sách yêu cầu."
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
                      scroll={{ x: 940 }}
                      onRow={(ticket) => ({
                        onClick: () => setSelectedId(ticket.id),
                        style: { cursor: 'pointer' },
                      })}
                    />
                  </div>
                ) : (
                  <EmptyState
                    title="Chưa có yêu cầu IT"
                    description="Khi gặp sự cố kỹ thuật, tạo yêu cầu để bộ phận IT hỗ trợ."
                    action={
                      <Button
                        type="primary"
                        icon={<PlusOutlined />}
                        onClick={() => setSearchParams({ tab: 'new' })}
                      >
                        Tạo yêu cầu
                      </Button>
                    }
                  />
                )}
              </div>
            ),
          },
          {
            key: 'new',
            label: 'Tạo yêu cầu',
            children: (
              <div className="ticket-create-layout">
                <Panel title="Nội dung yêu cầu">
                  <Form
                    form={form}
                    layout="vertical"
                    requiredMark={false}
                    initialValues={{
                      category: 'OTHER',
                      priority: 'MEDIUM',
                    }}
                    onFinish={handleCreate}
                  >
                    <Form.Item
                      label="Tiêu đề"
                      name="title"
                      rules={[
                        { required: true, message: 'Vui lòng nhập tiêu đề.' },
                        { min: 5, message: 'Tiêu đề tối thiểu 5 ký tự.' },
                        { max: 200, message: 'Tiêu đề tối đa 200 ký tự.' },
                      ]}
                    >
                      <Input placeholder="Ví dụ: Không kết nối được VPN" />
                    </Form.Item>
                    <Form.Item
                      label="Mô tả sự cố"
                      name="description"
                      rules={[
                        { required: true, message: 'Vui lòng mô tả sự cố.' },
                        { min: 20, message: 'Mô tả tối thiểu 20 ký tự.' },
                        { max: 2000, message: 'Mô tả tối đa 2000 ký tự.' },
                      ]}
                    >
                      <Input.TextArea
                        rows={5}
                        maxLength={2000}
                        showCount
                        placeholder="Thời điểm xảy ra, thiết bị/hệ thống liên quan, thông báo lỗi và các bước đã thử."
                      />
                    </Form.Item>

                    <div className="row row--wrap" style={{ marginBottom: 18 }}>
                      <Button
                        icon={<ThunderboltOutlined />}
                        onClick={ensureClassification}
                        loading={classifyMutation.isPending}
                      >
                        Phân tích bằng AI
                      </Button>
                      <span className="muted text-sm">
                        AI đề xuất nhóm và mức ưu tiên, bạn vẫn có thể chỉnh lại.
                      </span>
                    </div>

                    {classification ? (
                      <div className="ai-suggestion">
                        <div className="ai-suggestion__head">
                          <BulbOutlined />
                          <strong>Đề xuất từ AI</strong>
                          <span className="score-pill" style={{ marginLeft: 'auto' }}>
                            {formatPercent(classification.confidence)}
                          </span>
                        </div>
                        <div className="row row--wrap">
                          <Tag color="blue">
                            {TICKET_CATEGORY_LABELS[classification.category]}
                          </Tag>
                          <PriorityTag priority={classification.priority} />
                          <Button size="small" type="link" onClick={applyClassification}>
                            Áp dụng đề xuất
                          </Button>
                        </div>
                        <Progress
                          percent={Math.round(classification.confidence * 100)}
                          size="small"
                          showInfo={false}
                          strokeColor="var(--accent)"
                        />
                      </div>
                    ) : null}

                    <div className="form-grid">
                      <Form.Item
                        label="Nhóm sự cố"
                        name="category"
                        rules={[{ required: true, message: 'Chọn nhóm sự cố.' }]}
                      >
                        <Select
                          options={FORM_CATEGORIES.map((category) => ({
                            value: category,
                            label: TICKET_CATEGORY_LABELS[category],
                          }))}
                        />
                      </Form.Item>
                      <Form.Item
                        label="Mức ưu tiên"
                        name="priority"
                        rules={[{ required: true, message: 'Chọn mức ưu tiên.' }]}
                      >
                        <Select
                          options={FORM_PRIORITIES.map((priority) => ({
                            value: priority,
                            label: TICKET_PRIORITY_LABELS[priority],
                          }))}
                        />
                      </Form.Item>
                    </div>

                    <Form.Item label="Tệp đính kèm (không bắt buộc)">
                      <Upload
                        accept=".png,.jpg,.jpeg,.pdf,.txt,.log"
                        maxCount={1}
                        showUploadList={false}
                        beforeUpload={(selected) => {
                          setAttachment(selected)
                          setAttachmentError(
                            selected.size > 10 * 1024 * 1024
                              ? 'Tệp đính kèm vượt quá 10 MB.'
                              : null,
                          )
                          return false
                        }}
                      >
                        <Button icon={<PaperClipOutlined />}>Chọn tệp đính kèm</Button>
                      </Upload>
                      {attachment ? (
                        <div className="upload-file mt-12">
                          <FileTextOutlined />
                          <div className="grow">
                            <div style={{ fontWeight: 500 }}>{attachment.name}</div>
                            <div className="muted text-sm">
                              {Math.round(attachment.size / 1024)} KB
                            </div>
                          </div>
                          <Button size="small" onClick={() => setAttachment(null)}>
                            Bỏ chọn
                          </Button>
                        </div>
                      ) : null}
                      {attachmentError ? (
                        <Alert
                          type="warning"
                          showIcon
                          title={attachmentError}
                          style={{ marginTop: 10 }}
                        />
                      ) : null}
                    </Form.Item>

                    <Button
                      type="primary"
                      htmlType="submit"
                      icon={<InboxOutlined />}
                      loading={createMutation.isPending}
                    >
                      Gửi yêu cầu
                    </Button>
                  </Form>
                </Panel>

                <div className="stack">
                  <Panel title="AI hỗ trợ phân loại">
                    <div className="suggestion-steps">
                      <div className="suggestion-step">
                        <span className="suggestion-step__index">1</span>
                        <span className="suggestion-step__text">
                          Mô tả càng rõ thiết bị, hệ thống và thông báo lỗi thì phân
                          loại càng chính xác.
                        </span>
                      </div>
                      <div className="suggestion-step">
                        <span className="suggestion-step__index">2</span>
                        <span className="suggestion-step__text">
                          AI đọc tiêu đề và mô tả để đề xuất nhóm sự cố, mức ưu tiên
                          và độ tin cậy.
                        </span>
                      </div>
                      <div className="suggestion-step">
                        <span className="suggestion-step__index">3</span>
                        <span className="suggestion-step__text">
                          Kết quả cuối cùng do bạn quyết định trước khi gửi yêu cầu.
                        </span>
                      </div>
                    </div>
                  </Panel>
                  <Panel title="Cam kết xử lý">
                    <div className="detail-list">
                      <div className="detail-row">
                        <span className="detail-row__label">Phản hồi</span>
                        <span className="detail-row__value">Trong 4 giờ làm việc</span>
                      </div>
                      <div className="detail-row">
                        <span className="detail-row__label">Khẩn cấp</span>
                        <span className="detail-row__value">Xử lý trong 1 giờ</span>
                      </div>
                      <div className="detail-row">
                        <span className="detail-row__label">Theo dõi</span>
                        <span className="detail-row__value">
                          Cập nhật trạng thái trong mục Yêu cầu của tôi
                        </span>
                      </div>
                    </div>
                  </Panel>
                </div>
              </div>
            ),
          },
        ]}
      />

      <Drawer
        title={selectedTicket ? selectedTicket.ticketCode : 'Chi tiết yêu cầu'}
        size={540}
        open={selectedTicket !== null}
        onClose={() => setSelectedId(null)}
      >
        {selectedTicket ? (
          <div className="stack" style={{ gap: 18 }}>
            <div>
              <div className="row row--wrap" style={{ marginBottom: 6 }}>
                <StatusTag status={selectedTicket.status} />
                <PriorityTag priority={selectedTicket.priority} />
                <Tag>{TICKET_CATEGORY_LABELS[selectedTicket.category]}</Tag>
              </div>
              <h2 style={{ fontSize: 17, margin: 0 }}>{selectedTicket.title}</h2>
              <div className="muted text-sm mt-8">
                Gửi bởi {selectedTicket.requesterName} ·{' '}
                {formatDateTime(selectedTicket.createdAt)}
              </div>
            </div>

            <div>
              <div className="muted text-sm">Mô tả</div>
              <div className="chunk-content mt-8">{selectedTicket.description}</div>
            </div>

            {selectedTicket.attachmentName ? (
              <div className="upload-file">
                <PaperClipOutlined />
                <div className="grow">
                  <div style={{ fontWeight: 500 }}>{selectedTicket.attachmentName}</div>
                  <div className="muted text-sm">Tệp đính kèm</div>
                </div>
              </div>
            ) : null}

            <div className="detail-list">
              <div className="detail-row">
                <span className="detail-row__label">Người xử lý</span>
                <span className="detail-row__value">
                  {selectedTicket.assigneeName ?? 'Chưa phân công'}
                </span>
              </div>
              {selectedTicket.aiConfidence !== null &&
              selectedTicket.aiConfidence !== undefined ? (
                <div className="detail-row">
                  <span className="detail-row__label">Độ tin cậy AI</span>
                  <span className="detail-row__value">
                    {formatPercent(selectedTicket.aiConfidence)}
                  </span>
                </div>
              ) : null}
              {selectedTicket.resolutionNote ? (
                <div className="detail-row">
                  <span className="detail-row__label">Kết quả</span>
                  <span className="detail-row__value">{selectedTicket.resolutionNote}</span>
                </div>
              ) : null}
            </div>

            <div>
              <div className="muted text-sm" style={{ marginBottom: 8 }}>
                Tiến trình
              </div>
              <Timeline items={timelineItems} />
            </div>

            {selectedTicket.status === 'RESOLVED' ||
            selectedTicket.status === 'CLOSED' ? (
              <Button
                icon={<ReloadOutlined />}
                loading={reopenMutation.isPending}
                onClick={() => reopenMutation.mutate(selectedTicket.id)}
              >
                Mở lại yêu cầu
              </Button>
            ) : (
              <Alert
                type="info"
                showIcon
                icon={<ClockCircleOutlined />}
                title="Bộ phận IT đang xử lý yêu cầu của bạn."
                description="Bạn sẽ nhận được thông báo khi trạng thái thay đổi."
              />
            )}
          </div>
        ) : null}
      </Drawer>

      <div className="docs-footnote">
        <CustomerServiceOutlined /> Yêu cầu khẩn cấp nên được gọi trực tiếp hotline
        IT sau khi gửi ticket.
      </div>
    </div>
  )
}
