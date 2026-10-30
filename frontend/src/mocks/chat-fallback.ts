import type {
  AskResponse,
  Citation,
  Classification,
  DocumentChunk,
  SearchResponse,
  TicketSuggestion,
} from '@/api/types'
import { demoChunks } from '@/mocks/fixtures'

function pagesOf(chunk: DocumentChunk): string {
  return chunk.pageStart === chunk.pageEnd
    ? `Trang ${chunk.pageStart}`
    : `Trang ${chunk.pageStart} → ${chunk.pageEnd}`
}

function toCitation(chunk: DocumentChunk, index: number, score: number): Citation {
  return {
    index,
    chunk_id: chunk.chunkId,
    score,
    document_id: chunk.documentId,
    section_path: chunk.sectionPath,
    pages: pagesOf(chunk),
    snippet: chunk.content,
  }
}

function scoreChunk(query: string, chunk: DocumentChunk): number {
  const text = `${chunk.sectionPath.join(' ')} ${chunk.content}`.toLowerCase()
  const tokens = query
    .toLowerCase()
    .split(/\s+/)
    .map((token) => token.replace(/[?.,!;:()[\]"]/g, ''))
    .filter((token) => token.length > 2)
  if (tokens.length === 0) return 0
  const matches = tokens.filter((token) => text.includes(token)).length
  if (matches === 0) return 0
  return Math.min(0.94, 0.5 + (matches / tokens.length) * 0.42)
}

function findChunk(id: string): DocumentChunk {
  const found = demoChunks.find((chunk) => chunk.chunkId === id)
  if (!found) throw new Error(`Missing mock chunk ${id}`)
  return found
}

function citationsFor(ids: string[]): Citation[] {
  return ids.map((id, index) => {
    const chunk = findChunk(id)
    return {
      ...toCitation(chunk, index + 1, [0.91, 0.86, 0.78][index] ?? 0.75),
      document_id: id.startsWith('nqld') ? 'doc-nqld' : 'doc-csit',
    }
  })
}

export function mockChatAnswer(question: string): AskResponse {
  const started = performance.now()
  const normalized = question.toLowerCase()
  let answer: string
  let ids: string[]

  if (normalized.includes('nghỉ phép') || normalized.includes('ngày phép')) {
    ids = ['nqld-15-1', 'nqld-15-2']
    answer =
      'Theo **Điều 15 — Nghỉ phép năm** của Nội quy Lao động 2026:\n\n' +
      '- Người lao động làm việc đủ 12 tháng được nghỉ phép năm **12 ngày làm việc**, hưởng nguyên lương [1].\n' +
      '- Có thể thỏa thuận nghỉ thành nhiều lần hoặc nghỉ gộp tối đa 03 năm một lần [2].\n' +
      '- Cần gửi đề nghị trước ít nhất **03 ngày làm việc** để bộ phận nhân sự và quản lý sắp xếp công việc [2].\n\n' +
      '> Trường hợp làm việc chưa đủ 12 tháng, số ngày nghỉ được tính theo tỷ lệ tương ứng với số tháng làm việc [1].'
  } else if (normalized.includes('thử việc')) {
    ids = ['nqld-5-1', 'nqld-5-2']
    answer =
      'Theo **Điều 5 — Thời gian thử việc** [1]:\n\n' +
      '- Tối đa **60 ngày** với công việc cần trình độ cao đẳng trở lên.\n' +
      '- Tối đa **30 ngày** với công việc cần trình độ trung cấp, công nhân kỹ thuật.\n' +
      '- Tối đa **06 ngày làm việc** với công việc khác.\n\n' +
      'Trong thời gian thử việc, mức lương ít nhất bằng **85%** mức lương của công việc đó [2].'
  } else if (normalized.includes('vpn') || normalized.includes('từ xa')) {
    ids = ['nqld-20-1', 'nqld-21-1']
    answer =
      'Theo **Điều 20 — Điều kiện làm việc từ xa** [1]:\n\n' +
      '- Được làm việc từ xa tối đa **02 ngày/tuần** nếu tính chất công việc cho phép và có phê duyệt của quản lý trực tiếp.\n' +
      '- Phải kết nối **VPN nội bộ**, không dùng thiết bị công cộng và không lưu dữ liệu doanh nghiệp trên thiết bị cá nhân khi chưa mã hóa.\n\n' +
      'Khi dùng thiết bị cá nhân, thiết bị phải có phần mềm diệt virus, bật mã hóa ổ đĩa và đăng ký với IT [2].'
  } else if (normalized.includes('mật khẩu') || normalized.includes('bảo mật')) {
    ids = ['csit-7-1', 'nqld-30-1']
    answer =
      'Theo **Chính sách An toàn thông tin** [1]:\n\n' +
      '- Mật khẩu tối thiểu **12 ký tự**, gồm chữ hoa, chữ thường, số và ký tự đặc biệt.\n' +
      '- Không dùng lại mật khẩu đã dùng trong **05 lần gần nhất**.\n' +
      '- Bật xác thực đa yếu tố cho tài khoản truy cập từ bên ngoài.\n\n' +
      'Nhân viên không được chia sẻ tài khoản hoặc mã xác thực cho bất kỳ ai, kể cả đồng nghiệp [2].'
  } else {
    const hits = demoChunks
      .map((chunk) => ({ chunk, score: scoreChunk(question, chunk) }))
      .filter((item) => item.score > 0)
      .sort((a, b) => b.score - a.score)
      .slice(0, 2)

    if (hits.length === 0) {
      return {
        success: true,
        query: question,
        answer:
          'Dựa trên các tài liệu nội bộ hiện tại, tôi chưa tìm thấy thông tin để trả lời câu hỏi này. Bạn có thể thử diễn đạt cụ thể hơn hoặc liên hệ bộ phận phụ trách.',
        citations: [],
        execution_time_ms: Math.max(28, Math.round(performance.now() - started)),
        model_used: 'mock-extractive',
      }
    }

    ids = hits.map((item) => item.chunk.chunkId)
    answer =
      'Tôi tìm thấy các đoạn tài liệu liên quan đến câu hỏi của bạn:\n\n' +
      hits
        .map(
          (item, index) =>
            `**[${index + 1}] ${item.chunk.sectionPath.join(' › ')}** (${pagesOf(item.chunk)}):\n> ${item.chunk.content}`,
        )
        .join('\n\n') +
      '\n\nBạn nên mở trích dẫn để đối chiếu toàn văn trước khi sử dụng thông tin.'
  }

  return {
    success: true,
    query: question,
    answer,
    citations: citationsFor(ids),
    execution_time_ms: Math.max(28, Math.round(performance.now() - started)),
    model_used: 'mock-extractive',
  }
}

export function mockSearchResponse(
  query: string,
  topK: number,
  minScore: number,
  documentId?: string,
): SearchResponse {
  const started = performance.now()
  const data = demoChunks
    .filter((chunk) => !documentId || chunk.documentId === documentId)
    .map((chunk) => ({
      chunk,
      score: scoreChunk(query, chunk),
    }))
    .filter((item) => item.score >= minScore)
    .sort((a, b) => b.score - a.score)
    .slice(0, topK)
    .map(({ chunk, score }) => ({
      chunk_id: chunk.chunkId,
      score: Number(score.toFixed(4)),
      content: chunk.content,
      metadata: {
        document_id: chunk.chunkId.startsWith('nqld') ? 'doc-nqld' : 'doc-csit',
        page_start: chunk.pageStart,
        page_end: chunk.pageEnd,
        section_path: chunk.sectionPath,
        document_type: chunk.chunkId.startsWith('nqld') ? 'Nội quy' : 'Chính sách IT',
      },
    }))

  return {
    success: true,
    query,
    total: data.length,
    execution_time_ms: Math.max(28, Math.round(performance.now() - started)),
    data,
  }
}

export function mockClassification(title: string, description: string): Classification {
  const text = `${title} ${description}`.toLowerCase()
  if (text.includes('vpn') || text.includes('mạng') || text.includes('email')) {
    return { category: 'NETWORK', priority: 'HIGH', confidence: 0.87 }
  }
  if (text.includes('máy in') || text.includes('màn hình') || text.includes('phần cứng')) {
    return { category: 'HARDWARE', priority: 'MEDIUM', confidence: 0.9 }
  }
  if (text.includes('mật khẩu') || text.includes('erp') || text.includes('tài khoản')) {
    return { category: 'ACCOUNT', priority: 'HIGH', confidence: 0.42 }
  }
  if (text.includes('onedrive') || text.includes('phần mềm') || text.includes('cài đặt')) {
    return { category: 'SOFTWARE', priority: 'MEDIUM', confidence: 0.81 }
  }
  return { category: 'SOFTWARE', priority: 'MEDIUM', confidence: 0.55 }
}

export function mockTicketSuggestion(): TicketSuggestion {
  return {
    steps: [
      'Kiểm tra trạng thái dịch vụ VPN và xác nhận tài khoản chưa bị khóa trong hệ thống quản trị.',
      'Yêu cầu người dùng đăng xuất toàn bộ phiên VPN cũ, sau đó đăng nhập lại bằng tài khoản nội bộ.',
      'Xóa cache DNS trên máy người dùng và kiểm tra kết nối tới cổng VPN nội bộ.',
    ],
    citations: citationsFor(['nqld-20-1', 'csit-7-1', 'nqld-30-1']),
  }
}
