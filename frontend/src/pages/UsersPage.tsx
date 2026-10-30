import { useEffect, useMemo, useState } from 'react'
import {
  IdcardOutlined,
  LockOutlined,
  MoreOutlined,
  SearchOutlined,
  TeamOutlined,
  UnlockOutlined,
  UserAddOutlined,
} from '@ant-design/icons'
import {
  App as AntApp,
  Avatar,
  Badge,
  Button,
  Dropdown,
  Form,
  Input,
  Modal,
  Select,
  Table,
  Tag,
} from 'antd'
import type { MenuProps, TableProps } from 'antd'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useSearchParams } from 'react-router-dom'
import type { Role, User } from '@/api/types'
import { usersApi } from '@/api/users'
import { useAuth } from '@/auth/AuthContext'
import { KpiCard } from '@/components/ui/KpiCard'
import { PageHeader } from '@/components/ui/PageHeader'
import { EmptyState, ErrorState } from '@/components/ui/States'
import { RoleTag } from '@/components/ui/Tags'
import { ROLE_DESCRIPTIONS, ROLE_LABELS } from '@/lib/constants'
import { formatDate } from '@/lib/dates'
import { initials } from '@/lib/format'
import { usePageTitle } from '@/lib/usePageTitle'

interface CreateUserValues {
  fullName: string
  email: string
  password: string
  role: Role
}

const ASSIGNABLE_ROLES: Role[] = ['EMPLOYEE', 'MANAGER', 'IT_SUPPORT', 'ADMIN']

