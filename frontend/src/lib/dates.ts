import dayjs from 'dayjs'
import relativeTime from 'dayjs/plugin/relativeTime'

dayjs.extend(relativeTime)

export function countInclusiveDays(startDate: string, endDate: string): number {
  const start = dayjs(startDate)
  const end = dayjs(endDate)
  if (!start.isValid() || !end.isValid() || end.isBefore(start, 'day')) return 0
  return end.startOf('day').diff(start.startOf('day'), 'day') + 1
}

export function rangesOverlap(
  startA: string,
  endA: string,
  startB: string,
  endB: string,
): boolean {
  const aStart = dayjs(startA)
  const aEnd = dayjs(endA)
  const bStart = dayjs(startB)
  const bEnd = dayjs(endB)
  if (!aStart.isValid() || !aEnd.isValid() || !bStart.isValid() || !bEnd.isValid()) return false
  return !aEnd.isBefore(bStart, 'day') && !bEnd.isBefore(aStart, 'day')
}

export function isPastDate(value: string): boolean {
  const date = dayjs(value)
  return date.isValid() && date.startOf('day').isBefore(dayjs().startOf('day'))
}

export function formatDate(value: string | undefined | null): string {
  if (!value) return '—'
  const date = dayjs(value)
  return date.isValid() ? date.format('DD/MM/YYYY') : '—'
}

export function formatDateTime(value: string | undefined | null): string {
  if (!value) return '—'
  const date = dayjs(value)
  return date.isValid() ? date.format('DD/MM/YYYY HH:mm') : '—'
}

export function formatRelative(value: string | undefined | null): string {
  if (!value) return '—'
  const date = dayjs(value)
  return date.isValid() ? date.fromNow() : '—'
}

export function todayIso(): string {
  return dayjs().format('YYYY-MM-DD')
}
