import { useEffect, useState } from 'react'
import { Outlet, useLocation } from 'react-router-dom'
import { ContextSidebar } from '@/components/layout/ContextSidebar'
import { Rail } from '@/components/layout/Rail'
import { StatusBar } from '@/components/layout/StatusBar'
import { Topbar } from '@/components/layout/Topbar'
import { useWorkspaceCounts } from '@/components/layout/useWorkspaceCounts'

export function AppShell() {
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const { pathname } = useLocation()
  const counts = useWorkspaceCounts()

  useEffect(() => {
    setSidebarOpen(false)
  }, [pathname])

  return (
    <div className="app-shell">
      <Rail counts={counts} />
      <ContextSidebar
        open={sidebarOpen}
        counts={counts}
        onNavigate={() => setSidebarOpen(false)}
        onClose={() => setSidebarOpen(false)}
      />
      {sidebarOpen ? (
        <button
          type="button"
          className="sidebar-backdrop"
          aria-label="Đóng thanh điều hướng"
          onClick={() => setSidebarOpen(false)}
        />
      ) : null}
      <div className="app-main">
        <Topbar onToggleSidebar={() => setSidebarOpen((value) => !value)} />
        <main className="app-content">
          <Outlet />
        </main>
        <StatusBar />
      </div>
    </div>
  )
}
