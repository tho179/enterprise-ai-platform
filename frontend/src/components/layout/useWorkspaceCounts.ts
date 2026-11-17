import { useQuery } from '@tanstack/react-query'
import { documentsApi } from '@/api/documents'
import { leaveApi } from '@/api/leave'
import { DEMO_MODE } from '@/lib/constants'
import { ticketsApi } from '@/api/tickets'
import { useAuth } from '@/auth/AuthContext'

export interface WorkspaceDocument {
  id: string
  title: string
}

export interface WorkspaceCounts {
  documents: number
  /** Ingested documents, sorted by title — what the assistant can cite. */
  ingestedDocuments: WorkspaceDocument[]
  failedDocuments: number
  pendingApprovals: number
  queueOpen: number
  categories: Record<string, number>
}

export function useWorkspaceCounts(): WorkspaceCounts {
  const { session } = useAuth()

  const documentsQuery = useQuery({
    queryKey: ['documents'],
    queryFn: () => documentsApi.list({}),
    enabled: session !== null,
  })

  const pendingQuery = useQuery({
    queryKey: ['leave', 'pending'],
    queryFn: () => leaveApi.list({ status: 'PENDING' }),
    enabled: DEMO_MODE && session?.role === 'MANAGER',
  })

  const queueQuery = useQuery({
    queryKey: ['tickets', 'queue'],
    queryFn: () => ticketsApi.list(),
    enabled: DEMO_MODE && session?.role === 'IT_SUPPORT',
  })

  const documents = documentsQuery.data?.items ?? []
  const categories: Record<string, number> = {}
  for (const document of documents) {
    categories[document.category] = (categories[document.category] ?? 0) + 1
  }

  const ingestedDocuments = documents
    .filter((document) => document.currentVersion.status === 'INGESTED')
    .map((document) => ({ id: document.id, title: document.title }))
    .sort((a, b) => a.title.localeCompare(b.title, 'vi'))

  return {
    documents: documents.length,
    ingestedDocuments,
    failedDocuments: documents.filter(
      (document) => document.currentVersion.status === 'FAILED',
    ).length,
    pendingApprovals: pendingQuery.data?.length ?? 0,
    queueOpen:
      queueQuery.data?.filter((ticket) =>
        ['OPEN', 'REOPENED', 'IN_PROGRESS'].includes(ticket.status),
      ).length ?? 0,
    categories,
  }
}
