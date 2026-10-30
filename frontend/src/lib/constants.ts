import type { Role, TicketCategory, TicketPriority, TicketStatus } from '@/api/types'

export const DEMO_MODE = import.meta.env.VITE_USE_MOCKS === 'true'
export const AI_BASE = (import.meta.env.VITE_AI_BASE_URL as string | undefined) || '/ai-api'
export const MAX_UPLOAD_BYTES = 25 * 1024 * 1024

export const ROLE_LABELS: Record<Role, string> = {
  EMPLOYEE: 'Nhân viên',
  MANAGER: 'Quản lý',
  ADMIN: 'Quản trị viên',
  IT_SUPPORT: 'Hỗ trợ IT',
}

export const ROLE_DESCRIPTIONS: Record<Role, string> = {
  EMPLOYEE: 'Tra cứu tri thức, tạo đơn nghỉ phép và yêu cầu IT',
  MANAGER: 'Duyệt đơn nghỉ phép và theo dõi đội ngũ',
  ADMIN: 'Quản lý tài liệu, người dùng và cấu hình hệ thống',
  IT_SUPPORT: 'Tiếp nhận và xử lý yêu cầu hỗ trợ IT',
}

export const STATUS_LABELS: Record<string, string> = {
  UPLOADED: 'Đã tải lên',
  PROCESSING: 'Đang xử lý',
  INGESTED: 'Đã nạp',
  FAILED: 'Nạp lỗi',
  PENDING: 'Chờ duyệt',
  APPROVED: 'Đã duyệt',
  REJECTED: 'Từ chối',
  CANCELLED: 'Đã hủy',
  OPEN: 'Mới',
  IN_PROGRESS: 'Đang xử lý',
  RESOLVED: 'Đã xử lý',
  CLOSED: 'Đã đóng',
  REOPENED: 'Mở lại',
}

export const TICKET_CATEGORY_LABELS: Record<TicketCategory, string> = {
  NETWORK: 'Mạng',
  HARDWARE: 'Phần cứng',
  SOFTWARE: 'Phần mềm',
  ACCOUNT: 'Tài khoản',
  OTHER: 'Khác',
  UNCLASSIFIED: 'Chưa phân loại',
}

export const TICKET_PRIORITY_LABELS: Record<TicketPriority, string> = {
  LOW: 'Thấp',
  MEDIUM: 'Trung bình',
  HIGH: 'Cao',
  URGENT: 'Khẩn cấp',
}

export const TICKET_STATUS_LABELS: Record<TicketStatus, string> = {
  OPEN: 'Mới',
  IN_PROGRESS: 'Đang xử lý',
  RESOLVED: 'Đã xử lý',
  CLOSED: 'Đã đóng',
  REOPENED: 'Mở lại',
}

export const DOCUMENT_CATEGORIES = ['Nội quy', 'Quy chế', 'Chính sách IT', 'Hướng dẫn'] as const

export const TICKET_CATEGORIES: TicketCategory[] = [
  'NETWORK',
  'HARDWARE',
  'SOFTWARE',
  'ACCOUNT',
  'OTHER',
  'UNCLASSIFIED',
]

export const TICKET_PRIORITIES: TicketPriority[] = ['LOW', 'MEDIUM', 'HIGH', 'URGENT']

export function defaultRouteForRole(role: Role | undefined): string {
  switch (role) {
    case 'MANAGER':
      return '/approvals'
    case 'ADMIN':
      return '/documents'
    case 'IT_SUPPORT':
      return '/tickets/queue'
    default:
      return '/chat'
  }
}
