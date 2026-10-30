export const ROLES = ['EMPLOYEE', 'MANAGER', 'ADMIN', 'IT_SUPPORT'] as const
export type Role = (typeof ROLES)[number]

export interface AuthSession {
  id: string
  fullName: string
  email: string
  role: Role
  accessToken: string
}

export interface User {
  id: string
  fullName: string
  email: string
  role: Role
  active: boolean
  createdAt: string
}

export type DocumentStatus = 'UPLOADED' | 'PROCESSING' | 'INGESTED' | 'FAILED'

export interface DocumentVersion {
  id: string
  documentId: string
  versionNumber: number
  status: DocumentStatus
  chunkCount: number
  pageCount: number
  isCurrent: boolean
  fileHash: string
  createdAt: string
  createdBy: string
  errorMessage?: string
}

export interface DocumentSummary {
  id: string
  documentCode: string
  title: string
  category: string
  createdAt: string
  updatedAt: string
  createdBy: string
  currentVersion: DocumentVersion
}

export interface DocumentDetail extends DocumentSummary {
  versions: DocumentVersion[]
}

export interface DocumentChunk {
  id: string
  chunkId: string
  documentId?: string
  vectorId: string
  pageStart: number
  pageEnd: number
  headingLevel: number
  sectionPath: string[]
  content: string
}

export interface Citation {
  index: number
  chunk_id: string
  score: number
  document_id?: string | null
  section_path: string[]
  pages: string
  snippet: string
}

export interface ChatTurn {
  role: 'user' | 'assistant'
  content: string
}

export interface AskResponse {
  success: boolean
  query: string
  answer: string
  citations: Citation[]
  execution_time_ms: number
  model_used: string
}

export interface SearchHit {
  chunk_id: string
  score: number
  content: string
  metadata: {
    document_id?: string | null
    page_start?: number | null
    page_end?: number | null
    section_path: string[]
    document_type?: string | null
  }
}

export interface SearchResponse {
  success: boolean
  query: string
  total: number
  execution_time_ms: number
  data: SearchHit[]
}

export type LeaveStatus = 'PENDING' | 'APPROVED' | 'REJECTED' | 'CANCELLED'

export interface LeaveRequest {
  id: string
  userId: string
  employeeName: string
  startDate: string
  endDate: string
  totalDays: number
  reason: string
  status: LeaveStatus
  createdAt: string
  approverName?: string
  comment?: string
  decidedAt?: string
}

export type TicketStatus = 'OPEN' | 'IN_PROGRESS' | 'RESOLVED' | 'CLOSED' | 'REOPENED'
export type TicketCategory = 'NETWORK' | 'HARDWARE' | 'SOFTWARE' | 'ACCOUNT' | 'OTHER' | 'UNCLASSIFIED'
export type TicketPriority = 'LOW' | 'MEDIUM' | 'HIGH' | 'URGENT'

export interface Ticket {
  id: string
  ticketCode: string
  requesterId: string
  requesterName: string
  assigneeId?: string | null
  assigneeName?: string | null
  title: string
  description: string
  attachmentName?: string | null
  category: TicketCategory
  priority: TicketPriority
  aiConfidence?: number | null
  status: TicketStatus
  resolutionNote?: string | null
  createdAt: string
  resolvedAt?: string | null
}

export interface Classification {
  category: TicketCategory
  priority: TicketPriority
  confidence: number
}

export interface TicketSuggestion {
  steps: string[]
  citations: Citation[]
}

export interface AppNotification {
  id: string
  title: string
  body: string
  createdAt: string
  read: boolean
  href?: string
}

export interface HealthSnapshot {
  ai: 'healthy' | 'down'
  qdrantVectors?: number
  model?: string
  latencyMs?: number
}

export interface DocumentListParams {
  q?: string
  category?: string
  status?: string
  page?: number
  size?: number
}

export interface UploadTicket {
  taskId: string
  versionId: string
  documentId?: string
}

export interface IngestionStatus {
  status: 'PROCESSING' | 'INGESTED' | 'FAILED'
  step: number
  chunkCount?: number
  message?: string
}
