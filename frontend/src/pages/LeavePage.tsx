import { useState } from 'react'
import {
  CalendarOutlined,
  CheckCircleOutlined,
  ClockCircleOutlined,
  FileTextOutlined,
  PlusOutlined,
  StopOutlined,
} from '@ant-design/icons'
import {
  Alert,
  App as AntApp,
  Button,
  DatePicker,
  Form,
  Input,
  Popconfirm,
  Progress,
  Select,
  Table,
  Tabs,
  Tag,
  Tooltip,
} from 'antd'
import type { TableProps } from 'antd'
import dayjs from 'dayjs'
import type { Dayjs } from 'dayjs'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Link, useSearchParams } from 'react-router-dom'
import { leaveApi } from '@/api/leave'
import type { LeaveRequest, LeaveStatus } from '@/api/types'
import { useAuth } from '@/auth/AuthContext'
import { KpiCard } from '@/components/ui/KpiCard'
import { PageHeader } from '@/components/ui/PageHeader'
import { Panel } from '@/components/ui/Panel'
import { EmptyState, ErrorState } from '@/components/ui/States'
import { StatusTag } from '@/components/ui/Tags'
import { STATUS_LABELS } from '@/lib/constants'
import { countInclusiveDays, formatDate, formatDateTime, rangesOverlap } from '@/lib/dates'
import { formatNumber } from '@/lib/format'
import { usePageTitle } from '@/lib/usePageTitle'

interface LeaveFormValues {
  range: [Dayjs, Dayjs]
  reason: string
}

const LEAVE_STATUSES: LeaveStatus[] = ['PENDING', 'APPROVED', 'REJECTED', 'CANCELLED']

