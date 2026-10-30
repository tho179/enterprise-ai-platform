import { FileTextOutlined, FilePdfOutlined, LoadingOutlined } from '@ant-design/icons'
import { Alert, Button, Modal, Spin, Tag } from 'antd'
import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { documentsApi } from '@/api/documents'
import { normalizeError } from '@/api/errors'
import type { Citation } from '@/api/types'
import { formatPercent } from '@/lib/format'

export function CitationCard({
  citation,
  active,
  onSelect,
}: {
  citation: Citation
  active?: boolean
  onSelect?: (citation: Citation) => void
}) {
  return (
    <button
      type="button"
      className={`citation-card${active ? ' citation-card--active' : ''}`}
      aria-pressed={active}
      onClick={() => onSelect?.(citation)}
    >
      <div className="citation-card__head">
        <span className="citation-card__index">{citation.index}</span>
        <span className="citation-card__path">
          {citation.section_path?.join(' ') || 'Đoạn trích'}
        </span>
        <span className="score-pill" style={{ marginLeft: 'auto' }}>
          {formatPercent(citation.score)}
        </span>
      </div>
      <div className="citation-card__meta">
        <span>{citation.pages || 'Không rõ trang'}</span>
        {citation.document_id ? (
          <span className="mono" style={{ fontSize: 10 }}>
            {citation.document_id.slice(0, 18)}
          </span>
        ) : null}
      </div>
      <div className="citation-card__snippet">{citation.snippet}</div>
    </button>
  )
}

type PreviewState =
  | { status: 'idle' }
  | { status: 'loading' }
  | { status: 'ready'; url: string }
  | { status: 'error'; message: string }

function ChunkPreview({ citation }: { citation: Citation }) {
  const [preview, setPreview] = useState<PreviewState>({ status: 'idle' })

  useEffect(() => {
    let revoked: string | null = null
    if (!citation.document_id || !citation.chunk_id) return
    setPreview({ status: 'loading' })
    documentsApi
      .chunkPreviewUrl(citation.document_id, citation.chunk_id)
      .then((url) => {
        revoked = url
        setPreview({ status: 'ready', url })
      })
      .catch((error) => {
        setPreview({ status: 'error', message: normalizeError(error).message })
      })
    return () => {
      if (revoked) URL.revokeObjectURL(revoked)
    }
  }, [citation.document_id, citation.chunk_id])

  if (preview.status === 'loading') {
    return (
      <div className="citation-preview" style={{ textAlign: 'center', padding: 24 }}>
        <Spin indicator={<LoadingOutlined spin />} tip="Đang render trang PDF đã tô vàng…" />
      </div>
    )
  }
  if (preview.status === 'error') {
    return (
      <Alert
        type="warning"
        showIcon
        title="Không xem được trang PDF"
        description={preview.message}
      />
    )
  }
  if (preview.status === 'idle') return null
  return (
    <div className="citation-preview">
      <img src={preview.url} alt={`Trang PDF với đoạn trích đã tô vàng: ${citation.pages}`} />
      <div className="muted" style={{ fontSize: 12, marginTop: 4, textAlign: 'center' }}>
        Vùng vàng trên trang là đoạn văn bản mà trích dẫn dựa vào.
      </div>
    </div>
  )
}

export function CitationModal({
  citation,
  open,
  onClose,
}: {
  citation: Citation | null
  open: boolean
  onClose: () => void
}) {
  const [fullPdfUrl, setFullPdfUrl] = useState<string | null>(null)
  const [pdfLoading, setPdfLoading] = useState(false)

  useEffect(() => {
    if (!open && fullPdfUrl) {
      URL.revokeObjectURL(fullPdfUrl)
      setFullPdfUrl(null)
    }
  }, [open, fullPdfUrl])

  async function openFullPdf(documentId: string) {
    if (fullPdfUrl) {
      window.open(fullPdfUrl, '_blank', 'noopener')
      return
    }
    setPdfLoading(true)
    try {
      const url = await documentsApi.fileUrl(documentId)
      setFullPdfUrl(url)
      window.open(url, '_blank', 'noopener')
    } catch {
      // Lỗi tải file: báo qua tag nhỏ, không chặn modal.
      setFullPdfUrl(null)
    } finally {
      setPdfLoading(false)
    }
  }

  return (
    <Modal
      open={open}
      onCancel={onClose}
      title={
        citation ? (
          <span>
            Trích dẫn [{citation.index}] · {citation.pages}
          </span>
        ) : (
          'Trích dẫn'
        )
      }
      width={720}
      footer={
        citation?.document_id ? (
          <>
            <Button
              onClick={() => openFullPdf(citation.document_id as string)}
              loading={pdfLoading}
              icon={<FilePdfOutlined />}
            >
              Mở toàn bộ PDF
            </Button>
            <Link to={`/documents/${citation.document_id}`} onClick={onClose}>
              <Tag color="blue" style={{ cursor: 'pointer', margin: 0 }}>
                <FileTextOutlined /> Thông tin tài liệu gốc
              </Tag>
            </Link>
          </>
        ) : null
      }
    >
      {citation ? (
        <div className="stack" style={{ gap: 14 }}>
          <div>
            <div className="muted text-sm">Trang PDF với đoạn trích được tô vàng</div>
            <ChunkPreview citation={citation} />
          </div>
          <div>
            <div className="muted text-sm">Đường dẫn mục</div>
            <div style={{ fontWeight: 600, marginTop: 2 }}>
              {citation.section_path?.join(' ') || '—'}
            </div>
          </div>
          <div>
            <div className="muted text-sm">Nội dung đoạn trích</div>
            <div className="chunk-content mt-8">{citation.snippet}</div>
          </div>
          <div className="row">
            <Tag>Điểm liên quan: {citation.score.toFixed(3)}</Tag>
            <Tag className="mono">Chunk: {citation.chunk_id}</Tag>
          </div>
        </div>
      ) : null}
    </Modal>
  )
}
