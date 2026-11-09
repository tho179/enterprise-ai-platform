import { Tooltip } from 'antd'
import { Link, useLocation } from 'react-router-dom'
import { useAuth } from '@/auth/AuthContext'
import { ROLE_LABELS } from '@/lib/constants'
import { initials } from '@/lib/format'
import { isRailItemActive, RAIL_ITEMS } from '@/components/layout/navConfig'
import { DEMO_MODE } from '@/lib/constants'
import type { WorkspaceCounts } from '@/components/layout/useWorkspaceCounts'

export function Rail({ counts }: { counts: WorkspaceCounts }) {
  const { session } = useAuth()
  const { pathname } = useLocation()

  if (!session) return null

  const items = RAIL_ITEMS.filter((item) => DEMO_MODE || !item.demoOnly).filter(
    (item) => !item.roles || item.roles.includes(session.role),
  )
  const activeItem = [...items]
    .filter((item) => isRailItemActive(pathname, item.to))
    .sort((a, b) => b.to.length - a.to.length)[0]

  return (
    <nav className="rail" aria-label="Điều hướng chính">
      <Link to="/dashboard" className="rail__logo" aria-label="EAKWP Console">
        E
      </Link>
      <div className="rail__nav">
        {items.map((item) => {
          const badge =
            item.key === 'approvals'
              ? counts.pendingApprovals
              : item.key === 'queue'
                ? counts.queueOpen
                : 0
          const active = activeItem?.key === item.key
          return (
            <Tooltip key={item.key} title={item.label} placement="right">
              <Link
                to={item.to}
                className={`rail__item${active ? ' rail__item--active' : ''}`}
                aria-label={item.label}
                aria-current={active ? 'page' : undefined}
              >
                {item.icon}
                {badge > 0 ? <span className="rail__badge" aria-hidden="true" /> : null}
              </Link>
            </Tooltip>
          )
        })}
      </div>
      <div className="rail__spacer" />
      <Tooltip
        title={`${session.fullName} · ${ROLE_LABELS[session.role]}`}
        placement="right"
      >
        <Link to="/dashboard" className="rail__avatar" aria-label="Hồ sơ người dùng">
          {initials(session.fullName)}
        </Link>
      </Tooltip>
    </nav>
  )
}
