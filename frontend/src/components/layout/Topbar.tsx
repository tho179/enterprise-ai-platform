import { useState } from 'react'
import {
  AppstoreOutlined,
  BellOutlined,
  LogoutOutlined,
  MenuOutlined,
  SearchOutlined,
} from '@ant-design/icons'
import { Avatar, Badge, Button, Empty, Input, Popover, Spin, Tag, Tooltip } from 'antd'
import type { MenuProps } from 'antd'
import { Dropdown } from 'antd'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { useLocation, useNavigate } from 'react-router-dom'
import { notificationsApi } from '@/api/notifications'
import { useAuth } from '@/auth/AuthContext'
import { DEMO_MODE, ROLE_LABELS } from '@/lib/constants'
import { formatRelative } from '@/lib/dates'
import { initials } from '@/lib/format'
import { getShellMeta } from '@/components/layout/navConfig'

export function Topbar({ onToggleSidebar }: { onToggleSidebar: () => void }) {
  const { session, logout } = useAuth()
  const navigate = useNavigate()
  const { pathname } = useLocation()
  const queryClient = useQueryClient()
  const [query, setQuery] = useState('')
  const [notifOpen, setNotifOpen] = useState(false)

  const notificationsQuery = useQuery({
    queryKey: ['notifications'],
    queryFn: notificationsApi.list,
    enabled: session !== null,
  })

  if (!session) return null

  const unread = notificationsQuery.data?.filter((item) => !item.read).length ?? 0
  const meta = getShellMeta(pathname)

  const openNotification = (id: string, href?: string) => {
    void notificationsApi.markRead(id).then(() => {
      void queryClient.invalidateQueries({ queryKey: ['notifications'] })
    })
    if (href) {
      setNotifOpen(false)
      navigate(href)
    }
  }

  const markAllRead = () => {
    void notificationsApi.markAllRead().then(() => {
      void queryClient.invalidateQueries({ queryKey: ['notifications'] })
    })
  }

  const userMenu: MenuProps['items'] = [
    {
      key: 'profile',
      disabled: true,
      label: (
        <div style={{ padding: '2px 0', minWidth: 190 }}>
          <div style={{ color: 'var(--text)', fontWeight: 600 }}>{session.fullName}</div>
          <div style={{ color: 'var(--muted)', fontSize: 12 }}>{session.email}</div>
          <Tag color="blue" style={{ marginTop: 6 }}>
            {ROLE_LABELS[session.role]}
          </Tag>
        </div>
      ),
    },
    { type: 'divider' },
    { key: 'dashboard', label: 'Tổng quan', icon: <AppstoreOutlined /> },
    { type: 'divider' },
    { key: 'logout', label: 'Đăng xuất', icon: <LogoutOutlined />, danger: true },
  ]

  const notificationContent = (
    <div className="notif-panel">
      <div className="notif-panel__head">
        <div>
          <div className="notif-panel__title">Thông báo</div>
          <div className="text-sm muted">{unread} chưa đọc</div>
        </div>
        <Button type="link" size="small" disabled={unread === 0} onClick={markAllRead}>
          Đánh dấu tất cả
        </Button>
      </div>
      <div className="notif-panel__list">
        {notificationsQuery.isLoading ? (
          <div style={{ padding: 24, textAlign: 'center' }}>
            <Spin size="small" />
          </div>
        ) : notificationsQuery.data && notificationsQuery.data.length > 0 ? (
          notificationsQuery.data.map((item) => (
            <button
              key={item.id}
              type="button"
              className={`notif-item${item.read ? '' : ' notif-item--unread'}`}
              onClick={() => openNotification(item.id, item.href)}
            >
              <span className="notif-item__dot" />
              <span className="notif-item__body">
                <span className="notif-item__title">{item.title}</span>
                <span className="notif-item__text">{item.body}</span>
                <span className="notif-item__time">{formatRelative(item.createdAt)}</span>
              </span>
            </button>
          ))
        ) : (
          <Empty
            image={Empty.PRESENTED_IMAGE_SIMPLE}
            description="Không có thông báo mới"
            style={{ padding: '18px 0' }}
          />
        )}
      </div>
    </div>
  )

  return (
    <header className="topbar">
      <button
        type="button"
        className="topbar__icon-btn sidebar-toggle"
        onClick={onToggleSidebar}
        aria-label="Mở thanh điều hướng"
      >
        <MenuOutlined />
      </button>
      <div className="topbar__left">
        <span className="topbar__brand">EAKWP</span>
        <span className="topbar__sep">/</span>
        <h1 className="topbar__title">{meta.title}</h1>
        <span className="topbar__sep hide-tablet">/</span>
        <span className="topbar__sub hide-tablet">{meta.subtitle}</span>
      </div>
      <div className="topbar__actions">
        <Input
          className="topbar__search hide-tablet"
          placeholder="Tìm tài liệu, câu hỏi…"
          prefix={<SearchOutlined />}
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          onPressEnter={() => {
            const value = query.trim()
            if (!value) return
            navigate(`/search?q=${encodeURIComponent(value)}`)
            setQuery('')
          }}
          allowClear
          aria-label="Tìm kiếm nhanh"
        />
        {DEMO_MODE ? (
          <Tooltip title="Một số phân hệ dùng dữ liệu mô phỏng (MSW).">
            <Tag color="gold" className="hide-tablet" style={{ margin: 0 }}>
              Demo
            </Tag>
          </Tooltip>
        ) : null}
        <Popover
          content={notificationContent}
          trigger="click"
          placement="bottomRight"
          arrow={false}
          open={notifOpen}
          onOpenChange={setNotifOpen}
          styles={{ content: { padding: 0 } }}
        >
          <button type="button" className="topbar__icon-btn" aria-label="Thông báo">
            <Badge count={unread} size="small" offset={[-2, 2]}>
              <BellOutlined />
            </Badge>
          </button>
        </Popover>
        <Dropdown
          menu={{
            items: userMenu,
            onClick: ({ key }) => {
              if (key === 'logout') {
                logout()
                navigate('/login', { replace: true })
              }
              if (key === 'dashboard') navigate('/dashboard')
            },
          }}
          trigger={['click']}
          placement="bottomRight"
        >
          <button type="button" className="topbar__user">
            <Avatar
              size={30}
              style={{ background: 'var(--brand-700)', fontSize: 11, fontWeight: 600 }}
            >
              {initials(session.fullName)}
            </Avatar>
            <span className="topbar__user-meta">
              <span className="topbar__user-name">{session.fullName}</span>
              <span className="topbar__user-role">{ROLE_LABELS[session.role]}</span>
            </span>
          </button>
        </Dropdown>
      </div>
    </header>
  )
}
