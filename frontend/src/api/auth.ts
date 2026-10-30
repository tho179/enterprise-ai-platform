import { api } from '@/api/client'
import { ApiError, normalizeError } from '@/api/errors'
import type { AuthSession, Role } from '@/api/types'
import { ROLES } from '@/api/types'
import { DEMO_MODE } from '@/lib/constants'
import { demoAccounts, demoUsers } from '@/mocks/fixtures'

interface LoginInput {
  email: string
  password: string
}

interface RawAuthResponse {
  id?: string
  fullName?: string
  email?: string
  role?: string
  accessToken?: string
  token?: string
}

function isRole(value: string | undefined): value is Role {
  return value !== undefined && (ROLES as readonly string[]).includes(value)
}

function toSession(raw: RawAuthResponse): AuthSession {
  const token = raw.accessToken ?? raw.token
  if (!raw.id || !raw.fullName || !raw.email || !isRole(raw.role) || !token) {
    throw new ApiError('Phản hồi đăng nhập không hợp lệ.', { status: 500 })
  }
  return {
    id: raw.id,
    fullName: raw.fullName,
    email: raw.email,
    role: raw.role,
    accessToken: token,
  }
}

function demoLogin(input: LoginInput): AuthSession {
  const account = demoAccounts.find(
    (item) => item.email.toLowerCase() === input.email.trim().toLowerCase(),
  )
  if (!account || account.password !== input.password) {
    throw new ApiError('Email hoặc mật khẩu không đúng.', { status: 401 })
  }
  const user = demoUsers.find((item) => item.id === account.userId)
  if (!user || !user.active) {
    throw new ApiError('Tài khoản đã bị khóa.', { status: 403 })
  }
  return {
    id: user.id,
    fullName: user.fullName,
    email: user.email,
    role: user.role,
    accessToken: `mock-token-${user.id}-${Date.now()}`,
  }
}

export const authApi = {
  async login(input: LoginInput): Promise<AuthSession> {
    try {
      const { data } = await api.post<RawAuthResponse>('/api/auth/login', {
        email: input.email.trim(),
        password: input.password,
      })
      return toSession(data)
    } catch (error) {
      const normalized = normalizeError(error)
      // Chỉ fallback khi backend không kết nối được; lỗi xác thực phải hiển thị thật.
      if (DEMO_MODE && normalized.status === 0) {
        return demoLogin(input)
      }
      throw normalized
    }
  },
}
