import { useEffect, useState } from 'react'
import { CloseOutlined, FilePdfOutlined, PlusOutlined } from '@ant-design/icons'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { useAuth } from '@/auth/AuthContext'
import { DOCUMENT_CATEGORIES, ROLE_LABELS } from '@/lib/constants'
import { CHAT_SUGGESTIONS, SEARCH_SUGGESTIONS, getShellMeta } from '@/components/layout/navConfig'
import type { WorkspaceCounts } from '@/components/layout/useWorkspaceCounts'
import { DocumentPdfModal, type PdfTarget } from '@/components/documents/DocumentPdfModal'

/** Verified: answered by Chính sách an ninh thông tin, page 18 (VPN + MFA). */
const VPN_QUESTION = 'Kết nối từ Internet vào mạng nội bộ Công ty phải dùng gì?'

interface ContextLink {
  key?: string
  label: string
  /** Second line under the label, e.g. the document that answers a question. */
  sub?: string
  to: string
  count?: number
  active?: boolean
  onClick?: (e: React.MouseEvent) => void
  icon?: React.ReactNode
}

interface ContextGroup {
  title: string
  links: ContextLink[]
  /** Shown instead of links while the group has nothing to list. */
  empty?: string
}

const isLink = (item: ContextLink | null): item is ContextLink => item !== null

