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

export const CHAT_SUGGESTIONS = [
  {
    label: 'Chính sách nghỉ phép năm',
    question: 'Nhân viên được nghỉ phép bao nhiêu ngày mỗi năm?',
  },
  {
    label: 'Thời giờ làm việc & ca kíp',
    question: 'Thỏa ước lao động tập thể quy định thời giờ làm việc như thế nào?',
  },
  {
    label: 'Tiêu chí đánh giá nhà cung cấp',
    question: 'Quy trình đánh giá nhà cung cấp gồm những tiêu chí nào?',
  },
  {
    label: 'Quy định bảo mật mật khẩu',
    question: 'Chính sách an ninh thông tin quy định mật khẩu như thế nào?',
  },
  {
    label: 'Số lượng thành viên HĐQT',
    question: 'Công ty có bao nhiêu thành viên Hội đồng Quản trị?',
  },
  {
    label: 'Số cuộc họp HĐQT mỗi năm',
    question: 'Hội đồng Quản trị có bao nhiêu cuộc họp mỗi năm?',
  },
]

export const SEARCH_SUGGESTIONS = [
  'nghỉ phép năm',
  'thời gian thử việc',
  'làm việc từ xa VPN',
  'mật khẩu an toàn thông tin',
  'kỷ luật lao động',
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
