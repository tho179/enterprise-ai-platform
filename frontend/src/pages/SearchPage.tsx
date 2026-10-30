import { useEffect, useMemo, useState } from 'react'
import {
  ArrowRightOutlined,
  FileSearchOutlined,
  FileTextOutlined,
  MessageOutlined,
  SearchOutlined,
} from '@ant-design/icons'
import { Button, Input, Select, Skeleton, Tag } from 'antd'
import { useQuery } from '@tanstack/react-query'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { documentsApi } from '@/api/documents'
import { searchApi } from '@/api/search'
import type { SearchHit } from '@/api/types'
import { useAuth } from '@/auth/AuthContext'
import { PageHeader } from '@/components/ui/PageHeader'
import { EmptyState, ErrorState } from '@/components/ui/States'
import { SEARCH_SUGGESTIONS } from '@/components/layout/navConfig'
import { formatPercent } from '@/lib/format'
import { usePageTitle } from '@/lib/usePageTitle'

function escapeRegExp(value: string): string {
  return value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
}

function HighlightedText({ text, query }: { text: string; query: string }) {
  const tokens = query
    .split(/\s+/)
    .map((token) => token.trim())
    .filter((token) => token.length > 1)
  if (tokens.length === 0) return <>{text}</>
  const pattern = new RegExp(`(${tokens.map(escapeRegExp).join('|')})`, 'gi')
  const lowered = new Set(tokens.map((token) => token.toLowerCase()))
  return (
    <>
      {text.split(pattern).map((part, index) =>
        lowered.has(part.toLowerCase()) ? (
          <mark key={`${part}-${index}`} className="search-mark">
            {part}
          </mark>
        ) : (
          <span key={`${part}-${index}`}>{part}</span>
        ),
      )}
    </>
  )
}

function resultMeta(hit: SearchHit): string {
  const pages =
    hit.metadata.page_start && hit.metadata.page_end
      ? hit.metadata.page_start === hit.metadata.page_end
        ? `Trang ${hit.metadata.page_start}`
        : `Trang ${hit.metadata.page_start} → ${hit.metadata.page_end}`
      : 'Không rõ trang'
  return `${pages} · ${hit.metadata.document_type ?? 'Tài liệu nội bộ'}`
}

