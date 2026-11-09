import { describe, expect, it } from 'vitest'
import {
  canApproveLeave,
  canHandleTickets,
  canManageDocuments,
  canManageUsers,
  getDefaultRoute,
  hasAnyRole,
} from '@/lib/permissions'

describe('permissions', () => {
  it('allows access when no roles are required', () => {
    expect(hasAnyRole(undefined, undefined)).toBe(true)
    expect(hasAnyRole(undefined, [])).toBe(true)
  })

  it('checks explicit role lists', () => {
    expect(hasAnyRole('MANAGER', ['MANAGER', 'ADMIN'])).toBe(true)
    expect(hasAnyRole('EMPLOYEE', ['MANAGER', 'ADMIN'])).toBe(false)
    expect(hasAnyRole(undefined, ['EMPLOYEE'])).toBe(false)
  })

  it('maps capabilities to the right roles', () => {
    expect(canManageDocuments('ADMIN')).toBe(true)
    expect(canManageDocuments('MANAGER')).toBe(false)
    expect(canApproveLeave('MANAGER')).toBe(true)
    expect(canApproveLeave('ADMIN')).toBe(false)
    expect(canManageUsers('ADMIN')).toBe(true)
    expect(canHandleTickets('IT_SUPPORT')).toBe(true)
    expect(canHandleTickets('EMPLOYEE')).toBe(false)
  })

  it('selects the landing route by role', () => {
    expect(getDefaultRoute('ADMIN')).toBe('/documents')
    // Tests run with mocks off, where approvals and the IT queue are unavailable.
    expect(getDefaultRoute('MANAGER')).toBe('/chat')
    expect(getDefaultRoute('IT_SUPPORT')).toBe('/chat')
    expect(getDefaultRoute('EMPLOYEE')).toBe('/chat')
    expect(getDefaultRoute(undefined)).toBe('/chat')
  })
})
