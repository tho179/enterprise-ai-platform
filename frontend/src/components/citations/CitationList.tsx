import { FileTextOutlined, LoadingOutlined } from '@ant-design/icons'
import { Alert, Modal, Spin, Tag } from 'antd'
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

type PdfState =
  | { status: 'loading' }
  | { status: 'ready'; url: string }
  | { status: 'error'; message: string }

function ChunkPdfViewer({ citation }: { citation: Citation }) {
  const [pdf, setPdf] = useState<PdfState>({ status: 'loading' })

  useEffect(() => {
    let revoked: string | null = null
    if (!citation.document_id || !citation.chunk_id) {
      setPdf({
        status: 'error',
        message: 'Trích dẫn này thiếu mã tài liệu để mở PDF.',
      })
      return
    }
    setPdf({ status: 'loading' })
    documentsApi
      .chunkPdfUrl(citation.document_id, citation.chunk_id)
      .then((url) => {
        revoked = url
        setPdf({ status: 'ready', url })
      })
      .catch((error) => {
        setPdf({ status: 'error', message: normalizeError(error).message })
      })
    return () => {
      if (revoked) URL.revokeObjectURL(revoked)
    }
  }, [citation.document_id, citation.chunk_id])

  if (pdf.status === 'loading') {
    return (
      <div className="citation-preview citation-preview--loading">
        <Spin indicator={<LoadingOutlined spin />} tip="Đang tạo PDF với đoạn trích tô vàng…" />
      </div>
    )
  }
  if (pdf.status === 'error') {
    return (
      <Alert
        type="warning"
        showIcon
        title="Không mở được PDF"
        description={pdf.message}
      />
    )
  }
  const page = citation.pages.match(/\d+/)?.[0] ?? '1'
  return (
    <div className="citation-preview">
      <iframe
        title={`PDF gốc đã tô vàng: ${citation.pages}`}
        src={`${pdf.url}#page=${page}&zoom=page-width`}
      />
      <div className="citation-preview__foot">
        <span className="muted">PDF gốc đã tô vàng đoạn dẫn chứng.</span>
        <a href={pdf.url} target="_blank" rel="noopener noreferrer">
          Mở tab mới
        </a>
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
      width={960}
      styles={{ body: { maxHeight: '76vh', overflowY: 'auto' } }}
      footer={
        citation?.document_id ? (
          <Link to={`/documents/${citation.document_id}`} onClick={onClose}>
            <Tag color="blue" style={{ cursor: 'pointer', margin: 0 }}>
              <FileTextOutlined /> Thông tin tài liệu gốc
            </Tag>
          </Link>
        ) : null
      }
    >
      {citation ? (
        <div className="stack" style={{ gap: 14 }}>
          <div>
            <div className="muted text-sm">PDF gốc với đoạn trích được tô vàng</div>
            <ChunkPdfViewer citation={citation} />
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
