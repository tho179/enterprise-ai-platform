import { useEffect, useMemo, useRef, useState } from 'react'
import type { ReactNode } from 'react'
import {
  CloseOutlined,
  DeleteOutlined,
  FileSearchOutlined,
  HistoryOutlined,
  MessageOutlined,
  PlusOutlined,
  ReloadOutlined,
  RobotOutlined,
  SafetyCertificateOutlined,
  SendOutlined,
} from '@ant-design/icons'
import { Alert, Button, Drawer, Empty, Grid, Input, Popconfirm, Spin, Tag, Tooltip } from 'antd'
import { useSearchParams } from 'react-router-dom'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import rehypeSanitize from 'rehype-sanitize'
import dayjs from 'dayjs'
import { chatApi } from '@/api/chat'
import { normalizeError } from '@/api/errors'
import type { Citation, ChatTurn } from '@/api/types'
import { useAuth } from '@/auth/AuthContext'
import { CitationCard, CitationModal } from '@/components/citations/CitationList'
import { CHAT_SUGGESTIONS } from '@/components/layout/navConfig'
import { linkCitationMarkers } from '@/lib/citations'
import { formatRelative } from '@/lib/dates'
import { initials, truncate } from '@/lib/format'
import { readChatStorage, writeChatStorage } from '@/lib/storage'
import { usePageTitle } from '@/lib/usePageTitle'

interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  createdAt: string
  citations?: Citation[]
  model?: string
  executionTimeMs?: number
}

interface ChatSession {
  id: string
  title: string
  createdAt: string
  updatedAt: string
  messages: ChatMessage[]
}

function createId(prefix: string): string {
  return `${prefix}-${Date.now()}-${Math.random().toString(16).slice(2, 7)}`
}

function citationKey(citation: Citation): string {
  return citation.chunk_id ?? `${citation.document_id ?? 'doc'}-${citation.index}`
}

function loadSessions(userId: string | undefined): ChatSession[] {
  if (!userId) return []
  return readChatStorage<ChatSession[]>(userId) ?? []
}

function InspectorBody({
  message,
  activeCitationKey,
  onSelectCitation,
}: {
  message: ChatMessage
  activeCitationKey: string | null
  onSelectCitation: (citation: Citation) => void
}) {
  const citations = message.citations ?? []
  return (
    <div className="inspector__body">
      {citations.length > 0 ? (
        citations.map((citation) => (
          <CitationCard
            key={`${message.id}-${citation.index}-${citation.chunk_id}`}
            citation={citation}
            active={citationKey(citation) === activeCitationKey}
            onSelect={onSelectCitation}
          />
        ))
      ) : (
        <Empty
          image={Empty.PRESENTED_IMAGE_SIMPLE}
          description="Câu trả lời này chưa có trích dẫn."
        />
      )}
      <div className="inspector__note">
        <SafetyCertificateOutlined /> Nội dung trích từ tài liệu nội bộ. Bấm vào
        trích dẫn để xem toàn văn.
      </div>
    </div>
  )
}

