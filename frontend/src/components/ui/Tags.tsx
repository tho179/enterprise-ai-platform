import { Tag } from 'antd'
import type { Role, TicketPriority } from '@/api/types'
import {
  ROLE_LABELS,
  STATUS_LABELS,
  TICKET_PRIORITY_LABELS,
} from '@/lib/constants'

const STATUS_COLORS: Record<string, string> = {
  UPLOADED: 'default',
  PROCESSING: 'processing',
  INGESTED: 'success',
  FAILED: 'error',
  PENDING: 'warning',
  APPROVED: 'success',
  REJECTED: 'error',
  CANCELLED: 'default',
  OPEN: 'blue',
  IN_PROGRESS: 'processing',
  RESOLVED: 'success',
  CLOSED: 'default',
  REOPENED: 'warning',
}

export function StatusTag({ status }: { status: string }) {
  return <Tag color={STATUS_COLORS[status] ?? 'default'}>{STATUS_LABELS[status] ?? status}</Tag>
}

const ROLE_COLORS: Record<Role, string> = {
  ADMIN: 'blue',
  MANAGER: 'gold',
  IT_SUPPORT: 'cyan',
  EMPLOYEE: 'default',
}

export function RoleTag({ role }: { role: Role }) {
  return <Tag color={ROLE_COLORS[role]}>{ROLE_LABELS[role]}</Tag>
}

const PRIORITY_COLORS: Record<TicketPriority, string> = {
  LOW: 'default',
  MEDIUM: 'blue',
  HIGH: 'orange',
  URGENT: 'red',
}

export function PriorityTag({ priority }: { priority: TicketPriority }) {
  return (
    <Tag color={PRIORITY_COLORS[priority]}>{TICKET_PRIORITY_LABELS[priority]}</Tag>
  )
}
