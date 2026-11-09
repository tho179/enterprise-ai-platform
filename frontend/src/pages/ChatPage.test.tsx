import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { App as AntApp } from 'antd'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { chatApi } from '@/api/chat'
import { ApiError } from '@/api/errors'
import { ChatPage as ChatPageModule } from '@/pages/ChatPage'

vi.mock('@/api/chat', () => ({ chatApi: { ask: vi.fn() } }))
vi.mock('@/auth/AuthContext', () => ({
  useAuth: () => ({
    session: {
      id: 'u1',
      fullName: 'Nguyễn Văn A',
      email: 'nva@congty.vn',
      role: 'EMPLOYEE',
      accessToken: 'token',
    },
  }),
}))

const ask = vi.mocked(chatApi.ask)

function renderChat() {
  return render(
    <MemoryRouter>
      <AntApp>
        <ChatPageModule />
      </AntApp>
    </MemoryRouter>,
  )
}

function submit(question: string) {
  const input = screen.getByLabelText('Câu hỏi cho trợ lý AI')
  fireEvent.change(input, { target: { value: question } })
  fireEvent.keyDown(input, { key: 'Enter', code: 'Enter', charCode: 13 })
}

beforeEach(() => {
  ask.mockReset()
  Element.prototype.scrollIntoView = vi.fn()
  vi.stubGlobal(
    'ResizeObserver',
    class {
      observe() {}
      unobserve() {}
      disconnect() {}
    },
  )
  window.matchMedia = vi.fn().mockImplementation((query: string) => ({
    matches: false,
    media: query,
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    addListener: vi.fn(),
    removeListener: vi.fn(),
    dispatchEvent: vi.fn(),
    onchange: null,
  }))
})

describe('ChatPage', () => {
  it('shows the answer and its citation source', async () => {
    ask.mockResolvedValue({
      success: true,
      query: 'HĐQT có bao nhiêu thành viên?',
      answer: 'Hội đồng Quản trị có từ 03 đến 11 thành viên [1].',
      citations: [
        {
          index: 1,
          chunk_id: 'doc-1-v1-c7',
          score: 0.9,
          document_id: 'doc-1',
          section_path: ['Chương VII', 'Điều 26'],
          pages: 'Trang 12',
          snippet: 'Số lượng thành viên Hội đồng Quản trị từ 03 đến 11 người.',
        },
      ],
      execution_time_ms: 120,
      model_used: 'test-model',
    })

    renderChat()
    submit('HĐQT có bao nhiêu thành viên?')

    await waitFor(() => expect(ask).toHaveBeenCalledTimes(1))
    expect(ask.mock.calls[0][0].question).toBe('HĐQT có bao nhiêu thành viên?')
    expect(await screen.findByText(/03 đến 11 thành viên/)).toBeInTheDocument()
    expect(screen.getAllByText(/Nguồn|nguồn/).length).toBeGreaterThan(0)
  })

  it('shows the refusal without inventing sources', async () => {
    ask.mockResolvedValue({
      success: true,
      query: 'Cách làm bánh pizza?',
      answer: 'Dựa trên các tài liệu nội bộ hiện tại, tôi chưa tìm thấy thông tin phù hợp với câu hỏi này.',
      citations: [],
      execution_time_ms: 80,
      model_used: 'guardrail-refusal',
    })

    renderChat()
    submit('Cách làm bánh pizza?')

    expect(await screen.findByText(/chưa tìm thấy thông tin/)).toBeInTheDocument()
    expect(screen.queryByText(/Nguồn \(/)).not.toBeInTheDocument()
  })

  it('reports a backend failure to the user', async () => {
    ask.mockRejectedValue(new ApiError('Dịch vụ AI đang gặp sự cố, vui lòng thử lại sau.', { status: 502 }))

    renderChat()
    submit('Câu hỏi bất kỳ')

    expect(await screen.findByText(/Dịch vụ AI đang gặp sự cố/)).toBeInTheDocument()
  })
})
