import { LoadingOutlined, MessageOutlined } from '@ant-design/icons'
import { Alert, Button, Modal, Spin } from 'antd'
import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { documentsApi } from '@/api/documents'
import { normalizeError } from '@/api/errors'

export interface PdfTarget {
  id: string
  title: string
}

type FileState =
  | { status: 'loading' }
  | { status: 'ready'; url: string }
  | { status: 'error'; message: string }

function DocumentPdf({ id, title }: PdfTarget) {
  const [file, setFile] = useState<FileState>({ status: 'loading' })

  useEffect(() => {
    let url: string | null = null
    let cancelled = false
    documentsApi
      .fileUrl(id)
      .then((objectUrl) => {
        if (cancelled) {
          URL.revokeObjectURL(objectUrl)
          return
        }
        url = objectUrl
        setFile({ status: 'ready', url: objectUrl })
      })
      .catch((error) => {
        if (!cancelled) setFile({ status: 'error', message: normalizeError(error).message })
      })
    return () => {
      cancelled = true
      if (url) URL.revokeObjectURL(url)
    }
  }, [id])

  if (file.status === 'loading') {
    return (
      <div className="citation-preview citation-preview--loading">
        <Spin indicator={<LoadingOutlined spin />} tip="Đang tải PDF…" />
      </div>
    )
  }
  if (file.status === 'error') {
    return <Alert type="warning" showIcon title="Không mở được PDF" description={file.message} />
  }
  return (
    <div className="citation-preview">
      <iframe className="document-pdf__frame" title={`PDF: ${title}`} src={file.url} />
      <div className="citation-preview__foot">
        <span className="muted">Phiên bản hiện hành</span>
        <a href={file.url} target="_blank" rel="noopener noreferrer">
          Mở tab mới
        </a>
      </div>
    </div>
  )
}

/** Original PDF of a document, with a shortcut to ask the assistant about it. */
export function DocumentPdfModal({
  target,
  onClose,
  onAsk,
}: {
  target: PdfTarget | null
  onClose: () => void
  onAsk?: (target: PdfTarget) => void
}) {
  return (
    <Modal
      open={target !== null}
      onCancel={onClose}
      title={<span className="document-pdf__title">{target?.title}</span>}
      width={960}
      destroyOnHidden
      // "Hỏi về tài liệu này" moves focus to the chat composer; returning it to
      // the sidebar link on close would steal it back.
      focusTriggerAfterClose={false}
      footer={
        target ? (
          <div className="document-pdf__actions">
            <Link to={`/documents/${target.id}`} onClick={onClose}>
              Chi tiết tài liệu
            </Link>
            {onAsk ? (
              <Button type="primary" icon={<MessageOutlined />} onClick={() => onAsk(target)}>
                Hỏi về tài liệu này
              </Button>
            ) : null}
          </div>
        ) : null
      }
    >
      {target ? <DocumentPdf key={target.id} id={target.id} title={target.title} /> : null}
    </Modal>
  )
}