export function UsersPage() {
  usePageTitle('Người dùng')
  const { session } = useAuth()
  const { message } = AntApp.useApp()
  const queryClient = useQueryClient()
  const [searchParams, setSearchParams] = useSearchParams()
  const [createForm] = Form.useForm<CreateUserValues>()
  const selectedRole = Form.useWatch('role', createForm) ?? 'EMPLOYEE'
  const [createOpen, setCreateOpen] = useState(
    () => searchParams.get('new') === '1',
  )
  const [query, setQuery] = useState('')
  const roleFilter = searchParams.get('role') ?? ''

  useEffect(() => {
    if (searchParams.get('new') === '1') setCreateOpen(true)
  }, [searchParams])

  const usersQuery = useQuery({
    queryKey: ['users'],
    queryFn: usersApi.list,
  })

  const createMutation = useMutation({
    mutationFn: (values: CreateUserValues) => usersApi.create(values),
    onSuccess: (user) => {
      message.success(`Đã tạo tài khoản cho ${user.email}.`)
      setCreateOpen(false)
      createForm.resetFields()
      void queryClient.invalidateQueries({ queryKey: ['users'] })
      const next = new URLSearchParams(searchParams)
      next.delete('new')
      setSearchParams(next, { replace: true })
    },
    onError: (error) => message.error(error.message),
  })

  const roleMutation = useMutation({
    mutationFn: ({ id, role }: { id: string; role: Role }) =>
      usersApi.updateRole(id, role),
    onSuccess: (user) => {
      message.success(
        `Đã đổi vai trò của ${user.fullName} thành ${ROLE_LABELS[user.role]}.`,
      )
      void queryClient.invalidateQueries({ queryKey: ['users'] })
    },
    onError: (error) => message.error(error.message),
  })

  const statusMutation = useMutation({
    mutationFn: ({ id, active }: { id: string; active: boolean }) =>
      usersApi.setActive(id, active),
    onSuccess: (user) => {
      message.success(
        user.active
          ? `Đã mở khóa tài khoản ${user.email}.`
          : `Đã khóa tài khoản ${user.email}.`,
      )
      void queryClient.invalidateQueries({ queryKey: ['users'] })
    },
    onError: (error) => message.error(error.message),
  })

  const users = usersQuery.data ?? []
  const filtered = users.filter((user) => {
    const search = query.trim().toLowerCase()
    const matchesSearch =
      !search ||
      user.fullName.toLowerCase().includes(search) ||
      user.email.toLowerCase().includes(search)
    const matchesRole = !roleFilter || user.role === roleFilter
    return matchesSearch && matchesRole
  })

  const counts = useMemo(
    () => ({
      total: users.length,
      active: users.filter((user) => user.active).length,
      admins: users.filter((user) => user.role === 'ADMIN').length,
      it: users.filter((user) => user.role === 'IT_SUPPORT').length,
    }),
    [users],
  )

  const updateRoleFilter = (role: string) => {
    const next = new URLSearchParams(searchParams)
    if (role) next.set('role', role)
    else next.delete('role')
    setSearchParams(next, { replace: true })
  }

  const openCreate = () => {
    setCreateOpen(true)
    const next = new URLSearchParams(searchParams)
    next.set('new', '1')
    setSearchParams(next, { replace: true })
  }

  const closeCreate = () => {
    setCreateOpen(false)
    createForm.resetFields()
    const next = new URLSearchParams(searchParams)
    next.delete('new')
    setSearchParams(next, { replace: true })
  }

  const menuFor = (user: User): MenuProps => {
    const isSelf = user.id === session?.id
    return {
      items: [
        {
          key: 'roles',
          type: 'group',
          label: 'Vai trò',
          children: ASSIGNABLE_ROLES.map((role) => ({
            key: `role:${role}`,
            label: (
              <span className="row" style={{ justifyContent: 'space-between', gap: 18 }}>
                {ROLE_LABELS[role]}
                {user.role === role ? <Tag color="blue">Hiện tại</Tag> : null}
              </span>
            ),
            disabled: isSelf || user.role === role,
          })),
        },
        { type: 'divider' },
        {
          key: 'status',
          label: user.active ? 'Khóa tài khoản' : 'Mở khóa tài khoản',
          icon: user.active ? <LockOutlined /> : <UnlockOutlined />,
          danger: user.active,
          disabled: isSelf,
        },
      ],
      onClick: ({ key }) => {
        if (isSelf) {
          message.warning('Không thể thay đổi vai trò hoặc trạng thái của chính bạn.')
          return
        }
        if (key.startsWith('role:')) {
          const role = key.replace('role:', '') as Role
          roleMutation.mutate({ id: user.id, role })
          return
        }
        if (key === 'status') {
          statusMutation.mutate({ id: user.id, active: !user.active })
        }
      },
    }
  }

  const columns: TableProps<User>['columns'] = [
    {
      title: 'Người dùng',
      key: 'user',
      render: (_, user) => (
        <div className="row" style={{ gap: 10 }}>
          <Avatar style={{ background: 'var(--brand-50)', color: 'var(--brand-700)', fontWeight: 600 }}>
            {initials(user.fullName)}
          </Avatar>
          <div className="table-title-cell">
            <span className="table-title">
              {user.fullName}
              {user.id === session?.id ? (
                <Tag color="blue" style={{ marginLeft: 6 }}>
                  Bạn
                </Tag>
              ) : null}
            </span>
            <span className="table-sub">{user.email}</span>
            <span className="mobile-only" style={{ marginTop: 2 }}>
              <RoleTag role={user.role} />
            </span>
          </div>
        </div>
      ),
    },
    {
      title: 'Vai trò',
      dataIndex: 'role',
      key: 'role',
      width: 140,
      responsive: ['md'],
      render: (role: Role) => <RoleTag role={role} />,
    },
    {
      title: 'Trạng thái',
      key: 'status',
      width: 140,
      responsive: ['lg'],
      render: (_, user) => (
        <Badge
          status={user.active ? 'success' : 'default'}
          text={user.active ? 'Đang hoạt động' : 'Đã khóa'}
        />
      ),
    },
    {
      title: 'Ngày tạo',
      dataIndex: 'createdAt',
      key: 'createdAt',
      width: 130,
      responsive: ['xl'],
      render: (value: string) => formatDate(value),
    },
    {
      title: '',
      key: 'actions',
      width: 64,
      align: 'right',
      render: (_, user) => (
        <Dropdown
          menu={menuFor(user)}
          trigger={['click']}
          placement="bottomRight"
        >
          <Button
            type="text"
            icon={<MoreOutlined />}
            aria-label={`Thao tác với ${user.fullName}`}
          />
        </Dropdown>
      ),
    },
  ]

  const hasFilters = Boolean(query || roleFilter)

  return (
    <div>
      <PageHeader
        title="Người dùng"
        description="Quản lý tài khoản nội bộ, vai trò truy cập và trạng thái hoạt động."
        actions={
          <Button type="primary" icon={<UserAddOutlined />} onClick={openCreate}>
            Thêm người dùng
          </Button>
        }
      />

      <div className="kpi-grid">
        <KpiCard label="Tổng người dùng" value={counts.total} hint="Tất cả tài khoản" />
        <KpiCard label="Đang hoạt động" value={counts.active} hint="Có thể đăng nhập" />
        <KpiCard label="Quản trị viên" value={counts.admins} hint="Toàn quyền hệ thống" />
        <KpiCard label="Hỗ trợ IT" value={counts.it} hint="Xử lý yêu cầu kỹ thuật" />
      </div>

      <div className="toolbar">
        <Input
          prefix={<SearchOutlined />}
          placeholder="Tìm theo tên hoặc email"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          allowClear
          style={{ maxWidth: 330 }}
          aria-label="Tìm người dùng"
        />
        <Select
          allowClear
          placeholder="Vai trò"
          value={roleFilter || undefined}
          onChange={(value) => updateRoleFilter(value ?? '')}
          options={ASSIGNABLE_ROLES.map((role) => ({
            value: role,
            label: ROLE_LABELS[role],
          }))}
          style={{ minWidth: 170 }}
        />
        <div className="toolbar__right muted text-sm">
          {filtered.length} / {users.length} tài khoản
        </div>
      </div>

      {usersQuery.isError ? (
        <ErrorState
          message="Không tải được danh sách người dùng."
          onRetry={() => usersQuery.refetch()}
        />
      ) : (
        <div className="table-card">
          <Table<User>
            rowKey="id"
            columns={columns}
            dataSource={filtered}
            loading={usersQuery.isLoading}
            pagination={{ pageSize: 8, showSizeChanger: true }}
            locale={{
              emptyText: (
                <EmptyState
                  title="Không có người dùng phù hợp"
                  description="Thử thay đổi từ khóa hoặc bộ lọc vai trò."
                  action={
                    hasFilters ? (
                      <Button
                        onClick={() => {
                          setQuery('')
                          updateRoleFilter('')
                        }}
                      >
                        Xóa bộ lọc
                      </Button>
                    ) : null
                  }
                />
              ),
            }}
          />
        </div>
      )}

      <div className="docs-footnote">
        <IdcardOutlined /> Vai trò quyết định quyền truy cập tài liệu, phê duyệt và
        hàng đợi IT. Không thể tự khóa tài khoản đang đăng nhập.
      </div>

      <Modal
        title="Thêm người dùng"
        open={createOpen}
        onCancel={closeCreate}
        okText="Tạo tài khoản"
        cancelText="Hủy"
        confirmLoading={createMutation.isPending}
        onOk={() => createForm.submit()}
        destroyOnHidden
      >
        <Form
          form={createForm}
          layout="vertical"
          requiredMark={false}
          initialValues={{ role: 'EMPLOYEE' }}
          onFinish={(values) => createMutation.mutate(values)}
        >
          <Form.Item
            label="Họ và tên"
            name="fullName"
            rules={[
              { required: true, message: 'Vui lòng nhập họ tên.' },
              { min: 3, message: 'Họ tên tối thiểu 3 ký tự.' },
              { max: 100, message: 'Họ tên tối đa 100 ký tự.' },
            ]}
          >
            <Input placeholder="Nguyễn Văn A" />
          </Form.Item>
          <Form.Item
            label="Email"
            name="email"
            rules={[
              { required: true, message: 'Vui lòng nhập email.' },
              { type: 'email', message: 'Email không hợp lệ.' },
              {
                validator: async (_, value: string) => {
                  if (!value) return
                  const duplicated = users.some(
                    (user) => user.email.toLowerCase() === value.toLowerCase(),
                  )
                  if (duplicated) throw new Error('Email đã được sử dụng.')
                },
              },
            ]}
          >
            <Input placeholder="nhanvien@congty.vn" />
          </Form.Item>
          <Form.Item
            label="Mật khẩu ban đầu"
            name="password"
            rules={[
              { required: true, message: 'Vui lòng nhập mật khẩu.' },
              { min: 8, message: 'Mật khẩu tối thiểu 8 ký tự.' },
              {
                pattern: /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d).+$/,
                message: 'Cần có chữ hoa, chữ thường và số.',
              },
            ]}
          >
            <Input.Password placeholder="Ví dụ: Demo@123" />
          </Form.Item>
          <Form.Item
            label="Vai trò"
            name="role"
            rules={[{ required: true, message: 'Chọn vai trò.' }]}
            extra={
              <span className="muted text-sm">
                {ROLE_DESCRIPTIONS[selectedRole]}
              </span>
            }
          >
            <Select
              options={ASSIGNABLE_ROLES.map((role) => ({
                value: role,
                label: ROLE_LABELS[role],
              }))}
            />
          </Form.Item>
          <div className="role-hint">
            <TeamOutlined />
            <span>
              {ROLE_DESCRIPTIONS.EMPLOYEE} · {ROLE_DESCRIPTIONS.MANAGER} ·{' '}
              {ROLE_DESCRIPTIONS.IT_SUPPORT} · {ROLE_DESCRIPTIONS.ADMIN}
            </span>
          </div>
        </Form>
      </Modal>
    </div>
  )
}
