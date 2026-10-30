import type { ReactNode } from 'react'

export function Panel({
  title,
  extra,
  children,
  flush = false,
  className = '',
}: {
  title: ReactNode
  extra?: ReactNode
  children: ReactNode
  flush?: boolean
  className?: string
}) {
  return (
    <section className={`panel ${className}`.trim()}>
      <div className="panel__head">
        <h2 className="panel__title">{title}</h2>
        {extra}
      </div>
      <div className={`panel__body${flush ? ' panel__body--flush' : ''}`}>{children}</div>
    </section>
  )
}
