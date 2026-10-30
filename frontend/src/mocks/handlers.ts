import { HttpResponse, delay, http } from 'msw'
import type {
  AppNotification,
  Classification,
  LeaveRequest,
  Ticket,
  User,
} from '@/api/types'
import {
  demoLeaveRequests,
  demoNotifications,
  demoTickets,
  demoUsers,
} from '@/mocks/fixtures'
import { mockClassification, mockTicketSuggestion } from '@/mocks/chat-fallback'

let leaveRequests: LeaveRequest[] = JSON.parse(JSON.stringify(demoLeaveRequests)) as LeaveRequest[]
let tickets: Ticket[] = JSON.parse(JSON.stringify(demoTickets)) as Ticket[]
let notifications: AppNotification[] = JSON.parse(
  JSON.stringify(demoNotifications),
) as AppNotification[]
const users: User[] = JSON.parse(JSON.stringify(demoUsers)) as User[]

function currentUserId(request: Request): string {
  return request.headers.get('X-Demo-User') || 'u-emp-1'
}

function currentUserName(request: Request): string {
  const id = currentUserId(request)
  return users.find((user) => user.id === id)?.fullName ?? 'Nguyễn Văn A'
}

export const handlers = [
  http.get('/api/notifications', async () => {
    await delay(150)
    return HttpResponse.json(notifications)
  }),

  http.patch('/api/notifications/read-all', async () => {
    await delay(120)
    notifications = notifications.map((item) => ({ ...item, read: true }))
    return HttpResponse.json({ success: true })
  }),

  http.patch('/api/notifications/:id/read', async ({ params }) => {
    await delay(120)
    notifications = notifications.map((item) =>
      item.id === params.id ? { ...item, read: true } : item,
    )
    return HttpResponse.json({ success: true })
  }),

  http.get('/api/leave-requests/balance', async () => {
    await delay(120)
    return HttpResponse.json({ total: 12, used: 4, remaining: 8 })
  }),

  http.get('/api/leave-requests', async ({ request }) => {
    await delay(200)
    const url = new URL(request.url)
    const mine = url.searchParams.get('mine') === 'true'
    const status = url.searchParams.get('status')
    const userId = currentUserId(request)
    const data = leaveRequests
      .filter((item) => (mine ? item.userId === userId : true))
      .filter((item) => (status ? item.status === status : true))
      .sort((a, b) => b.createdAt.localeCompare(a.createdAt))
    return HttpResponse.json(data)
  }),

  http.post('/api/leave-requests', async ({ request }) => {
    await delay(300)
    const body = (await request.json()) as {
      startDate: string
      endDate: string
      totalDays: number
      reason: string
    }
    const userId = currentUserId(request)
    const requestItem: LeaveRequest = {
      id: `lv-${Date.now()}`,
      userId,
      employeeName: currentUserName(request),
      startDate: body.startDate,
      endDate: body.endDate,
      totalDays: body.totalDays,
      reason: body.reason,
      status: 'PENDING',
      createdAt: new Date().toISOString(),
    }
    leaveRequests = [requestItem, ...leaveRequests]
    return HttpResponse.json(requestItem, { status: 201 })
  }),

  http.patch('/api/leave-requests/:id/approve', async ({ params, request }) => {
    await delay(250)
    const body = (await request.json()) as { comment?: string }
    const item = leaveRequests.find((leave) => leave.id === params.id)
    if (!item) return HttpResponse.json({ message: 'Không tìm thấy đơn.' }, { status: 404 })
    if (item.status !== 'PENDING') {
      return HttpResponse.json(
        { code: 'LEAVE_STATE_CHANGED', message: 'Đơn đã thay đổi trạng thái, vui lòng tải lại.' },
        { status: 409 },
      )
    }
    item.status = 'APPROVED'
    item.approverName = currentUserName(request)
    item.comment = body.comment || ''
    item.decidedAt = new Date().toISOString()
    return HttpResponse.json(item)
  }),

  http.patch('/api/leave-requests/:id/reject', async ({ params, request }) => {
    await delay(250)
    const body = (await request.json()) as { comment?: string }
    const item = leaveRequests.find((leave) => leave.id === params.id)
    if (!item) return HttpResponse.json({ message: 'Không tìm thấy đơn.' }, { status: 404 })
    if (item.status !== 'PENDING') {
      return HttpResponse.json(
        { code: 'LEAVE_STATE_CHANGED', message: 'Đơn đã thay đổi trạng thái, vui lòng tải lại.' },
        { status: 409 },
      )
    }
    item.status = 'REJECTED'
    item.approverName = currentUserName(request)
    item.comment = body.comment || ''
    item.decidedAt = new Date().toISOString()
    return HttpResponse.json(item)
  }),

  http.patch('/api/leave-requests/:id/cancel', async ({ params }) => {
    await delay(200)
    const item = leaveRequests.find((leave) => leave.id === params.id)
    if (!item) return HttpResponse.json({ message: 'Không tìm thấy đơn.' }, { status: 404 })
    if (item.status !== 'PENDING') {
      return HttpResponse.json(
        { code: 'LEAVE_STATE_CHANGED', message: 'Chỉ có thể hủy đơn đang chờ duyệt.' },
        { status: 409 },
      )
    }
    item.status = 'CANCELLED'
    return HttpResponse.json(item)
  }),

  http.get('/api/it-requests', async ({ request }) => {
    await delay(200)
    const url = new URL(request.url)
    const mine = url.searchParams.get('mine') === 'true'
    const status = url.searchParams.get('status')
    const priority = url.searchParams.get('priority')
    const q = (url.searchParams.get('q') || '').toLowerCase()
    const userId = currentUserId(request)
    const data = tickets
      .filter((ticket) => (mine ? ticket.requesterId === userId : true))
      .filter((ticket) => (status ? ticket.status === status : true))
      .filter((ticket) => (priority ? ticket.priority === priority : true))
      .filter(
        (ticket) =>
          !q ||
          ticket.title.toLowerCase().includes(q) ||
          ticket.ticketCode.toLowerCase().includes(q),
      )
      .sort((a, b) => b.createdAt.localeCompare(a.createdAt))
    return HttpResponse.json(data)
  }),

  http.post('/api/it-requests/classify-preview', async ({ request }) => {
    await delay(650)
    const body = (await request.json()) as { title?: string; description?: string }
    const result: Classification = mockClassification(
      body.title || '',
      body.description || '',
    )
    return HttpResponse.json(result)
  }),

  http.post('/api/it-requests', async ({ request }) => {
    await delay(350)
    const body = (await request.json()) as {
      title: string
      description: string
      category: Ticket['category']
      priority: Ticket['priority']
      attachmentName?: string | null
      aiConfidence?: number | null
    }
    const next = tickets.length + 7
    const ticket: Ticket = {
      id: `it-${Date.now()}`,
      ticketCode: `IT-2026-${String(next).padStart(4, '0')}`,
      requesterId: currentUserId(request),
      requesterName: currentUserName(request),
      assigneeId: null,
      assigneeName: null,
      title: body.title,
      description: body.description,
      attachmentName: body.attachmentName || null,
      category: body.category,
      priority: body.priority,
      aiConfidence: body.aiConfidence ?? null,
      status: 'OPEN',
      createdAt: new Date().toISOString(),
    }
    tickets = [ticket, ...tickets]
    return HttpResponse.json(ticket, { status: 201 })
  }),

  http.patch('/api/it-requests/:id/assign', async ({ params, request }) => {
    await delay(250)
    const ticket = tickets.find((item) => item.id === params.id)
    if (!ticket) return HttpResponse.json({ message: 'Không tìm thấy ticket.' }, { status: 404 })
    if (ticket.status === 'CLOSED') {
      return HttpResponse.json({ code: 'TICKET_CLOSED', message: 'Ticket đã đóng.' }, { status: 409 })
    }
    if (ticket.assigneeId && ticket.assigneeId !== currentUserId(request)) {
      return HttpResponse.json(
        { code: 'TICKET_TAKEN', message: `Ticket đã được tiếp nhận bởi ${ticket.assigneeName}.` },
        { status: 409 },
      )
    }
    ticket.assigneeId = currentUserId(request)
    ticket.assigneeName = currentUserName(request)
    ticket.status = 'IN_PROGRESS'
    return HttpResponse.json(ticket)
  }),

  http.get('/api/it-requests/:id/suggestions', async ({ params }) => {
    await delay(900)
    const ticket = tickets.find((item) => item.id === params.id)
    if (!ticket) return HttpResponse.json({ message: 'Không tìm thấy ticket.' }, { status: 404 })
    return HttpResponse.json(mockTicketSuggestion())
  }),

  http.patch('/api/it-requests/:id/resolve', async ({ params, request }) => {
    await delay(300)
    const body = (await request.json()) as { resolutionNote?: string }
    const ticket = tickets.find((item) => item.id === params.id)
    if (!ticket) return HttpResponse.json({ message: 'Không tìm thấy ticket.' }, { status: 404 })
    if (ticket.status === 'CLOSED') {
      return HttpResponse.json({ code: 'TICKET_CLOSED', message: 'Ticket đã đóng.' }, { status: 409 })
    }
    ticket.status = 'RESOLVED'
    ticket.resolutionNote = body.resolutionNote || ''
    ticket.resolvedAt = new Date().toISOString()
    return HttpResponse.json(ticket)
  }),

  http.patch('/api/it-requests/:id/close', async ({ params }) => {
    await delay(200)
    const ticket = tickets.find((item) => item.id === params.id)
    if (!ticket) return HttpResponse.json({ message: 'Không tìm thấy ticket.' }, { status: 404 })
    ticket.status = 'CLOSED'
    return HttpResponse.json(ticket)
  }),

  http.patch('/api/it-requests/:id/reopen', async ({ params }) => {
    await delay(200)
    const ticket = tickets.find((item) => item.id === params.id)
    if (!ticket) return HttpResponse.json({ message: 'Không tìm thấy ticket.' }, { status: 404 })
    ticket.status = 'REOPENED'
    return HttpResponse.json(ticket)
  }),
]
