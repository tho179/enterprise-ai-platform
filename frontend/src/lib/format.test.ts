import { describe, expect, it } from 'vitest'
import { formatBytes, formatNumber, formatPercent, initials, truncate } from '@/lib/format'

describe('format helpers', () => {
  it('formats Vietnamese numbers', () => {
    expect(formatNumber(1234567)).toBe('1.234.567')
    expect(formatNumber(0)).toBe('0')
    expect(formatNumber(undefined)).toBe('—')
    expect(formatNumber(Number.NaN)).toBe('—')
  })

  it('formats byte sizes', () => {
    expect(formatBytes(512)).toBe('512 B')
    expect(formatBytes(2048)).toBe('2 KB')
    expect(formatBytes(2.5 * 1024 * 1024)).toBe('2.5 MB')
  })

  it('formats percentages', () => {
    expect(formatPercent(0.916)).toBe('92%')
  })

  it('builds initials from Vietnamese names', () => {
    expect(initials('Nguyễn Văn An')).toBe('NA')
    expect(initials('An')).toBe('AN')
    expect(initials('  ')).toBe('?')
  })

  it('truncates long text without cutting the suffix', () => {
    expect(truncate('abcdef', 3)).toBe('abc…')
    expect(truncate('abc', 3)).toBe('abc')
  })
})
