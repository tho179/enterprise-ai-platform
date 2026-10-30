import { describe, expect, it } from 'vitest'
import {
  countInclusiveDays,
  formatDate,
  formatDateTime,
  isPastDate,
  rangesOverlap,
} from '@/lib/dates'

describe('dates', () => {
  it('counts inclusive calendar days', () => {
    expect(countInclusiveDays('2026-10-29', '2026-10-31')).toBe(3)
    expect(countInclusiveDays('2026-10-29', '2026-10-29')).toBe(1)
  })

  it('returns 0 for invalid or inverted ranges', () => {
    expect(countInclusiveDays('2026-11-01', '2026-10-31')).toBe(0)
    expect(countInclusiveDays('not-a-date', '2026-10-31')).toBe(0)
  })

  it('detects overlapping ranges', () => {
    expect(rangesOverlap('2026-10-01', '2026-10-05', '2026-10-05', '2026-10-08')).toBe(true)
    expect(rangesOverlap('2026-10-01', '2026-10-05', '2026-10-06', '2026-10-08')).toBe(false)
    expect(rangesOverlap('bad', '2026-10-05', '2026-10-06', '2026-10-08')).toBe(false)
  })

  it('formats dates and handles empty input', () => {
    expect(formatDate('2026-10-25T08:30:00')).toBe('25/10/2026')
    expect(formatDateTime('2026-10-25T08:30:00')).toBe('25/10/2026 08:30')
    expect(formatDate(undefined)).toBe('—')
    expect(formatDateTime('invalid')).toBe('—')
  })

  it('only marks dates before today as past', () => {
    expect(isPastDate('2000-01-01')).toBe(true)
    expect(isPastDate('2999-01-01')).toBe(false)
    expect(isPastDate('invalid')).toBe(false)
  })
})
