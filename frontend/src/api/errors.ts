import { isAxiosError } from 'axios'

export class ApiError extends Error {
  readonly status: number
  readonly code?: string
  readonly details?: unknown

  constructor(message: string, options: { status?: number; code?: string; details?: unknown } = {}) {
    super(message)
    this.name = 'ApiError'
    this.status = options.status ?? 0
    this.code = options.code
    this.details = options.details
  }
}

type ErrorBody = {
  message?: unknown
  error?: unknown
  code?: unknown
  detail?: unknown
}

function messageFromBody(body: unknown): { message?: string; code?: string } {
  if (!body || typeof body !== 'object') return {}
  const data = body as ErrorBody
  if (typeof data.error === 'object' && data.error !== null) {
    const nested = data.error as ErrorBody
    return {
      message: typeof nested.message === 'string' ? nested.message : undefined,
      code: typeof nested.code === 'string' ? nested.code : undefined,
    }
  }
  return {
    message:
      typeof data.message === 'string'
        ? data.message
        : typeof data.detail === 'string'
          ? data.detail
          : undefined,
    code: typeof data.code === 'string' ? data.code : undefined,
  }
}

export function normalizeError(error: unknown): ApiError {
  if (error instanceof ApiError) return error

  if (isAxiosError(error)) {
    const status = error.response?.status ?? 0
    if (status === 0) {
      const isTimeout = error.code === 'ECONNABORTED'
      return new ApiError(
        isTimeout
          ? 'Máy chủ phản hồi quá lâu. Vui lòng thử lại.'
          : 'Không kết nối được máy chủ. Kiểm tra backend hoặc chế độ mock.',
        { status: isTimeout ? 408 : 0, code: error.code },
      )
    }
    const parsed = messageFromBody(error.response?.data)
    return new ApiError(parsed.message || `Yêu cầu thất bại (HTTP ${status}).`, {
      status,
      code: parsed.code,
      details: error.response?.data,
    })
  }

  if (error instanceof Error) {
    return new ApiError(error.message)
  }

  return new ApiError('Đã xảy ra lỗi không xác định.')
}

export function loginErrorMessage(error: ApiError): string {
  const message = error.message.toLowerCase()
  if (error.status === 403) {
    return 'Tài khoản đã bị khóa. Vui lòng liên hệ quản trị viên.'
  }
  if (
    error.status === 401 ||
    message.includes('invalid email') ||
    message.includes('invalid password') ||
    message.includes('bad credentials')
  ) {
    return 'Email hoặc mật khẩu không đúng.'
  }
  if (error.status === 0 || error.status === 408) {
    return error.message
  }
  return error.message || 'Không thể đăng nhập. Vui lòng thử lại.'
}
