import { Navigate, Route, Routes, useLocation } from 'react-router-dom'
import { useEffect } from 'react'
import { DemoOnly } from '@/components/ui/DemoOnly'
import { AppShell } from '@/components/layout/AppShell'
import { RequireAuth, RequireRole } from '@/auth/guards'
import { useAuth } from '@/auth/AuthContext'
import { defaultRouteForRole } from '@/lib/constants'
import { LoginPage } from '@/pages/LoginPage'
import { DashboardPage } from '@/pages/DashboardPage'
import { ChatPage } from '@/pages/ChatPage'
import { SearchPage } from '@/pages/SearchPage'
import { DocumentsPage } from '@/pages/DocumentsPage'
import { DocumentDetailPage } from '@/pages/DocumentDetailPage'
import { UploadPage } from '@/pages/UploadPage'
import { UsersPage } from '@/pages/UsersPage'
import { LeavePage } from '@/pages/LeavePage'
import { ApprovalsPage } from '@/pages/ApprovalsPage'
import { TicketsPage } from '@/pages/TicketsPage'
import { TicketQueuePage } from '@/pages/TicketQueuePage'
import { ForbiddenPage } from '@/pages/ForbiddenPage'
import { NotFoundPage } from '@/pages/NotFoundPage'

function ScrollToTop() {
  const { pathname } = useLocation()
  useEffect(() => {
    window.scrollTo({ top: 0, behavior: 'auto' })
    // .app-content owns the console scroll, so window scroll alone leaves stale offsets.
    document.querySelector<HTMLElement>('.app-content')?.scrollTo({
      top: 0,
      behavior: 'auto',
    })
  }, [pathname])
  return null
}

function RoleHome() {
  const { session } = useAuth()
  return <Navigate to={defaultRouteForRole(session?.role)} replace />
}

export function AppRoutes() {
  return (
    <>
      <ScrollToTop />
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route
          element={
            <RequireAuth>
              <AppShell />
            </RequireAuth>
          }
        >
          <Route index element={<RoleHome />} />
          <Route path="dashboard" element={<DashboardPage />} />
          <Route path="chat" element={<ChatPage />} />
          <Route path="search" element={<SearchPage />} />
          <Route path="documents" element={<DocumentsPage />} />
          <Route
            path="documents/upload"
            element={
              <RequireRole roles={['ADMIN']}>
                <UploadPage />
              </RequireRole>
            }
          />
          <Route path="documents/:id" element={<DocumentDetailPage />} />
          <Route path="leave" element={<DemoOnly><LeavePage /></DemoOnly>} />
          <Route
            path="approvals"
            element={
              <RequireRole roles={['MANAGER']}>
                <DemoOnly><ApprovalsPage /></DemoOnly>
              </RequireRole>
            }
          />
          <Route path="tickets" element={<DemoOnly><TicketsPage /></DemoOnly>} />
          <Route
            path="tickets/queue"
            element={
              <RequireRole roles={['IT_SUPPORT']}>
                <DemoOnly><TicketQueuePage /></DemoOnly>
              </RequireRole>
            }
          />
          <Route
            path="users"
            element={
              <RequireRole roles={['ADMIN']}>
                <UsersPage />
              </RequireRole>
            }
          />
          <Route path="forbidden" element={<ForbiddenPage />} />
          <Route path="*" element={<NotFoundPage />} />
        </Route>
      </Routes>
    </>
  )
}