const fold = (text: string) =>
  text
    .normalize('NFD')
    .replace(/[̀-ͯ]/g, '')
    .replace(/đ/g, 'd')
    .replace(/Đ/g, 'D')
    .toLowerCase()

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
  const navigate = useNavigate()
  const { pathname, search } = useLocation()
  const params = new URLSearchParams(search)
  const role = session?.role
  const shellMeta = getShellMeta(pathname)
  const groups: ContextGroup[] = []
  const [pdfTarget, setPdfTarget] = useState<PdfTarget | null>(null)

  // ChatPage owns which conversation is open; it broadcasts whether the
  // "new chat" view is showing so this list never guesses or lags behind.
  const [chatIsNew, setChatIsNew] = useState(true)

  useEffect(() => {
    const handleActiveChange = (event: Event) => {
      const detail = (event as CustomEvent<{ key?: string }>).detail
      setChatIsNew(detail?.key === 'new-chat')
    }
    window.addEventListener('app:chat-active', handleActiveChange)
    return () => window.removeEventListener('app:chat-active', handleActiveChange)
  }, [])

  const link = (
    label: string,
    to: string,
    active = false,
    count?: number,
    key?: string,
  ): ContextLink => ({
    key: key ?? `${to}-${label}`,
    label,
    to,
    active,
    count,
  })

  /** Link to a real document found by title; null while it is not in the store. */
  const docLink = (label: string, titleIncludes: string): ContextLink | null => {
    const match = counts.ingestedDocuments.find((item) =>
      fold(item.title).includes(fold(titleIncludes)),
    )
    return match ? link(label, `/documents/${match.id}`) : null
  }

  if (pathname === '/chat') {
    groups.push({
      title: 'Tác vụ',
      links: [
        {
          key: 'new-chat',
          label: 'Cuộc trò chuyện mới',
          to: '/chat',
          icon: <PlusOutlined />,
          active: chatIsNew,
          onClick: (e) => {
            e.preventDefault()
            window.dispatchEvent(new CustomEvent('app:new-chat'))
            onNavigate()
          },
        },
      ],
    })
    groups.push({
      title: 'Câu hỏi gợi ý',
      links: CHAT_SUGGESTIONS.map((suggestion) => ({
        key: `suggestion-${suggestion.label}`,
        label: suggestion.label,
        sub: suggestion.source,
        to: `/chat?q=${encodeURIComponent(suggestion.question)}`,
        onClick: (e: React.MouseEvent) => {
          e.preventDefault()
          window.dispatchEvent(
            new CustomEvent('app:chat-prompt', { detail: suggestion.question }),
          )
          onNavigate()
        },
      })),
    })
    groups.push({
      title: 'Tài liệu đã nạp',
      empty: 'Chưa có tài liệu nào sẵn sàng.',
      links: counts.ingestedDocuments.map((document) => ({
        key: `doc-${document.id}`,
        label: document.title,
        to: `/documents/${document.id}`,
        icon: <FilePdfOutlined />,
        onClick: (e: React.MouseEvent) => {
          e.preventDefault()
          setPdfTarget(document)
          onNavigate()
        },
      })),
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
        docLink('Điều lệ công ty', 'điều lệ công ty'),
        docLink('Thỏa ước lao động tập thể', 'thỏa ước lao động'),
      ].filter(isLink),
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
      title: 'Không gian làm việc',
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
      links: [docLink('Thỏa ước lao động tập thể', 'thỏa ước lao động')].filter(isLink),
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
      links: [docLink('Thỏa ước lao động tập thể', 'thỏa ước lao động')].filter(isLink),
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
          link('Kết nối VPN từ bên ngoài', `/chat?q=${encodeURIComponent(VPN_QUESTION)}`),
          docLink('Chính sách an ninh thông tin', 'an ninh thông tin'),
        ].filter(isLink),
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
      links: [docLink('Chính sách an ninh thông tin', 'an ninh thông tin')].filter(isLink),
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
    <aside
      className={`context-sidebar${open ? '' : ' context-sidebar--closed'}`}
      aria-label={`Điều hướng: ${shellMeta.title}`}
    >
      <div className="context-sidebar__head">
        <div className="context-sidebar__heading">
          <h2 className="context-sidebar__title">{shellMeta.title}</h2>
          <p className="context-sidebar__sub">{shellMeta.subtitle}</p>
        </div>
        <button
          type="button"
          className="context-close"
          onClick={onClose}
          aria-label="Đóng thanh điều hướng"
        >
          <CloseOutlined />
        </button>
      </div>
      <div className="context-sidebar__body">
        {groups.map((group) => (
          <section key={group.title} className="context-group">
            <h3 className="context-group__label">{group.title}</h3>
            {group.links.length === 0 && group.empty ? (
              <p className="context-group__empty">{group.empty}</p>
            ) : null}
            {group.links.map((item) => {
              const className = [
                'context-item',
                item.active ? 'context-item--active' : '',
                item.sub ? 'context-item--two-line' : '',
                item.key === 'new-chat' ? 'context-item--action' : '',
              ]
                .filter(Boolean)
                .join(' ')
              return (
                <Link
                  key={item.key ?? `${group.title}-${item.to}-${item.label}`}
                  to={item.to}
                  className={className}
                  aria-current={item.active ? 'page' : undefined}
                  title={item.sub ? `${item.label} — ${item.sub}` : item.label}
                  onClick={(e) => {
                    if (item.onClick) {
                      item.onClick(e)
                    } else {
                      onNavigate()
                    }
                  }}
                >
                  {item.icon ? (
                    <span className="context-item__icon" aria-hidden="true">
                      {item.icon}
                    </span>
                  ) : null}
                  {item.sub ? (
                    <span className="context-item__text">
                      <span className="context-item__label">{item.label}</span>
                      <span className="context-item__sub">{item.sub}</span>
                    </span>
                  ) : (
                    <span className="context-item__label">{item.label}</span>
                  )}
                  {item.count !== undefined ? (
                    <span className="context-item__count">{item.count}</span>
                  ) : null}
                </Link>
              )
            })}
          </section>
        ))}
      </div>
      <DocumentPdfModal
        target={pdfTarget}
        onClose={() => setPdfTarget(null)}
        onAsk={(target) => {
          setPdfTarget(null)
          navigate(`/chat?draft=${encodeURIComponent(`Trong tài liệu “${target.title}”, `)}`)
        }}
      />
    </aside>
  )
}
