import { useEffect, useRef, useState } from 'react'
import {
  ArrowLeftOutlined,
  CloudUploadOutlined,
  FilePdfOutlined,
  InboxOutlined,
  ReloadOutlined,
} from '@ant-design/icons'
import {
  Alert,
  App as AntApp,
  Button,
  Collapse,
  Descriptions,
  Input,
  Modal,
  Skeleton,
  Table,
  Tabs,
  Tag,
  Upload,
} from 'antd'
import type { TableProps } from 'antd'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useNavigate, useParams } from 'react-router-dom'
import { documentsApi } from '@/api/documents'
import type { DocumentVersion } from '@/api/types'
import { useAuth } from '@/auth/AuthContext'
import { PageHeader } from '@/components/ui/PageHeader'
import { ErrorState } from '@/components/ui/States'
import { StatusTag } from '@/components/ui/Tags'
import { MAX_UPLOAD_BYTES } from '@/lib/constants'
import { formatDateTime } from '@/lib/dates'
import { formatNumber } from '@/lib/format'
import { usePageTitle } from '@/lib/usePageTitle'

export function DocumentDetailPage() {
  const { id } = useParams<{ id: string }>()
  const { session } = useAuth()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const { message } = AntApp.useApp()
  const [chunkQuery, setChunkQuery] = useState('')
  const [uploadOpen, setUploadOpen] = useState(false)
  const [versionFile, setVersionFile] = useState<File | null>(null)
  const [uploadError, setUploadError] = useState<string | null>(null)
  const [tab, setTab] = useState('content')
  const previousStatus = useRef<string | undefined>(undefined)

  const documentQuery = useQuery({
    queryKey: ['document', id],
    queryFn: () => documentsApi.get(id as string),
    enabled: Boolean(id),
    refetchInterval: (query) =>
      query.state.data?.currentVersion.status === 'PROCESSING' ? 2000 : false,
  })

  const document = documentQuery.data
  const isAdmin = session?.role === 'ADMIN'
  const currentStatus = document?.currentVersion.status

  usePageTitle(document?.title ? document.title : 'Chi tiết tài liệu')

  const chunksQuery = useQuery({
    queryKey: ['document', id, 'chunks'],
    queryFn: () => documentsApi.chunks(id as string),
    enabled: Boolean(id),
  })

  useEffect(() => {
    if (
      previousStatus.current === 'PROCESSING' &&
      currentStatus &&
      currentStatus !== 'PROCESSING'
    ) {
      void queryClient.invalidateQueries({ queryKey: ['documents'] })
      void queryClient.invalidateQueries({ queryKey: ['document', id, 'chunks'] })
    }
    previousStatus.current = currentStatus
  }, [currentStatus, id, queryClient])

  const refresh = () => {
    void queryClient.invalidateQueries({ queryKey: ['document', id] })
    void queryClient.invalidateQueries({ queryKey: ['documents'] })
    void queryClient.invalidateQueries({ queryKey: ['document', id, 'chunks'] })
  }

  const retryMutation = useMutation({
    mutationFn: (versionId: string) => documentsApi.retry(versionId),
    onSuccess: () => {
      message.success('Đã đưa phiên bản vào hàng đợi nạp lại.')
      refresh()
    },
    onError: (error) => message.error(error.message),
  })

  const setCurrentMutation = useMutation({
    mutationFn: (versionId: string) => documentsApi.setCurrent(versionId),
    onSuccess: () => {
      message.success('Đã đặt phiên bản làm hiện hành.')
      refresh()
    },
    onError: (error) => message.error(error.message),
  })

  const uploadMutation = useMutation({
    mutationFn: async () => {
      if (!versionFile || !id) throw new Error('Chưa chọn tệp PDF.')
      const formData = new FormData()
      formData.append('file', versionFile)
      return documentsApi.uploadVersion(id, formData)
    },
    onSuccess: () => {
      message.success('Đã bắt đầu nạp phiên bản mới. Theo dõi trạng thái tại đây.')
      setUploadOpen(false)
      setVersionFile(null)
      setUploadError(null)
      setTab('versions')
      refresh()
    },
    onError: (error) => setUploadError(error.message),
  })

  if (documentQuery.isError) {
    return (
      <div>
        <PageHeader
          title="Không tìm thấy tài liệu"
          description="Tài liệu có thể đã bị xóa hoặc bạn không có quyền truy cập."
          actions={
            <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/documents')}>
              Về kho tài liệu
            </Button>
          }
        />
        <ErrorState
          message="Không tải được tài liệu."
          onRetry={() => documentQuery.refetch()}
        />
      </div>
    )
  }

  if (documentQuery.isLoading || !document) {
    return <Skeleton active paragraph={{ rows: 10 }} />
  }

  const versionColumns: TableProps<DocumentVersion>['columns'] = [
    {
      title: 'Phiên bản',
      key: 'version',
      render: (_, version) => (
        <div className="row" style={{ gap: 6 }}>
          <span className="mono">v{version.versionNumber}</span>
          {version.isCurrent ? <Tag color="blue">Hiện hành</Tag> : null}
        </div>
      ),
    },
    {
      title: 'Trạng thái',
      key: 'status',
      render: (_, version) => <StatusTag status={version.status} />,
    },
    {
      title: 'Chunk',
      dataIndex: 'chunkCount',
      key: 'chunkCount',
      align: 'right',
      render: (value: number) => (value > 0 ? formatNumber(value) : '—'),
    },
    {
      title: 'Trang',
      dataIndex: 'pageCount',
      key: 'pageCount',
      align: 'right',
      render: (value: number) => formatNumber(value),
    },
    {
      title: 'Thời điểm nạp',
      dataIndex: 'createdAt',
      key: 'createdAt',
      render: (value: string) => formatDateTime(value),
    },
    {
      title: 'Mã băm',
      dataIndex: 'fileHash',
      key: 'fileHash',
      responsive: ['lg'],
      render: (value: string) => (
        <span className="mono" title={value}>
          {value.slice(0, 12)}…
        </span>
      ),
    },
    {
      title: '',
      key: 'actions',
      align: 'right',
      render: (_, version) => {
        if (!isAdmin) return null
        if (version.status === 'FAILED') {
          return (
            <Button
              size="small"
              icon={<ReloadOutlined />}
              loading={
                retryMutation.isPending &&
                retryMutation.variables === version.id
              }
              onClick={() => retryMutation.mutate(version.id)}
            >
              Nạp lại
            </Button>
          )
        }
        if (version.status === 'INGESTED' && !version.isCurrent) {
          return (
            <Button
              size="small"
              loading={
                setCurrentMutation.isPending &&
                setCurrentMutation.variables === version.id
              }
              onClick={() => setCurrentMutation.mutate(version.id)}
            >
              Đặt hiện hành
            </Button>
          )
        }
        return null
      },
    },
  ]

  const chunks = chunksQuery.data ?? []
  const filteredChunks = chunks.filter((chunk) => {
    const search = chunkQuery.trim().toLowerCase()
    if (!search) return true
    return (
      chunk.content.toLowerCase().includes(search) ||
      chunk.sectionPath.join(' ').toLowerCase().includes(search)
    )
  })

  const collapseItems = filteredChunks.map((chunk) => ({
    key: chunk.id,
    label: (
      <div className="chunk-label">
        <span className="chunk-label__path">
          {chunk.sectionPath?.join(' › ') || 'Đoạn trích'}
        </span>
        <span className="chunk-label__meta">
          Trang {chunk.pageStart}
          {chunk.pageEnd !== chunk.pageStart ? ` → ${chunk.pageEnd}` : ''} ·{' '}
          <span className="mono">{chunk.vectorId}</span>
        </span>
      </div>
    ),
    children: <div className="chunk-content">{chunk.content}</div>,
  }))

  const hasProcessingVersion = document.versions.some(
    (version) => version.status === 'PROCESSING',
  )

  return (
    <div>
      <Button
        type="text"
        icon={<ArrowLeftOutlined />}
        onClick={() => navigate('/documents')}
        style={{ paddingLeft: 0, marginBottom: 8 }}
      >
        Kho tài liệu
      </Button>
      <PageHeader
        title={
          <span className="row row--wrap" style={{ gap: 10 }}>
            {document.title}
            <StatusTag status={document.currentVersion.status} />
          </span>
        }
        description={`${document.documentCode} · ${document.category} · Cập nhật ${formatDateTime(document.updatedAt)}`}
        actions={
          isAdmin ? (
            <>
              {document.currentVersion.status === 'FAILED' ? (
                <Button
                  icon={<ReloadOutlined />}
                  loading={retryMutation.isPending}
                  onClick={() => retryMutation.mutate(document.currentVersion.id)}
                >
                  Nạp lại phiên bản lỗi
                </Button>
              ) : null}
              <Button
                type="primary"
                icon={<CloudUploadOutlined />}
                disabled={hasProcessingVersion}
                onClick={() => {
                  setUploadError(null)
                  setUploadOpen(true)
                }}
              >
                Tải phiên bản mới
              </Button>
            </>
          ) : null
        }
      />

      {document.currentVersion.status === 'FAILED' ? (
        <Alert
          type="error"
          showIcon
          style={{ marginBottom: 16 }}
          title="Phiên bản hiện hành nạp thất bại"
          description={
            document.currentVersion.errorMessage ??
            'Pipeline dừng trước khi hoàn tất. Kiểm tra dịch vụ embedding/Qdrant rồi nạp lại.'
          }
        />
      ) : null}

      {document.currentVersion.status === 'PROCESSING' ? (
        <Alert
          type="info"
          showIcon
          style={{ marginBottom: 16 }}
          title="Tài liệu đang được nạp"
          description="Trạng thái tự động cập nhật. Bạn có thể rời trang và quay lại sau."
        />
      ) : null}

      <div className="doc-meta-grid">
        <div className="doc-meta">
          <div className="doc-meta__label">Danh mục</div>
          <div className="doc-meta__value">{document.category}</div>
        </div>
        <div className="doc-meta">
          <div className="doc-meta__label">Phiên bản hiện hành</div>
          <div className="doc-meta__value">v{document.currentVersion.versionNumber}</div>
        </div>
        <div className="doc-meta">
          <div className="doc-meta__label">Đoạn trích</div>
          <div className="doc-meta__value">
            {formatNumber(document.currentVersion.chunkCount)} chunk ·{' '}
            {formatNumber(document.currentVersion.pageCount)} trang
          </div>
        </div>
        <div className="doc-meta">
          <div className="doc-meta__label">Người tạo</div>
          <div className="doc-meta__value">{document.createdBy}</div>
        </div>
      </div>

      <Tabs
        activeKey={tab}
        onChange={setTab}
        items={[
          {
            key: 'content',
            label: `Nội dung đã nạp (${chunks.length})`,
            children: (
              <div>
                <div className="toolbar">
                  <Input
                    placeholder="Tìm trong các đoạn trích…"
                    value={chunkQuery}
                    onChange={(event) => setChunkQuery(event.target.value)}
                    allowClear
                    style={{ maxWidth: 360 }}
                  />
                  <div className="toolbar__right muted text-sm">
                    {filteredChunks.length} đoạn
                  </div>
                </div>
                {chunksQuery.isLoading ? (
                  <Skeleton active paragraph={{ rows: 6 }} />
                ) : collapseItems.length > 0 ? (
                  <Collapse size="small" items={collapseItems} />
                ) : (
                  <ErrorState
                    message={
                      document.currentVersion.status === 'INGESTED'
                        ? 'Không có đoạn trích phù hợp.'
                        : 'Chưa có nội dung được nạp cho tài liệu này.'
                    }
                  />
                )}
              </div>
            ),
          },
          {
            key: 'versions',
            label: `Phiên bản (${document.versions.length})`,
            children: (
              <div className="table-card">
                <Table<DocumentVersion>
                  rowKey="id"
                  columns={versionColumns}
                  dataSource={document.versions}
                  pagination={false}
                  scroll={{ x: 860 }}
                />
              </div>
            ),
          },
          {
            key: 'info',
            label: 'Thông tin',
            children: (
              <div className="panel">
                <div className="panel__body">
                  <Descriptions
                    column={2}
                    size="small"
                    items={[
                      { key: 'code', label: 'Mã tài liệu', children: document.documentCode },
                      { key: 'title', label: 'Tiêu đề', children: document.title },
                      { key: 'category', label: 'Danh mục', children: document.category },
                      { key: 'createdBy', label: 'Người tạo', children: document.createdBy },
                      {
                        key: 'createdAt',
                        label: 'Ngày tạo',
                        children: formatDateTime(document.createdAt),
                      },
                      {
                        key: 'updatedAt',
                        label: 'Cập nhật gần nhất',
                        children: formatDateTime(document.updatedAt),
                      },
                      {
                        key: 'hash',
                        label: 'Mã băm tệp',
                        children: (
                          <span className="mono">{document.currentVersion.fileHash}</span>
                        ),
                      },
                      {
                        key: 'pages',
                        label: 'Số trang',
                        children: formatNumber(document.currentVersion.pageCount),
                      },
                    ]}
                  />
                </div>
              </div>
            ),
          },
        ]}
      />

      <Modal
        title="Tải phiên bản mới"
        open={uploadOpen}
        onCancel={() => {
          if (uploadMutation.isPending) return
          setUploadOpen(false)
          setVersionFile(null)
          setUploadError(null)
        }}
        okText="Bắt đầu nạp"
        cancelText="Hủy"
        confirmLoading={uploadMutation.isPending}
        onOk={() => {
          if (!versionFile) {
            setUploadError('Vui lòng chọn tệp PDF.')
            return
          }
          if (!versionFile.name.toLowerCase().endsWith('.pdf')) {
            setUploadError('Chỉ hỗ trợ tệp PDF.')
            return
          }
          if (versionFile.size > MAX_UPLOAD_BYTES) {
            setUploadError('Tệp vượt quá 25 MB.')
            return
          }
          uploadMutation.mutate()
        }}
        okButtonProps={{ icon: <CloudUploadOutlined /> }}
      >
        <p className="muted text-sm" style={{ marginTop: 0 }}>
          Phiên bản mới sẽ được nạp song song và chỉ thay thế bản hiện hành sau khi
          pipeline hoàn tất.
        </p>
        {uploadError ? (
          <Alert type="error" showIcon title={uploadError} style={{ marginBottom: 12 }} />
        ) : null}
        <Upload.Dragger
          accept=".pdf,application/pdf"
          maxCount={1}
          showUploadList={false}
          beforeUpload={(file) => {
            setUploadError(null)
            if (!file.name.toLowerCase().endsWith('.pdf')) {
              setVersionFile(null)
              setUploadError('Chỉ hỗ trợ tệp PDF.')
              return false
            }
            if (file.size > MAX_UPLOAD_BYTES) {
              setVersionFile(null)
              setUploadError('Tệp vượt quá 25 MB.')
              return false
            }
            setVersionFile(file)
            return false
          }}
        >
          <p className="ant-upload-drag-icon">
            <InboxOutlined />
          </p>
          <p className="ant-upload-text">Chọn hoặc kéo tệp PDF vào đây</p>
          <p className="ant-upload-hint">Tối đa 25 MB, chỉ hỗ trợ định dạng PDF.</p>
        </Upload.Dragger>
        {versionFile ? (
          <div className="upload-file mt-12">
            <FilePdfOutlined style={{ color: 'var(--danger)' }} />
            <div className="grow">
              <div style={{ fontWeight: 500 }}>{versionFile.name}</div>
              <div className="muted text-sm">
                {formatNumber(Math.round(versionFile.size / 1024))} KB
              </div>
            </div>
            <Button
              size="small"
              onClick={() => setVersionFile(null)}
              disabled={uploadMutation.isPending}
            >
              Bỏ chọn
            </Button>
          </div>
        ) : null}
        {versionFile && versionFile.size > MAX_UPLOAD_BYTES ? (
          <Alert
            type="warning"
            showIcon
            title="Tệp vượt quá 25 MB."
            style={{ marginTop: 12 }}
          />
        ) : null}
      </Modal>
    </div>
  )
}
