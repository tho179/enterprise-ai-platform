import { CloseOutlined } from '@ant-design/icons'
import { Link, useLocation } from 'react-router-dom'
import { useAuth } from '@/auth/AuthContext'
import { DOCUMENT_CATEGORIES, ROLE_LABELS } from '@/lib/constants'
import { CHAT_SUGGESTIONS, SEARCH_SUGGESTIONS, getShellMeta } from '@/components/layout/navConfig'
import type { WorkspaceCounts } from '@/components/layout/useWorkspaceCounts'

interface ContextLink {
  label: string
  to: string
  count?: number
  active?: boolean
}

interface ContextGroup {
  title: string
  links: ContextLink[]
}

export function ContextSidebar({
  open,
  counts,
  onNavigate,
  onClose,
}: {
  open: boolean
  counts: WorkspaceCounts
  onNavigate: () => void
  onClose: () => void
}) {
  const { session } = useAuth()
  const { pathname, search } = useLocation()
  const params = new URLSearchParams(search)
  const role = session?.role
  const shellMeta = getShellMeta(pathname)
  const groups: ContextGroup[] = []

  const link = (label: string, to: string, active = false, count?: number): ContextLink => ({
    label,
    to,
    active,
    count,
  })

  if (pathname === '/chat') {
    const q = params.get('q') ?? ''
    groups.push({
      title: 'Trợ lý AI',
      links: [
        link('Cuộc trò chuyện mới', '/chat', q === ''),
        link('Tìm kiếm tri thức', '/search'),
      ],
    })
    groups.push({
      title: 'Câu hỏi gợi ý',
      links: CHAT_SUGGESTIONS.map((suggestion) =>
        link(
          suggestion.label,
          `/chat?q=${encodeURIComponent(suggestion.question)}`,
          q === suggestion.question,
        ),
      ),
    })
    groups.push({
      title: 'Tài liệu tham khảo',
      links: [
        link('Nội quy Lao động 2026', '/documents/doc-nqld'),
        link('Chính sách An toàn thông tin', '/documents/doc-csit'),
      ],
    })
  } else if (pathname === '/search') {
    const q = params.get('q') ?? ''
    groups.push({
      title: 'Tìm kiếm',
      links: [
        link('Tìm kiếm ngữ nghĩa', '/search', q === ''),
        link('Hỏi trợ lý AI', '/chat'),
      ],
    })
    groups.push({
      title: 'Từ khóa gợi ý',
      links: SEARCH_SUGGESTIONS.map((term) =>
        link(term, `/search?q=${encodeURIComponent(term)}`, q === term),
      ),
    })
    groups.push({
      title: 'Tài liệu tham khảo',
      links: [
        link('Nội quy Lao động 2026', '/documents/doc-nqld'),
        link('Điều lệ Công ty 2021', '/documents/doc-dlct'),
      ],
    })
  } else if (pathname.startsWith('/documents')) {
    const category = params.get('category')
    const status = params.get('status')
    const overview = [
      link(
        'Tất cả tài liệu',
        '/documents',
        pathname === '/documents' && !category && !status,
        counts.documents,
      ),
      link(
        'Đang xử lý',
        '/documents?status=PROCESSING',
        pathname === '/documents' && status === 'PROCESSING',
      ),
      link(
        'Nạp lỗi',
        '/documents?status=FAILED',
        pathname === '/documents' && status === 'FAILED',
        counts.failedDocuments,
      ),
      link('Hỏi trợ lý AI', '/chat'),
    ]
    if (role === 'ADMIN') {
      overview.splice(3, 0, link('Tải tài liệu mới', '/documents/upload', pathname === '/documents/upload'))
    }
    groups.push({ title: 'Kho tri thức', links: overview })
    groups.push({
      title: 'Danh mục',
      links: DOCUMENT_CATEGORIES.map((item) =>
        link(
          item,
          `/documents?category=${encodeURIComponent(item)}`,
          pathname === '/documents' && category === item,
          counts.categories[item] ?? 0,
        ),
      ),
    })
    groups.push({
      title: 'Tìm kiếm',
      links: [link('Tìm trong kho', '/search'), link('Hỏi đáp có trích dẫn', '/chat')],
    })
  } else if (pathname === '/dashboard') {
    groups.push({
      title: 'Tổng quan',
      links: [
        link('Bảng điều khiển', '/dashboard', true),
        link('Trợ lý AI', '/chat'),
        link('Tìm kiếm tri thức', '/search'),
        link('Kho tài liệu', '/documents', false, counts.documents),
      ],
    })
    const shortcuts: ContextLink[] = []
    if (role === 'MANAGER') {
      shortcuts.push(
        link('Đơn chờ duyệt', '/approvals', false, counts.pendingApprovals),
      )
    }
    if (role === 'IT_SUPPORT') {
      shortcuts.push(link('Hàng đợi IT', '/tickets/queue', false, counts.queueOpen))
    }
    if (role === 'ADMIN' && counts.failedDocuments > 0) {
      shortcuts.push(
        link('Tài liệu nạp lỗi', '/documents?status=FAILED', false, counts.failedDocuments),
      )
    }
    shortcuts.push(link('Đơn nghỉ của tôi', '/leave?tab=mine'))
    shortcuts.push(link('Tạo yêu cầu IT', '/tickets?tab=new'))
    groups.push({ title: 'Lối tắt', links: shortcuts })
  } else if (pathname === '/leave') {
    const tab = params.get('tab') ?? 'mine'
    groups.push({
      title: 'Nghỉ phép',
      links: [
        link('Đơn của tôi', '/leave?tab=mine', tab === 'mine'),
        link('Tạo đơn nghỉ', '/leave?tab=new', tab === 'new'),
      ],
    })
    groups.push({
      title: 'Quy định liên quan',
      links: [
        link(
          'Chính sách nghỉ phép năm',
          '/chat?q=Nh%C3%A2n%20vi%C3%AAn%20%C4%91%C6%B0%E1%BB%A3c%20ngh%E1%BB%89%20ph%C3%A9p%20bao%20nhi%C3%AAu%20ng%C3%A0y%20m%E1%BB%97i%20n%C4%83m%3F',
        ),
        link('Nội quy Lao động 2026', '/documents/doc-nqld'),
      ],
    })
    if (role === 'MANAGER') {
      groups.push({
        title: 'Quản lý',
        links: [link('Duyệt đơn nghỉ', '/approvals', false, counts.pendingApprovals)],
      })
    }
  } else if (pathname === '/approvals') {
    groups.push({
      title: 'Phê duyệt',
      links: [
        link('Đơn chờ duyệt', '/approvals', true, counts.pendingApprovals),
        link('Đơn nghỉ của tôi', '/leave?tab=mine'),
        link('Tất cả đơn nghỉ', '/leave?tab=mine'),
      ],
    })
    groups.push({
      title: 'Quy định liên quan',
      links: [
        link(
          'Chính sách nghỉ phép năm',
          '/chat?q=Nh%C3%A2n%20vi%C3%AAn%20%C4%91%C6%B0%E1%BB%A3c%20ngh%E1%BB%89%20ph%C3%A9p%20bao%20nhi%C3%AAu%20ng%C3%A0y%20m%E1%BB%97i%20n%C4%83m%3F',
        ),
        link('Nội quy Lao động 2026', '/documents/doc-nqld'),
      ],
    })
  } else if (pathname === '/tickets' || pathname === '/tickets/queue') {
    const tab = params.get('tab') ?? 'mine'
    const status = params.get('status')
    if (pathname === '/tickets') {
      groups.push({
        title: 'Yêu cầu IT',
        links: [
          link('Yêu cầu của tôi', '/tickets', tab !== 'new'),
          link('Tạo yêu cầu', '/tickets?tab=new', tab === 'new'),
        ],
      })
      if (role === 'IT_SUPPORT') {
        groups.push({
          title: 'Dành cho IT',
          links: [link('Hàng đợi IT', '/tickets/queue', false, counts.queueOpen)],
        })
      }
      groups.push({
        title: 'Hướng dẫn',
        links: [
          link(
            'Kết nối VPN nội bộ',
            '/chat?q=Quy%20%C4%91%E1%BB%8Bnh%20l%C3%A0m%20vi%E1%BB%87c%20t%E1%BB%AB%20xa%20v%C3%A0%20k%E1%BA%BFt%20n%E1%BB%91i%20VPN%20nh%C6%B0%20th%E1%BA%BF%20n%C3%A0o%3F',
          ),
          link('Chính sách An toàn thông tin', '/documents/doc-csit'),
        ],
      })
    } else {
      groups.push({
        title: 'Hàng đợi',
        links: [
          link('Đang mở', '/tickets/queue', !status, counts.queueOpen),
          link('Mới', '/tickets/queue?status=OPEN', status === 'OPEN'),
          link('Đang xử lý', '/tickets/queue?status=IN_PROGRESS', status === 'IN_PROGRESS'),
          link('Mở lại', '/tickets/queue?status=REOPENED', status === 'REOPENED'),
          link('Đã xử lý', '/tickets/queue?status=RESOLVED', status === 'RESOLVED'),
          link('Đã đóng', '/tickets/queue?status=CLOSED', status === 'CLOSED'),
        ],
      })
      groups.push({
        title: 'Liên kết',
        links: [
          link('Yêu cầu của tôi', '/tickets'),
          link('Kho tài liệu', '/documents'),
        ],
      })
    }
  } else if (pathname === '/users') {
    const roleFilter = params.get('role')
    groups.push({
      title: 'Người dùng',
      links: [
        link('Tất cả người dùng', '/users', !roleFilter && params.get('new') !== '1'),
        link('Thêm người dùng', '/users?new=1', params.get('new') === '1'),
      ],
    })
    groups.push({
      title: 'Theo vai trò',
      links: (['EMPLOYEE', 'MANAGER', 'IT_SUPPORT', 'ADMIN'] as const).map((item) =>
        link(
          ROLE_LABELS[item],
          `/users?role=${item}`,
          roleFilter === item,
        ),
      ),
    })
    groups.push({
      title: 'Bảo mật',
      links: [link('Chính sách An toàn thông tin', '/documents/doc-csit')],
    })
  } else {
    groups.push({
      title: 'Điều hướng',
      links: [
        link('Tổng quan', '/dashboard'),
        link('Trợ lý AI', '/chat'),
        link('Kho tài liệu', '/documents'),
      ],
    })
  }

  return (
    <aside className={`context-sidebar${open ? '' : ' context-sidebar--closed'}`}>
      <div className="context-sidebar__head">
        <h2 className="context-sidebar__title">{shellMeta.title}</h2>
        <button
          type="button"
          className="context-close"
          onClick={onClose}
          aria-label="Đóng thanh điều hướng"
        >
          <CloseOutlined />
        </button>
      </div>
      {groups.map((group) => (
        <div key={group.title} className="context-group">
          {group.title.trim().toLowerCase() !== shellMeta.title.trim().toLowerCase() ? (
            <div className="context-group__label">{group.title}</div>
          ) : null}
          {group.links.map((item) => (
            <Link
              key={`${group.title}-${item.to}-${item.label}`}
              to={item.to}
              className={`context-item${item.active ? ' context-item--active' : ''}`}
              onClick={onNavigate}
            >
              <span>{item.label}</span>
              {item.count !== undefined ? (
                <span className="context-item__count">{item.count}</span>
              ) : null}
            </Link>
          ))}
        </div>
      ))}
    </aside>
  )
}