export function ChatPage() {
  usePageTitle('Trợ lý AI')
  const { session } = useAuth()
  const [searchParams, setSearchParams] = useSearchParams()
  const qParam = searchParams.get('q') ?? ''
  const screens = Grid.useBreakpoint()
  const isWide = screens.xl ?? false

  const [sessions, setSessions] = useState<ChatSession[]>(() =>
    loadSessions(session?.id),
  )
  const [activeId, setActiveId] = useState<string | null>(
    () => loadSessions(session?.id)[0]?.id ?? null,
  )
  const [input, setInput] = useState('')
  const [sending, setSending] = useState(false)
  const [pendingSessionId, setPendingSessionId] = useState<string | null>(null)
  const [sendError, setSendError] = useState<string | null>(null)
  const [retryState, setRetryState] = useState<{
    question: string
    sessionId: string
  } | null>(null)
  const [inspectorMessageId, setInspectorMessageId] = useState<string | null>(null)
  const [inspectorOpen, setInspectorOpen] = useState(true)
  const [drawerOpen, setDrawerOpen] = useState(false)
  const [sessionsOpen, setSessionsOpen] = useState(false)
  const [selectedCitation, setSelectedCitation] = useState<Citation | null>(null)
  const [activeCitationKey, setActiveCitationKey] = useState<string | null>(null)
  const scrollRef = useRef<HTMLDivElement>(null)
  const handledQRef = useRef<string | null>(null)

  const sortedSessions = useMemo(
    () =>
      [...sessions].sort((a, b) => b.updatedAt.localeCompare(a.updatedAt)),
    [sessions],
  )
  const activeSession = sessions.find((item) => item.id === activeId) ?? null
  const messages = activeSession?.messages ?? []
  const latestAnswer = [...messages]
    .reverse()
    .find(
      (message) =>
        message.role === 'assistant' && (message.citations?.length ?? 0) > 0,
    )
  const inspectorMessage =
    (inspectorMessageId
      ? messages.find((message) => message.id === inspectorMessageId)
      : null) ?? latestAnswer
  const citations = inspectorMessage?.citations ?? []
  const showInspector = isWide && inspectorOpen && citations.length > 0

  useEffect(() => {
    if (session) writeChatStorage(session.id, sessions)
  }, [sessions, session])

  useEffect(() => {
    const element = scrollRef.current
    if (element) element.scrollTop = element.scrollHeight
  }, [activeId, activeSession?.messages.length, sending])

  async function sendQuestion(
    question: string,
    options: {
      createNew?: boolean
      appendUser?: boolean
      sessionId?: string
    } = {},
  ): Promise<void> {
    const trimmed = question.trim()
    if (!trimmed || sending || !session) return

    setSendError(null)
    setRetryState(null)
    setSending(true)

    const now = new Date().toISOString()
    const appendUser = options.appendUser ?? true
    const userMessage: ChatMessage = {
      id: createId('msg'),
      role: 'user',
      content: trimmed,
      createdAt: now,
    }

    let targetId: string
    if (options.sessionId) targetId = options.sessionId
    else if (options.createNew || !activeId) targetId = createId('chat')
    else targetId = activeId

    const target = sessions.find((item) => item.id === targetId) ?? null

    if (!target) {
      const newSession: ChatSession = {
        id: targetId,
        title: truncate(trimmed, 56),
        createdAt: now,
        updatedAt: now,
        messages: appendUser ? [userMessage] : [],
      }
      setSessions((previous) => [newSession, ...previous])
      setActiveId(targetId)
    } else if (appendUser) {
      setSessions((previous) =>
        previous.map((item) =>
          item.id === targetId
            ? {
                ...item,
                title:
                  item.messages.length === 0 ? truncate(trimmed, 56) : item.title,
                messages: [...item.messages, userMessage],
                updatedAt: now,
              }
            : item,
        ),
      )
    }

    const history: ChatTurn[] = (target?.messages ?? [])
      .filter(
        (message) => message.role === 'assistant' || message.content !== trimmed,
      )
      .slice(-4)
      .map((message) => ({ role: message.role, content: message.content }))

    setPendingSessionId(targetId)
    setInspectorMessageId(null)
    setActiveCitationKey(null)

    try {
      const response = await chatApi.ask({ question: trimmed, history })
      const answer: ChatMessage = {
        id: createId('msg'),
        role: 'assistant',
        content: response.answer,
        createdAt: new Date().toISOString(),
        citations: response.citations,
        model: response.model_used,
        executionTimeMs: response.execution_time_ms,
      }
      setSessions((previous) =>
        previous.map((item) =>
          item.id === targetId
            ? {
                ...item,
                messages: [...item.messages, answer],
                updatedAt: new Date().toISOString(),
              }
            : item,
        ),
      )
      setInspectorMessageId(answer.id)
      if (isWide && (response.citations?.length ?? 0) > 0) {
        setInspectorOpen(true)
      }
    } catch (error) {
      setSendError(normalizeError(error).message)
      setRetryState({ question: trimmed, sessionId: targetId })
    } finally {
      setSending(false)
      setPendingSessionId(null)
    }
  }

  useEffect(() => {
    if (!qParam || handledQRef.current === qParam) return
    handledQRef.current = qParam
    void sendQuestion(qParam, { createNew: true })
    setSearchParams({}, { replace: true })
    // qParam is the only trigger; sendQuestion intentionally uses current state.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [qParam])

  if (!session) return null

  const handleSend = () => {
    const question = input.trim()
    if (!question || sending) return
    setInput('')
    void sendQuestion(question)
  }

  const handleSuggestion = (question: string) => {
    if (sending) return
    void sendQuestion(question, { createNew: true })
  }

  const startNewChat = () => {
    setActiveId(null)
    setInput('')
    setSendError(null)
    setRetryState(null)
  }

  const deleteSession = (id: string) => {
    setSessions((previous) => previous.filter((item) => item.id !== id))
    if (activeId === id) setActiveId(null)
  }

  const openCitations = (message: ChatMessage) => {
    setInspectorMessageId(message.id)
    setActiveCitationKey(null)
    if (isWide) setInspectorOpen(true)
    else setDrawerOpen(true)
  }

  const openCitation = (citation: Citation) => {
    setActiveCitationKey(citationKey(citation))
    setSelectedCitation(citation)
  }

  const retry = () => {
    if (!retryState) return
    void sendQuestion(retryState.question, {
      appendUser: false,
      sessionId: retryState.sessionId,
    })
  }

  const markdownComponents = (message: ChatMessage) => ({
    a: ({ href, children }: { href?: string; children?: ReactNode }) => {
      if (href?.startsWith('#citation-')) {
        const index = Number(href.replace('#citation-', ''))
        return (
          <button
            type="button"
            className="citation-marker"
            onClick={() => {
              const citation = message.citations?.find(
                (item) => item.index === index,
              )
              setInspectorMessageId(message.id)
              if (isWide) setInspectorOpen(true)
              else setDrawerOpen(true)
              if (citation) openCitation(citation)
            }}
            title={`Xem trích dẫn ${index}`}
          >
            {children}
          </button>
        )
      }
      return (
        <a href={href} target="_blank" rel="noreferrer">
          {children}
        </a>
      )
    },
  })

  const selectSession = (id: string) => {
    setActiveId(id)
    setSendError(null)
    setRetryState(null)
    setSessionsOpen(false)
  }

  const renderSessions = () =>
    sortedSessions.length > 0 ? (
      sortedSessions.map((item) => (
        <div
          key={item.id}
          className={`chat-session-row${item.id === activeId ? ' chat-session-row--active' : ''}`}
        >
          <button
            type="button"
            className="chat-session"
            onClick={() => selectSession(item.id)}
          >
            <span className="chat-session__body">
              <span className="chat-session__title">{item.title}</span>
              <span className="chat-session__meta">
                {item.messages.length} tin nhắn · {formatRelative(item.updatedAt)}
                {pendingSessionId === item.id ? ' · đang trả lời…' : ''}
              </span>
            </span>
          </button>
          <Popconfirm
            title="Xóa cuộc trò chuyện?"
            description="Toàn bộ tin nhắn trong cuộc trò chuyện này sẽ bị xóa."
            okText="Xóa"
            cancelText="Hủy"
            onConfirm={() => deleteSession(item.id)}
            disabled={pendingSessionId === item.id}
          >
            <Button
              type="text"
              size="small"
              className="chat-session__delete"
              icon={<DeleteOutlined />}
              aria-label="Xóa cuộc trò chuyện"
              disabled={pendingSessionId === item.id}
            />
          </Popconfirm>
        </div>
      ))
    ) : (
      <div className="chat-sessions__empty">
        <MessageOutlined />
        <span>Chưa có cuộc trò chuyện nào.</span>
      </div>
    )

  return (
    <div className="chat-page">
      <div className={`chat-workspace${showInspector ? ' chat-workspace--inspector' : ''}`}>
        <aside className="chat-sessions">
          <div className="chat-sessions__head">
            <div>
              <div style={{ fontWeight: 600, fontSize: 13 }}>Lịch sử trò chuyện</div>
              <div className="muted" style={{ fontSize: 11 }}>
                {sessions.length} cuộc trò chuyện
              </div>
            </div>
            <Tooltip title="Cuộc trò chuyện mới">
              <Button
                type="text"
                size="small"
                icon={<PlusOutlined />}
                onClick={startNewChat}
                aria-label="Cuộc trò chuyện mới"
              />
            </Tooltip>
          </div>
          <div className="chat-sessions__list">{renderSessions()}</div>
        </aside>

        <section className="chat-thread">
          <div className="chat-thread__head">
            <div style={{ minWidth: 0, flex: 1 }}>
              <h2 className="chat-thread__title">
                {activeSession?.title ?? 'Cuộc trò chuyện mới'}
              </h2>
              <div className="chat-thread__meta">
                Trợ lý AI · Trích dẫn từ kho tri thức nội bộ
              </div>
            </div>
            <Tooltip title="Lịch sử trò chuyện">
              <Button
                className="chat-history-trigger"
                size="small"
                icon={<HistoryOutlined />}
                onClick={() => setSessionsOpen(true)}
              >
                Lịch sử
              </Button>
            </Tooltip>
            <Tooltip title="Cuộc trò chuyện mới">
              <Button
                className="chat-new-session"
                size="small"
                icon={<PlusOutlined />}
                onClick={startNewChat}
                aria-label="Cuộc trò chuyện mới"
              />
            </Tooltip>
            {latestAnswer && (latestAnswer.citations?.length ?? 0) > 0 ? (
              <Button
                size="small"
                icon={<FileSearchOutlined />}
                onClick={() => openCitations(latestAnswer)}
              >
                Nguồn ({latestAnswer.citations?.length})
              </Button>
            ) : null}
          </div>

          <div className="chat-messages" ref={scrollRef}>
            {messages.length === 0 && !sending ? (
              <div className="chat-empty">
                <div className="chat-empty__icon">
                  <RobotOutlined />
                </div>
                <h2 className="chat-empty__title">Hỏi trợ lý về tri thức nội bộ</h2>
                <p className="chat-empty__desc">
                  Câu trả lời được tổng hợp từ tài liệu đã nạp và luôn kèm trích
                  dẫn để bạn đối chiếu.
                </p>
                <div className="suggestion-grid">
                  {CHAT_SUGGESTIONS.map((suggestion) => (
                    <button
                      key={suggestion.label}
                      type="button"
                      className="suggestion"
                      onClick={() => handleSuggestion(suggestion.question)}
                    >
                      {suggestion.label}
                    </button>
                  ))}
                </div>
              </div>
            ) : (
              <>
                {messages.map((message) => (
                  <article
                    key={message.id}
                    className={`chat-message chat-message--${message.role}`}
                  >
                    <div className="chat-message__avatar">
                      {message.role === 'assistant' ? (
                        <RobotOutlined />
                      ) : (
                        initials(session.fullName)
                      )}
                    </div>
                    <div className="chat-message__body">
                      <div className="chat-message__head">
                        <span className="chat-message__name">
                          {message.role === 'assistant'
                            ? 'Trợ lý EAKWP'
                            : session.fullName}
                        </span>
                        <span className="chat-message__time">
                          {dayjs(message.createdAt).format('HH:mm')}
                        </span>
                      </div>
                      {message.role === 'assistant' ? (
                        <div className="chat-answer">
                          <ReactMarkdown
                            remarkPlugins={[remarkGfm]}
                            rehypePlugins={[rehypeSanitize]}
                            components={markdownComponents(message)}
                          >
                            {linkCitationMarkers(message.content)}
                          </ReactMarkdown>
                        </div>
                      ) : (
                        <div className="chat-message__text">{message.content}</div>
                      )}
                      {message.role === 'assistant' ? (
                        <div className="chat-message__foot">
                          {(message.citations?.length ?? 0) > 0 ? (
                            <button
                              type="button"
                              className="chat-source-button"
                              onClick={() => openCitations(message)}
                            >
                              <FileSearchOutlined /> {message.citations?.length}{' '}
                              nguồn trích dẫn
                            </button>
                          ) : (
                            <span>Không có trích dẫn cho câu trả lời này.</span>
                          )}
                          {message.executionTimeMs !== undefined ? (
                            <span>{message.executionTimeMs} ms</span>
                          ) : null}
                          {message.model ? <span className="mono">{message.model}</span> : null}
                        </div>
                      ) : null}
                    </div>
                  </article>
                ))}
                {sending && pendingSessionId === activeId ? (
                  <div className="chat-message chat-message--assistant">
                    <div className="chat-message__avatar">
                      <RobotOutlined />
                    </div>
                    <div className="chat-message__body">
                      <div className="chat-typing">
                        <Spin size="small" /> Đang tra cứu kho tri thức…
                      </div>
                    </div>
                  </div>
                ) : null}
              </>
            )}
          </div>

          <div className="chat-composer">
            {sendError ? (
              <Alert
                type="error"
                showIcon
                title={sendError}
                style={{ marginBottom: 8 }}
                action={
                  retryState ? (
                    <Button
                      size="small"
                      icon={<ReloadOutlined />}
                      onClick={retry}
                      loading={sending}
                    >
                      Thử lại
                    </Button>
                  ) : null
                }
                closable
                onClose={() => {
                  setSendError(null)
                  setRetryState(null)
                }}
              />
            ) : null}
            <div className="chat-composer__inner">
              <Input.TextArea
                value={input}
                onChange={(event) => setInput(event.target.value)}
                onPressEnter={(event) => {
                  if (!event.shiftKey) {
                    event.preventDefault()
                    handleSend()
                  }
                }}
                placeholder="Đặt câu hỏi về tài liệu nội bộ…"
                autoSize={{ minRows: 1, maxRows: 6 }}
                maxLength={2000}
                aria-label="Câu hỏi cho trợ lý AI"
              />
              <div className="chat-composer__bar">
                <span className="chat-composer__hint">
                  Enter để gửi · Shift + Enter để xuống dòng
                </span>
                <span className="chat-composer__count">{input.length}/2000</span>
                <Button
                  type="primary"
                  size="small"
                  icon={<SendOutlined />}
                  onClick={handleSend}
                  loading={sending}
                  disabled={!input.trim() || sending}
                >
                  Gửi
                </Button>
              </div>
            </div>
            <div className="chat-disclaimer">
              Trợ lý có thể mắc lỗi. Hãy kiểm tra trích dẫn trước khi sử dụng thông
              tin cho quyết định quan trọng.
            </div>
          </div>
        </section>

        {showInspector && inspectorMessage ? (
          <aside className="inspector chat-inspector">
            <div className="inspector__head">
              <FileSearchOutlined />
              <h2 className="inspector__title">Nguồn trích dẫn</h2>
              <span className="muted text-sm">{citations.length}</span>
              <Button
                type="text"
                size="small"
                icon={<CloseOutlined />}
                style={{ marginLeft: 'auto' }}
                onClick={() => setInspectorOpen(false)}
                aria-label="Đóng nguồn trích dẫn"
              />
            </div>
            <InspectorBody
              message={inspectorMessage}
              activeCitationKey={activeCitationKey}
              onSelectCitation={openCitation}
            />
            <div className="inspector__foot">
              <Tag icon={<SafetyCertificateOutlined />} color="green">
                Trích từ tài liệu nội bộ
              </Tag>
            </div>
          </aside>
        ) : null}
      </div>

      <Drawer
        title="Nguồn trích dẫn"
        placement="right"
        size={360}
        open={!isWide && drawerOpen && citations.length > 0}
        onClose={() => setDrawerOpen(false)}
        styles={{ body: { padding: 0 } }}
      >
        {inspectorMessage ? (
          <InspectorBody
            message={inspectorMessage}
            activeCitationKey={activeCitationKey}
            onSelectCitation={openCitation}
          />
        ) : null}
      </Drawer>

      <Drawer
        title="Lịch sử trò chuyện"
        placement="left"
        size={320}
        open={sessionsOpen}
        onClose={() => setSessionsOpen(false)}
        styles={{ body: { display: 'flex', flexDirection: 'column', gap: 8, padding: 12 } }}
      >
        <Button
          block
          icon={<PlusOutlined />}
          onClick={() => {
            startNewChat()
            setSessionsOpen(false)
          }}
        >
          Cuộc trò chuyện mới
        </Button>
        <div style={{ flex: 1, minHeight: 0, overflow: 'auto' }}>
          {renderSessions()}
        </div>
      </Drawer>

      <CitationModal
        citation={selectedCitation}
        open={selectedCitation !== null}
        onClose={() => setSelectedCitation(null)}
      />
    </div>
  )
}
