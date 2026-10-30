import { useState } from 'react'
import {
  CheckOutlined,
  CloseOutlined,
  FileTextOutlined,
  InboxOutlined,
} from '@ant-design/icons'
import {
  App as AntApp,
  Badge,
  Button,
  Form,
  Input,
  Modal,
  Table,
  Tabs,
  Tag,
} from 'antd'
import type { TableProps } from 'antd'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { leaveApi } from '@/api/leave'
import type { LeaveRequest } from '@/api/types'
import { KpiCard } from '@/components/ui/KpiCard'
import { PageHeader } from '@/components/ui/PageHeader'
import { EmptyState, ErrorState } from '@/components/ui/States'
import { StatusTag } from '@/components/ui/Tags'
import { formatDate, formatDateTime } from '@/lib/dates'
import { formatNumber } from '@/lib/format'
import { usePageTitle } from '@/lib/usePageTitle'

type DecisionMode = 'approve' | 'reject'

interface DecisionFormValues {
  comment: string
}

export function ApprovalsPage() {
  usePageTitle('Phê duyệt')
  const { message } = AntApp.useApp()
  const queryClient = useQueryClient()
  const [form] = Form.useForm<DecisionFormValues>()
  const [decision, setDecision] = useState<{
    request: LeaveRequest
    mode: DecisionMode
  } | null>(null)

  const leavesQuery = useQuery({
    queryKey: ['leave', 'all'],
    queryFn: () => leaveApi.list(),
  })

  const decisionMutation = useMutation({
    mutationFn: ({
      request,
      mode,
      comment,
    }: {
      request: LeaveRequest
      mode: DecisionMode
      comment: string
    }) =>
      mode === 'approve'
        ? leaveApi.approve(request.id, comment)
        : leaveApi.reject(request.id, comment),
    onSuccess: (updated, variables) => {
      message.success(
        variables.mode === 'approve'
          ? `Đã duyệt đơn của ${updated.employeeName}.`
          : `Đã từ chối đơn của ${updated.employeeName}.`,
      )
      setDecision(null)
      form.resetFields()
      void queryClient.invalidateQueries({ queryKey: ['leave', 'all'] })
      void queryClient.invalidateQueries({ queryKey: ['leave', 'pending'] })
      void queryClient.invalidateQueries({ queryKey: ['leave', 'balance'] })
      void queryClient.invalidateQueries({ queryKey: ['notifications'] })
    },
    onError: (error) => {
      message.error(error.message)
      void queryClient.invalidateQueries({ queryKey: ['leave', 'all'] })
      void queryClient.invalidateQueries({ queryKey: ['leave', 'pending'] })
    },
  })

  const leaves = leavesQuery.data ?? []
  const pending = leaves.filter((leave) => leave.status === 'PENDING')
  const history = leaves
    .filter((leave) => leave.status !== 'PENDING')
    .sort((a, b) => (b.decidedAt ?? b.createdAt).localeCompare(a.decidedAt ?? a.createdAt))
  const pendingDays = pending.reduce((total, leave) => total + leave.totalDays, 0)
  const approved = leaves.filter((leave) => leave.status === 'APPROVED').length
  const rejected = leaves.filter((leave) => leave.status === 'REJECTED').length

  const openDecision = (request: LeaveRequest, mode: DecisionMode) => {
    setDecision({ request, mode })
    form.setFieldsValue({ comment: '' })
  }

  const closeDecision = () => {
    if (decisionMutation.isPending) return
    setDecision(null)
    form.resetFields()
  }

  const submitDecision = (values: DecisionFormValues) => {
    if (!decision) return
    decisionMutation.mutate({
      request: decision.request,
      mode: decision.mode,
      comment: values.comment?.trim() ?? '',
    })
  }

  const pendingColumns: TableProps<LeaveRequest>['columns'] = [
    {
      title: 'Nhân viên',
      dataIndex: 'employeeName',
      key: 'employeeName',
      width: 180,
      render: (value: string) => <span style={{ fontWeight: 500 }}>{value}</span>,
    },
    {
      title: 'Thời gian nghỉ',
      key: 'dates',
      width: 210,
      render: (_, leave) => (
        <div className="table-title-cell">
          <span className="table-title">
            {formatDate(leave.startDate)} – {formatDate(leave.endDate)}
          </span>
          <span className="table-sub">{formatNumber(leave.totalDays)} ngày</span>
        </div>
      ),
    },
    {
      title: 'Lý do',
      dataIndex: 'reason',
      key: 'reason',
      ellipsis: true,
    },
    {
      title: 'Gửi lúc',
      dataIndex: 'createdAt',
      key: 'createdAt',
      width: 160,
      render: (value: string) => formatDateTime(value),
    },
    {
      title: '',
      key: 'actions',
      width: 190,
      align: 'right',
      render: (_, leave) => (
        <div className="row" style={{ justifyContent: 'flex-end', gap: 6 }}>
          <Button
            size="small"
            type="primary"
            ghost
            icon={<CheckOutlined />}
            onClick={() => openDecision(leave, 'approve')}
          >
            Duyệt
          </Button>
          <Button
            size="small"
            danger
            icon={<CloseOutlined />}
            onClick={() => openDecision(leave, 'reject')}
          >
            Từ chối
          </Button>
        </div>
      ),
    },
  ]

  const historyColumns: TableProps<LeaveRequest>['columns'] = [
    {
      title: 'Nhân viên',
      dataIndex: 'employeeName',
      key: 'employeeName',
      width: 170,
    },
    {
      title: 'Thời gian nghỉ',
      key: 'dates',
      width: 210,
      render: (_, leave) =>
        `${formatDate(leave.startDate)} – ${formatDate(leave.endDate)} (${leave.totalDays} ngày)`,
    },
    {
      title: 'Trạng thái',
      key: 'status',
      width: 130,
      render: (_, leave) => <StatusTag status={leave.status} />,
    },
    {
      title: 'Người xử lý',
      dataIndex: 'approverName',
      key: 'approverName',
      width: 160,
      render: (value: string | undefined) => value ?? '—',
    },
    {
      title: 'Thời điểm xử lý',
      dataIndex: 'decidedAt',
      key: 'decidedAt',
      width: 160,
      render: (value: string | undefined) => (value ? formatDateTime(value) : '—'),
    },
    {
      title: 'Ghi chú',
      dataIndex: 'comment',
      key: 'comment',
      ellipsis: true,
      render: (value: string | undefined) => value || '—',
    },
  ]

  return (
    <div>
      <PageHeader
        title="Phê duyệt"
        description="Xử lý đơn nghỉ phép của đội ngũ. Đơn đã xử lý sẽ được lưu trong lịch sử."
        actions={
          <Tag icon={<InboxOutlined />} color={pending.length > 0 ? 'gold' : 'default'}>
            {pending.length} đơn đang chờ
          </Tag>
        }
      />

      <div className="kpi-grid">
        <KpiCard label="Chờ duyệt" value={pending.length} hint="Cần xử lý" />
        <KpiCard label="Ngày nghỉ chờ duyệt" value={pendingDays} hint="Tổng ngày yêu cầu" />
        <KpiCard label="Đã duyệt" value={approved} hint="Tất cả thời gian" />
        <KpiCard label="Từ chối" value={rejected} hint="Tất cả thời gian" />
      </div>

      {leavesQuery.isError ? (
        <ErrorState
          message="Không tải được danh sách đơn nghỉ."
          onRetry={() => leavesQuery.refetch()}
        />
      ) : (
        <Tabs
          items={[
            {
              key: 'pending',
              label: (
                <span>
                  Chờ duyệt{' '}
                  <Badge
                    count={pending.length}
                    size="small"
                    style={{ backgroundColor: 'var(--brand-700)' }}
                  />
                </span>
              ),
              children:
                pending.length > 0 ? (
                  <div className="table-card">
                    <Table<LeaveRequest>
                      rowKey="id"
                      columns={pendingColumns}
                      dataSource={pending}
                      loading={leavesQuery.isLoading}
                      pagination={false}
                      scroll={{ x: 920 }}
                      expandable={{
                        expandedRowRender: (leave) => (
                          <div className="approval-reason">
                            <FileTextOutlined /> {leave.reason}
                          </div>
                        ),
                      }}
                    />
                  </div>
                ) : (
                  <EmptyState
                    title="Không có đơn chờ duyệt"
                    description="Mọi đơn nghỉ phép của đội ngũ đã được xử lý."
                  />
                ),
            },
            {
              key: 'history',
              label: `Lịch sử (${history.length})`,
              children:
                history.length > 0 ? (
                  <div className="table-card">
                    <Table<LeaveRequest>
                      rowKey="id"
                      columns={historyColumns}
                      dataSource={history}
                      loading={leavesQuery.isLoading}
                      pagination={{ pageSize: 8, hideOnSinglePage: true }}
                      scroll={{ x: 960 }}
                    />
                  </div>
                ) : (
                  <EmptyState
                    title="Chưa có lịch sử xử lý"
                    description="Các đơn đã duyệt hoặc từ chối sẽ xuất hiện tại đây."
                  />
                ),
            },
          ]}
        />
      )}

      <Modal
        title={
          decision?.mode === 'approve' ? 'Duyệt đơn nghỉ phép' : 'Từ chối đơn nghỉ phép'
        }
        open={decision !== null}
        onCancel={closeDecision}
        okText={decision?.mode === 'approve' ? 'Duyệt đơn' : 'Từ chối'}
        cancelText="Hủy"
        okButtonProps={{ danger: decision?.mode === 'reject' }}
        confirmLoading={decisionMutation.isPending}
        onOk={() => form.submit()}
        destroyOnHidden
      >
        {decision ? (
          <>
            <div className="detail-list" style={{ marginBottom: 16 }}>
              <div className="detail-row">
                <span className="detail-row__label">Nhân viên</span>
                <span className="detail-row__value">{decision.request.employeeName}</span>
              </div>
              <div className="detail-row">
                <span className="detail-row__label">Thời gian</span>
                <span className="detail-row__value">
                  {formatDate(decision.request.startDate)} –{' '}
                  {formatDate(decision.request.endDate)} ({decision.request.totalDays}{' '}
                  ngày)
                </span>
              </div>
              <div className="detail-row">
                <span className="detail-row__label">Lý do</span>
                <span className="detail-row__value">{decision.request.reason}</span>
              </div>
            </div>
            <Form
              form={form}
              layout="vertical"
              requiredMark={false}
              onFinish={submitDecision}
            >
              <Form.Item
                label="Ghi chú xử lý"
                name="comment"
                rules={
                  decision.mode === 'reject'
                    ? [
                        { required: true, message: 'Vui lòng nêu lý do từ chối.' },
                        { min: 5, message: 'Ghi chú tối thiểu 5 ký tự.' },
                      ]
                    : [{ max: 500, message: 'Ghi chú tối đa 500 ký tự.' }]
                }
              >
                <Input.TextArea
                  rows={3}
                  maxLength={500}
                  showCount
                  placeholder={
                    decision.mode === 'approve'
                      ? 'Ghi chú thêm (không bắt buộc)'
                      : 'Nêu rõ lý do từ chối để nhân viên điều chỉnh'
                  }
                />
              </Form.Item>
            </Form>
          </>
        ) : null}
      </Modal>
    </div>
  )
}