export function SearchPage() {
  usePageTitle('Tìm kiếm tri thức')
  const { session } = useAuth()
  const navigate = useNavigate()
  const [searchParams, setSearchParams] = useSearchParams()
  const submittedQuery = (searchParams.get('q') ?? '').trim()
  const submittedDocument = searchParams.get('document') ?? ''
  const submittedTopK = Number(searchParams.get('topk') ?? '10') || 10

  const [input, setInput] = useState(submittedQuery)
  const [documentId, setDocumentId] = useState<string | undefined>(
    submittedDocument || undefined,
  )
  const [topK, setTopK] = useState(submittedTopK)
  const [selectedChunkId, setSelectedChunkId] = useState<string | null>(null)

  useEffect(() => {
    setInput(submittedQuery)
    setDocumentId(submittedDocument || undefined)
    setTopK(submittedTopK)
  }, [submittedQuery, submittedDocument, submittedTopK])

  const documentsQuery = useQuery({
    queryKey: ['documents'],
    queryFn: () => documentsApi.list({}),
    enabled: session !== null,
  })
  const documents = documentsQuery.data?.items ?? []
  const documentLookup = useMemo(
    () => new Map(documents.map((document) => [document.id, document])),
    [documents],
  )

  const searchQuery = useQuery({
    queryKey: ['search', submittedQuery, submittedDocument, submittedTopK],
    queryFn: () =>
      searchApi.search({
        query: submittedQuery,
        topK: submittedTopK,
        documentId: submittedDocument || undefined,
        minScore: 0.2,
      }),
    enabled: submittedQuery.length > 0,
  })

  const results = searchQuery.data?.data ?? []
  const selected = results.find((hit) => hit.chunk_id === selectedChunkId) ?? null
  const selectedDocument = selected?.metadata.document_id
    ? documentLookup.get(selected.metadata.document_id)
    : undefined

  useEffect(() => {
    if (results.length === 0) {
      setSelectedChunkId(null)
      return
    }
    if (!results.some((hit) => hit.chunk_id === selectedChunkId)) {
      setSelectedChunkId(results[0].chunk_id)
    }
  }, [results, selectedChunkId])

  const runSearch = () => {
    const query = input.trim()
    if (!query) return
    const next = new URLSearchParams()
    next.set('q', query)
    if (documentId) next.set('document', documentId)
    if (topK !== 10) next.set('topk', String(topK))
    if (
      query === submittedQuery &&
      (documentId ?? '') === submittedDocument &&
      topK === submittedTopK
    ) {
      void searchQuery.refetch()
      return
    }
    setSearchParams(next)
  }

  const askAboutSelected = () => {
    if (!selected) return
    const question = `Hãy giải thích nội dung sau trong tài liệu nội bộ: ${selected.content.slice(0, 320)}`
    navigate(`/chat?q=${encodeURIComponent(question)}`)
  }

  return (
    <div>
      <PageHeader
        title="Tìm kiếm tri thức"
        description="Tìm theo ngữ nghĩa trên toàn bộ tài liệu đã nạp. Mỗi kết quả là một đoạn trích cụ thể, kèm điểm tương đồng."
        actions={
          <Button icon={<MessageOutlined />} onClick={() => navigate('/chat')}>
            Hỏi trợ lý AI
          </Button>
        }
      />

      <section className="search-hero">
        <div className="search-bar">
          <Input
            size="large"
            allowClear
            prefix={<SearchOutlined />}
            placeholder="Ví dụ: nhân viên được nghỉ phép bao nhiêu ngày?"
            value={input}
            onChange={(event) => setInput(event.target.value)}
            onPressEnter={runSearch}
            aria-label="Từ khóa tìm kiếm"
          />
          <Button type="primary" size="large" onClick={runSearch} loading={searchQuery.isFetching}>
            Tìm kiếm
          </Button>
        </div>
        <div className="search-filters">
          <Select
            allowClear
            style={{ minWidth: 240 }}
            placeholder="Tất cả tài liệu"
            value={documentId}
            onChange={(value) => setDocumentId(value)}
            options={documents.map((document) => ({
              value: document.id,
              label: `${document.title} · ${document.documentCode}`,
            }))}
            loading={documentsQuery.isLoading}
            aria-label="Lọc theo tài liệu"
          />
          <Select
            style={{ width: 150 }}
            value={topK}
            onChange={(value) => setTopK(value)}
            options={[
              { value: 5, label: '5 kết quả' },
              { value: 10, label: '10 kết quả' },
              { value: 20, label: '20 kết quả' },
            ]}
            aria-label="Số kết quả"
          />
          {!submittedQuery ? (
            <div className="search-suggestions">
              {SEARCH_SUGGESTIONS.map((term) => (
                <button
                  key={term}
                  type="button"
                  className="search-chip"
                  onClick={() => {
                    setInput(term)
                    const next = new URLSearchParams()
                    next.set('q', term)
                    setSearchParams(next)
                  }}
                >
                  {term}
                </button>
              ))}
            </div>
          ) : null}
        </div>
      </section>

      {!submittedQuery ? (
        <EmptyState
          title="Bắt đầu bằng một câu hỏi hoặc từ khóa"
          description="Ví dụ: “thời gian thử việc”, “làm việc từ xa VPN” hoặc “mật khẩu an toàn thông tin”."
        />
      ) : searchQuery.isError ? (
        <ErrorState
          message="Không thể tìm kiếm trong kho tri thức."
          onRetry={() => searchQuery.refetch()}
        />
      ) : (
        <div className="search-layout">
          <section>
            <div className="search-summary">
              <div>
                <strong>{searchQuery.data?.total ?? 0}</strong> kết quả cho “
                {submittedQuery}”
              </div>
              {searchQuery.data ? (
                <span className="muted text-sm">
                  {searchQuery.data.execution_time_ms} ms
                  {submittedDocument
                    ? ` · ${documentLookup.get(submittedDocument)?.title ?? 'Tài liệu đã chọn'}`
                    : ''}
                </span>
              ) : null}
            </div>

            {searchQuery.isLoading ? (
              <div className="search-results">
                <Skeleton active paragraph={{ rows: 3 }} />
                <Skeleton active paragraph={{ rows: 3 }} />
                <Skeleton active paragraph={{ rows: 3 }} />
              </div>
            ) : results.length > 0 ? (
              <div className="search-results">
                {results.map((hit) => {
                  const document = hit.metadata.document_id
                    ? documentLookup.get(hit.metadata.document_id)
                    : undefined
                  return (
                    <button
                      key={hit.chunk_id}
                      type="button"
                      className={`search-result${hit.chunk_id === selectedChunkId ? ' search-result--active' : ''}`}
                      aria-pressed={hit.chunk_id === selectedChunkId}
                      onClick={() => setSelectedChunkId(hit.chunk_id)}
                    >
                      <div className="search-result__head">
                        <span className="search-result__path">
                          {hit.metadata.section_path?.join(' › ') || 'Đoạn trích tài liệu'}
                        </span>
                        <span className="score-pill">{formatPercent(hit.score)}</span>
                      </div>
                      <div className="search-result__snippet">
                        <HighlightedText text={hit.content} query={submittedQuery} />
                      </div>
                      <div className="search-result__meta">
                        <span>{resultMeta(hit)}</span>
                        {document ? <span>{document.documentCode}</span> : null}
                      </div>
                    </button>
                  )
                })}
              </div>
            ) : (
              <EmptyState
                title="Không tìm thấy đoạn tài liệu phù hợp"
                description="Thử từ khóa ngắn hơn, bỏ bộ lọc tài liệu hoặc hỏi trợ lý AI để diễn giải câu hỏi."
                action={
                  <Button icon={<MessageOutlined />} onClick={() => navigate('/chat')}>
                    Hỏi trợ lý AI
                  </Button>
                }
              />
            )}
          </section>

          <aside className="inspector search-inspector">
            <div className="inspector__head">
              <FileSearchOutlined />
              <h2 className="inspector__title">Chi tiết đoạn trích</h2>
            </div>
            {selected ? (
              <>
                <div className="inspector__body">
                  <div className="detail-list">
                    <div>
                      <div className="muted text-sm">Đường dẫn mục</div>
                      <div style={{ fontWeight: 600, marginTop: 2 }}>
                        {selected.metadata.section_path?.join(' › ') || '—'}
                      </div>
                    </div>
                    <div className="row row--wrap">
                      <Tag>{resultMeta(selected)}</Tag>
                      <Tag color="blue">Điểm {selected.score.toFixed(3)}</Tag>
                      {selectedDocument ? (
                        <Tag className="mono">{selectedDocument.documentCode}</Tag>
                      ) : null}
                    </div>
                    <div>
                      <div className="muted text-sm">Nội dung</div>
                      <div className="chunk-content mt-8">
                        <HighlightedText text={selected.content} query={submittedQuery} />
                      </div>
                    </div>
                    <div className="row row--wrap">
                      {selectedDocument ? (
                        <Button
                          icon={<FileTextOutlined />}
                          onClick={() => navigate(`/documents/${selectedDocument.id}`)}
                        >
                          Mở tài liệu
                        </Button>
                      ) : null}
                      <Button
                        type="primary"
                        icon={<MessageOutlined />}
                        onClick={askAboutSelected}
                      >
                        Hỏi AI về đoạn này
                      </Button>
                    </div>
                  </div>
                </div>
                <div className="inspector__foot">
                  <span className="muted text-sm">
                    Điểm càng cao nghĩa là đoạn trích càng gần với truy vấn.
                  </span>
                </div>
              </>
            ) : (
              <div className="inspector__body">
                <EmptyState
                  title="Chọn một kết quả"
                  description="Bấm vào kết quả bên trái để xem toàn văn và thao tác."
                />
              </div>
            )}
          </aside>
        </div>
      )}

      {selected ? (
        <div className="search-footnote">
          <ArrowRightOutlined /> Bạn có thể hỏi AI về đoạn trích để được giải thích
          trong ngữ cảnh tài liệu.
        </div>
      ) : null}
    </div>
  )
}
