import type { Role } from '@/api/types'
import { defaultRouteForRole } from '@/lib/constants'

export function hasAnyRole(role: Role | undefined, allowed: Role[] | undefined): boolean {
  if (!allowed || allowed.length === 0) return true
  return role !== undefined && allowed.includes(role)
}

export function canManageDocuments(role: Role | undefined): boolean {
  return role === 'ADMIN'
}

export function canApproveLeave(role: Role | undefined): boolean {
  return role === 'MANAGER'
}

export function canManageUsers(role: Role | undefined): boolean {
  return role === 'ADMIN'
}

export function canHandleTickets(role: Role | undefined): boolean {
  return role === 'IT_SUPPORT'
}

export function getDefaultRoute(role: Role | undefined): string {
  return defaultRouteForRole(role)
}
