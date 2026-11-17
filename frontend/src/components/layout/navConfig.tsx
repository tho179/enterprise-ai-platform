import {
  AppstoreOutlined,
  CalendarOutlined,
  CheckSquareOutlined,
  CustomerServiceOutlined,
  FileTextOutlined,
  MessageOutlined,
  SearchOutlined,
  TeamOutlined,
  ToolOutlined,
} from '@ant-design/icons'
import type { ReactNode } from 'react'
import type { Role } from '@/api/types'

export interface RailItem {
  key: string
  label: string
  to: string
  icon: ReactNode
  roles?: Role[]
  /** Runs on browser mock data only; the backend has no such module yet. */
  demoOnly?: boolean
}

export const RAIL_ITEMS: RailItem[] = [
  { key: 'dashboard', label: 'Tổng quan', to: '/dashboard', icon: <AppstoreOutlined /> },
  { key: 'chat', label: 'Trợ lý AI', to: '/chat', icon: <MessageOutlined /> },
  { key: 'search', label: 'Tìm kiếm tri thức', to: '/search', icon: <SearchOutlined /> },
  { key: 'documents', label: 'Kho tài liệu', to: '/documents', icon: <FileTextOutlined /> },
  {
    key: 'leave',
    label: 'Nghỉ phép',
    to: '/leave',
    icon: <CalendarOutlined />,
    roles: ['EMPLOYEE', 'MANAGER'],
    demoOnly: true,
  },
  {
    key: 'approvals',
    label: 'Phê duyệt',
    to: '/approvals',
    icon: <CheckSquareOutlined />,
    roles: ['MANAGER'],
    demoOnly: true,
  },
  {
    key: 'tickets',
    label: 'Yêu cầu IT',
    to: '/tickets',
    icon: <CustomerServiceOutlined />,
    demoOnly: true,
  },
  {
    key: 'queue',
    label: 'Hàng đợi IT',
    to: '/tickets/queue',
    icon: <ToolOutlined />,
    roles: ['IT_SUPPORT'],
    demoOnly: true,
  },
  {
    key: 'users',
    label: 'Người dùng',
    to: '/users',
    icon: <TeamOutlined />,
    roles: ['ADMIN'],
  },
]

export function isRailItemActive(pathname: string, to: string): boolean {
  if (to === '/tickets') return pathname === '/tickets'
  return pathname === to || pathname.startsWith(`${to}/`)
}

export interface ChatSuggestion {
  label: string
  question: string
  /** Document that holds the answer, shown under the label. */
  source: string
}

/**
 * Each question was checked against the live knowledge base (Nov 2026): the
 * answer is stated in the cited document and every citation opens its PDF.
 * Re-check when the document set changes.
 */
export const CHAT_SUGGESTIONS: ChatSuggestion[] = [
  {
    label: 'Thời hạn của thỏa ước lao động',
    question: 'Thỏa ước lao động tập thể có hiệu lực trong bao lâu?',
    source: 'Thỏa ước lao động tập thể',
  },
  {
    label: 'Xử lý khi bị lộ mật khẩu',
    question: 'Nhân viên phải làm gì khi bị lộ mật khẩu hoặc quyền truy cập?',
    source: 'Chính sách an ninh thông tin',
  },
  {
    label: 'Cách chọn nhà cung cấp mới',
    question: 'Nhà cung cấp mới được lựa chọn như thế nào sau khi đánh giá?',
    source: 'Quy trình đánh giá nhà cung cấp',
  },
  {
    label: 'Thành viên và nhiệm kỳ HĐQT',
    question: 'Hội đồng Quản trị có bao nhiêu thành viên và nhiệm kỳ bao lâu?',
    source: 'Điều lệ công ty - 2021',
  },
  {
    label: 'Tần suất họp HĐQT',
    question: 'Hội đồng Quản trị có bao nhiêu cuộc họp mỗi năm?',
    source: 'Quy chế hoạt động HĐQT',
  },
  {
    label: 'Cam kết về lao động cưỡng bức',
    question: 'Chính sách nhân quyền cam kết gì về lao động cưỡng bức và lao động trẻ em?',
    source: 'Chính sách nhân quyền',
  },
]

export const SEARCH_SUGGESTIONS = [
  'thời hạn thỏa ước lao động',
  'thời gian thử việc',
  'kỷ luật lao động',
  'mật khẩu',
  'VPN',
  'cổ tức',
]

export function getShellMeta(pathname: string): { title: string; subtitle: string } {
  if (pathname === '/dashboard') {
    return {
      title: 'Tổng quan',
      subtitle: 'Sức khỏe vận hành và các việc cần xử lý trong ngày',
    }
  }
  if (pathname === '/chat') {
    return {
      title: 'Trợ lý AI',
      subtitle: 'Hỏi đáp có trích dẫn từ kho tri thức nội bộ',
    }
  }
  if (pathname === '/search') {
    return {
      title: 'Tìm kiếm tri thức',
      subtitle: 'Tìm theo ngữ nghĩa trên toàn bộ tài liệu đã nạp',
    }
  }
  if (pathname === '/documents/upload') {
    return {
      title: 'Tải tài liệu',
      subtitle: 'Đưa tài liệu mới vào pipeline nạp tri thức',
    }
  }
  if (pathname.startsWith('/documents/')) {
    return {
      title: 'Chi tiết tài liệu',
      subtitle: 'Phiên bản, đoạn trích và trạng thái xử lý',
    }
  }
  if (pathname === '/documents') {
    return {
      title: 'Kho tài liệu',
      subtitle: 'Quản lý tài liệu, phiên bản và trạng thái nạp',
    }
  }
  if (pathname === '/leave') {
    return {
      title: 'Nghỉ phép',
      subtitle: 'Theo dõi số ngày phép và gửi đơn nghỉ',
    }
  }
  if (pathname === '/approvals') {
    return {
      title: 'Phê duyệt',
      subtitle: 'Xử lý đơn nghỉ phép đang chờ quản lý',
    }
  }
  if (pathname === '/tickets/queue') {
    return {
      title: 'Hàng đợi IT',
      subtitle: 'Tiếp nhận, phân loại và xử lý yêu cầu hỗ trợ',
    }
  }
  if (pathname === '/tickets') {
    return {
      title: 'Yêu cầu IT',
      subtitle: 'Gửi và theo dõi yêu cầu hỗ trợ kỹ thuật',
    }
  }
  if (pathname === '/users') {
    return {
      title: 'Người dùng',
      subtitle: 'Quản lý tài khoản, vai trò và trạng thái truy cập',
    }
  }
  return { title: 'EAKWP Console', subtitle: 'Nền tảng tri thức doanh nghiệp' }
}