export function LeavePage() {
  usePageTitle('Nghỉ phép')
  const { session } = useAuth()
  const { message } = AntApp.useApp()
  const queryClient = useQueryClient()
  const [searchParams, setSearchParams] = useSearchParams()
  const [form] = Form.useForm<LeaveFormValues>()
  const [statusFilter, setStatusFilter] = useState<string>('')
  const tabParam = searchParams.get('tab') ?? 'mine'
  const activeTab = tabParam === 'new' ? 'new' : 'mine'
  const watchedRange = Form.useWatch('range', form) as
    | [Dayjs, Dayjs]
    | undefined

  const balanceQuery = useQuery({
    queryKey: ['leave', 'balance'],
    queryFn: leaveApi.balance,
  })
  const leavesQuery = useQuery({
    queryKey: ['leave', 'mine'],
    queryFn: () => leaveApi.list({ mine: true }),
    enabled: session !== null,
  })

  const leaves = leavesQuery.data ?? []
  const filteredLeaves = leaves.filter(
    (leave) => !statusFilter || leave.status === statusFilter,
  )
  const pendingLeaves = leaves.filter((leave) => leave.status === 'PENDING')
  const approvedDays = leaves
    .filter((leave) => leave.status === 'APPROVED')
    .reduce((total, leave) => total + leave.totalDays, 0)

  const requestedDays = watchedRange
    ? countInclusiveDays(
        watchedRange[0].format('YYYY-MM-DD'),
        watchedRange[1].format('YYYY-MM-DD'),
      )
    : 0

  const refreshLeaveQueries = () => {
    void queryClient.invalidateQueries({ queryKey: ['leave', 'mine'] })
    void queryClient.invalidateQueries({ queryKey: ['leave', 'all'] })
    void queryClient.invalidateQueries({ queryKey: ['leave', 'pending'] })
    void queryClient.invalidateQueries({ queryKey: ['leave', 'balance'] })
    void queryClient.invalidateQueries({ queryKey: ['notifications'] })
  }

  const createMutation = useMutation({
    mutationFn: leaveApi.create,
    onSuccess: (created) => {
      message.success(
        `Đã gửi đơn nghỉ ${created.totalDays} ngày và đang chờ quản lý duyệt.`,
      )
      form.resetFields()
      refreshLeaveQueries()
      setSearchParams({ tab: 'mine' }, { replace: true })
    },
    onError: (error) => message.error(error.message),
  })

  const cancelMutation = useMutation({
    mutationFn: leaveApi.cancel,
    onSuccess: () => {
      message.success('Đã hủy đơn nghỉ.')
      refreshLeaveQueries()
    },
    onError: (error) => message.error(error.message),
  })

  const balance = balanceQuery.data
  const usedPercent = balance
    ? Math.min(100, Math.round((balance.used / balance.total) * 100))
    : 0

  const columns: TableProps<LeaveRequest>['columns'] = [
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
      render: (reason: string) => (
        <Tooltip title={reason}>
          <span>{reason}</span>
        </Tooltip>
      ),
    },
    {
      title: 'Trạng thái',
      key: 'status',
      width: 140,
      render: (_, leave) => <StatusTag status={leave.status} />,
    },
    {
      title: 'Người duyệt',
      key: 'approver',
      width: 170,
      render: (_, leave) => (
        <div className="table-title-cell">
          <span>{leave.approverName ?? 'Chưa duyệt'}</span>
          {leave.comment ? (
            <span className="table-sub" title={leave.comment}>
              {leave.comment}
            </span>
          ) : null}
        </div>
      ),
    },
    {
      title: 'Ngày gửi',
      dataIndex: 'createdAt',
      key: 'createdAt',
      width: 150,
      render: (value: string) => formatDateTime(value),
    },
    {
      title: '',
      key: 'actions',
      width: 90,
      align: 'right',
      render: (_, leave) =>
        leave.status === 'PENDING' ? (
          <Popconfirm
            title="Hủy đơn nghỉ?"
            description="Đơn nghỉ sẽ chuyển sang trạng thái đã hủy và không thể khôi phục."
            okText="Hủy đơn"
            cancelText="Giữ lại"
            okButtonProps={{ danger: true }}
            onConfirm={() => cancelMutation.mutate(leave.id)}
          >
            <Button
              size="small"
              danger
              icon={<StopOutlined />}
              loading={
                cancelMutation.isPending && cancelMutation.variables === leave.id
              }
            >
              Hủy
            </Button>
          </Popconfirm>
        ) : null,
    },
  ]

  const handleSubmit = (values: LeaveFormValues) => {
    const [start, end] = values.range
    const startDate = start.format('YYYY-MM-DD')
    const endDate = end.format('YYYY-MM-DD')
    const totalDays = countInclusiveDays(startDate, endDate)
    if (totalDays <= 0) {
      message.error('Khoảng thời gian nghỉ không hợp lệ.')
      return
    }
    const conflict = leaves.find(
      (leave) =>
        (leave.status === 'PENDING' || leave.status === 'APPROVED') &&
        rangesOverlap(startDate, endDate, leave.startDate, leave.endDate),
    )
    if (conflict) {
      message.error(
        `Trùng với đơn ${conflict.status === 'APPROVED' ? 'đã duyệt' : 'đang chờ duyệt'} (${formatDate(conflict.startDate)} – ${formatDate(conflict.endDate)}).`,
      )
      return
    }
    createMutation.mutate({
      startDate,
      endDate,
      totalDays,
      reason: values.reason.trim(),
    })
  }

  return (
    <div>
      <PageHeader
        title="Nghỉ phép"
        description="Theo dõi số ngày phép, gửi đơn nghỉ và kiểm tra trạng thái phê duyệt."
        actions={
          <Button
            type="primary"
            icon={<PlusOutlined />}
            onClick={() => setSearchParams({ tab: 'new' }, { replace: true })}
          >
            Tạo đơn nghỉ
          </Button>
        }
      />

      <div className="kpi-grid">
        <KpiCard
          label="Ngày phép còn lại"
          value={balance?.remaining ?? '—'}
          hint={balance ? `Trong tổng số ${balance.total} ngày` : 'Đang tải số dư'}
        />
        <KpiCard
          label="Đã sử dụng"
          value={balance?.used ?? '—'}
          hint="Ngày phép đã duyệt"
        />
        <KpiCard
          label="Đơn chờ duyệt"
          value={pendingLeaves.length}
          hint="Đang chờ quản lý xử lý"
        />
        <KpiCard
          label="Ngày đã duyệt"
          value={approvedDays}
          hint="Cộng dồn các đơn đã duyệt"
        />
      </div>

      <Tabs
        activeKey={activeTab}
        onChange={(key) =>
          setSearchParams(key === 'mine' ? { tab: 'mine' } : { tab: 'new' }, {
            replace: true,
          })
        }
        items={[
          {
            key: 'mine',
            label: 'Đơn của tôi',
            children: (
              <div className="stack">
                <div className="leave-balance">
                  <div>
                    <div className="leave-balance__number">
                      {balance?.remaining ?? '—'}
                    </div>
                    <div className="leave-balance__label">
                      ngày phép còn lại
                    </div>
                  </div>
                  <div className="grow">
                    <div className="row" style={{ justifyContent: 'space-between' }}>
                      <span className="muted text-sm">
                        Đã dùng {balance?.used ?? 0}/{balance?.total ?? 12} ngày
                      </span>
                      <span className="muted text-sm">{usedPercent}%</span>
                    </div>
                    <Progress
                      percent={usedPercent}
                      showInfo={false}
                      strokeColor="var(--brand-700)"
                      trailColor="#eef2f6"
                      style={{ marginBottom: 0 }}
                    />
                  </div>
                  <Tag icon={<CalendarOutlined />} color="blue">
                    Năm 2026
                  </Tag>
                </div>

                <div className="toolbar">
                  <Select
                    allowClear
                    placeholder="Trạng thái"
                    value={statusFilter || undefined}
                    onChange={(value) => setStatusFilter(value ?? '')}
                    options={LEAVE_STATUSES.map((status) => ({
                      value: status,
                      label: STATUS_LABELS[status],
                    }))}
                    style={{ minWidth: 180 }}
                  />
                  <div className="toolbar__right muted text-sm">
                    {filteredLeaves.length} đơn
                  </div>
                </div>

                {leavesQuery.isError ? (
                  <ErrorState
                    message="Không tải được danh sách đơn nghỉ."
                    onRetry={() => leavesQuery.refetch()}
                  />
                ) : leavesQuery.isLoading ? (
                  <Panel title="Danh sách đơn nghỉ">
                    <div className="panel-empty">Đang tải…</div>
                  </Panel>
                ) : filteredLeaves.length > 0 ? (
                  <div className="table-card">
                    <Table<LeaveRequest>
                      rowKey="id"
                      columns={columns}
                      dataSource={filteredLeaves}
                      pagination={{ pageSize: 6, hideOnSinglePage: true }}
                      scroll={{ x: 900 }}
                    />
                  </div>
                ) : (
                  <EmptyState
                    title="Chưa có đơn nghỉ phép"
                    description="Bạn chưa gửi đơn nghỉ nào hoặc không có đơn phù hợp bộ lọc."
                    action={
                      <Button
                        type="primary"
                        icon={<PlusOutlined />}
                        onClick={() => setSearchParams({ tab: 'new' })}
                      >
                        Tạo đơn nghỉ
                      </Button>
                    }
                  />
                )}
              </div>
            ),
          },
          {
            key: 'new',
            label: 'Tạo đơn nghỉ',
            children: (
              <div className="leave-form-layout">
                <Panel title="Thông tin đơn nghỉ">
                  <Form
                    form={form}
                    layout="vertical"
                    requiredMark={false}
                    onFinish={handleSubmit}
                  >
                    <Form.Item
                      label="Khoảng thời gian nghỉ"
                      name="range"
                      rules={[{ required: true, message: 'Chọn thời gian nghỉ.' }]}
                    >
                      <DatePicker.RangePicker
                        format="DD/MM/YYYY"
                        style={{ width: '100%' }}
                        disabledDate={(current) =>
                          current
                            ? current.startOf('day').isBefore(dayjs().startOf('day'))
                            : false
                        }
                      />
                    </Form.Item>
                    <div className="leave-days-hint">
                      <ClockCircleOutlined /> Số ngày nghỉ dự kiến:{' '}
                      <strong>{requestedDays} ngày</strong>
                    </div>
                    <Form.Item
                      label="Lý do nghỉ"
                      name="reason"
                      rules={[
                        { required: true, message: 'Vui lòng nhập lý do.' },
                        { min: 10, message: 'Lý do tối thiểu 10 ký tự.' },
                        { max: 500, message: 'Lý do tối đa 500 ký tự.' },
                      ]}
                    >
                      <Input.TextArea
                        rows={4}
                        placeholder="Mô tả ngắn gọn lý do và kế hoạch bàn giao công việc."
                        maxLength={500}
                        showCount
                      />
                    </Form.Item>
                    <Alert
                      type="info"
                      showIcon
                      icon={<FileTextOutlined />}
                      title="Quy định gửi đơn"
                      description={
                        <span>
                          Đơn nghỉ cần gửi trước ít nhất 03 ngày làm việc để quản lý
                          sắp xếp công việc. Xem{' '}
                          <Link to="/chat?q=Nh%C3%A2n%20vi%C3%AAn%20%C4%91%C6%B0%E1%BB%A3c%20ngh%E1%BB%89%20ph%C3%A9p%20bao%20nhi%C3%AAu%20ng%C3%A0y%20m%E1%BB%97i%20n%C4%83m%3F">
                            chính sách nghỉ phép
                          </Link>
                          .
                        </span>
                      }
                    />
                    <div className="row mt-16">
                      <Button
                        type="primary"
                        htmlType="submit"
                        icon={<CheckCircleOutlined />}
                        loading={createMutation.isPending}
                        disabled={requestedDays <= 0}
                      >
                        Gửi đơn nghỉ
                      </Button>
                      <Button
                        onClick={() => {
                          form.resetFields()
                          setSearchParams({ tab: 'mine' }, { replace: true })
                        }}
                      >
                        Hủy
                      </Button>
                    </div>
                  </Form>
                </Panel>
                <Panel title="Bạn cần biết">
                  <div className="detail-list">
                    <div className="detail-row">
                      <span className="detail-row__label">Số dư</span>
                      <span className="detail-row__value">
                        {balance?.remaining ?? '—'} ngày phép còn lại
                      </span>
                    </div>
                    <div className="detail-row">
                      <span className="detail-row__label">Người duyệt</span>
                      <span className="detail-row__value">Quản lý trực tiếp</span>
                    </div>
                    <div className="detail-row">
                      <span className="detail-row__label">Thông báo</span>
                      <span className="detail-row__value">
                        Kết quả duyệt xuất hiện trong mục thông báo.
                      </span>
                    </div>
                  </div>
                  <div className="step-note">
                    Đơn đang chờ duyệt có thể được hủy từ tab “Đơn của tôi”.
                  </div>
                </Panel>
              </div>
            ),
          },
        ]}
      />
    </div>
  )
}
