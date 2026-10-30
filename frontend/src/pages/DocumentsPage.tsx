import { useEffect, useMemo, useState } from 'react'
import {
  DeleteOutlined,
  EyeOutlined,
  FileTextOutlined,
  ReloadOutlined,
  SearchOutlined,
  UploadOutlined,
} from '@ant-design/icons'
import { App as AntApp, Button, Input, Popconfirm, Select, Table, Tooltip } from 'antd'
import type { TableProps } from 'antd'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { documentsApi } from '@/api/documents'
import type { DocumentSummary } from '@/api/types'
import { useAuth } from '@/auth/AuthContext'
import { KpiCard } from '@/components/ui/KpiCard'
import { PageHeader } from '@/components/ui/PageHeader'
import { EmptyState, ErrorState } from '@/components/ui/States'
import { StatusTag } from '@/components/ui/Tags'
import { DOCUMENT_CATEGORIES, STATUS_LABELS } from '@/lib/constants'
import { formatNumber } from '@/lib/format'
import { formatDateTime, formatRelative } from '@/lib/dates'
import { usePageTitle } from '@/lib/usePageTitle'

const DOCUMENT_STATUSES = ['UPLOADED', 'PROCESSING', 'INGESTED', 'FAILED'] as const

export function DocumentsPage() {
  usePageTitle('Kho tài liệu')
  const { session } = useAuth()
  const navigate = useNavigate()
  const [searchParams, setSearchParams] = useSearchParams()
  const { message } = AntApp.useApp()
  const queryClient = useQueryClient()

  const categoryParam = searchParams.get('category') ?? ''
  const statusParam = searchParams.get('status') ?? ''
  const [query, setQuery] = useState('')
  const [category, setCategory] = useState(categoryParam)
  const [status, setStatus] = useState(statusParam)
  const [selectedRowKeys, setSelectedRowKeys] = useState<string[]>([])

  useEffect(() => {
    setCategory(categoryParam)
    setStatus(statusParam)
  }, [categoryParam, statusParam])

  useEffect(() => {
    setSelectedRowKeys([])
  }, [query, category, status])

  const documentsQuery = useQuery({
    queryKey: ['documents'],
    queryFn: () => documentsApi.list({}),
  })

  const retryMutation = useMutation({
    mutationFn: (versionId: string) => documentsApi.retry(versionId),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['documents'] })
      message.success('Đã đưa phiên bản vào hàng đợi nạp lại.')
    },
    onError: (error) => message.error(error.message),
  })

  const deleteMutation = useMutation({
    mutationFn: (ids: string[]) => documentsApi.delete(ids),
    onSuccess: (deleted) => {
      setSelectedRowKeys([])
      void queryClient.invalidateQueries({ queryKey: ['documents'] })
      message.success(`Đã xóa ${deleted} tài liệu khỏi kho tri thức.`)
    },
    onError: (error) => message.error(error.message),
  })

  const documents = documentsQuery.data?.items ?? []

  const counts = useMemo(
    () => ({
      total: documents.length,
      ingested: documents.filter(
        (document) => document.currentVersion.status === 'INGESTED',
      ).length,
      processing: documents.filter(
        (document) => document.currentVersion.status === 'PROCESSING',
      ).length,
      failed: documents.filter(
        (document) => document.currentVersion.status === 'FAILED',
      ).length,
    }),
    [documents],
  )

  const filtered = documents.filter((document) => {
    const search = query.trim().toLowerCase()
    const matchesSearch =
      !search ||
      document.title.toLowerCase().includes(search) ||
      document.documentCode.toLowerCase().includes(search)
    const matchesCategory = !category || document.category === category
    const matchesStatus = !status || document.currentVersion.status === status
    return matchesSearch && matchesCategory && matchesStatus
  })

  const updateParams = (nextCategory: string, nextStatus: string) => {
    const next = new URLSearchParams()
    if (nextCategory) next.set('category', nextCategory)
    if (nextStatus) next.set('status', nextStatus)
    setSearchParams(next, { replace: true })
  }

  const clearFilters = () => {
    setQuery('')
    setCategory('')
    setStatus('')
    setSearchParams({}, { replace: true })
  }

  const columns: TableProps<DocumentSummary>['columns'] = [
    {
      title: 'Tài liệu',
      dataIndex: 'title',
      key: 'title',
      render: (_, document) => (
        <div className="table-title-cell">
          <span className="table-title">{document.title}</span>
          <span className="table-sub">
            {document.documentCode} · {document.category}
          </span>
          <span className="mobile-only" style={{ marginTop: 2 }}>
            <StatusTag status={document.currentVersion.status} />
          </span>
        </div>
      ),
    },
    {
      title: 'Phiên bản',
      key: 'version',
      width: 150,
      responsive: ['md'],
      render: (_, document) => (
        <div className="row" style={{ gap: 6 }}>
          <span className="mono">v{document.currentVersion.versionNumber}</span>
          <StatusTag status={document.currentVersion.status} />
        </div>
      ),
    },
    {
      title: 'Chunk',
      key: 'chunks',
      width: 90,
      align: 'right',
      responsive: ['xl'],
      render: (_, document) =>
        document.currentVersion.chunkCount > 0
          ? formatNumber(document.currentVersion.chunkCount)
          : '—',
    },
    {
      title: 'Trang',
      key: 'pages',
      width: 80,
      align: 'right',
      responsive: ['xl'],
      render: (_, document) => formatNumber(document.currentVersion.pageCount),
    },
    {
      title: 'Cập nhật',
      dataIndex: 'updatedAt',
      key: 'updatedAt',
      width: 150,
      responsive: ['md'],
      render: (value: string) => (
        <Tooltip title={formatDateTime(value)}>
          <span className="muted">{formatRelative(value)}</span>
        </Tooltip>
      ),
    },
    {
      title: 'Người tạo',
      dataIndex: 'createdBy',
      key: 'createdBy',
      width: 150,
      responsive: ['xxl'],
    },
    {
      title: '',
      key: 'actions',
      width: 150,
      align: 'right',
      render: (_, document) => (
        <div className="row" style={{ justifyContent: 'flex-end', gap: 4 }}>
          {session?.role === 'ADMIN' &&
          document.currentVersion.status === 'FAILED' ? (
            <Button
              size="small"
              icon={<ReloadOutlined />}
              loading={
                retryMutation.isPending &&
                retryMutation.variables === document.currentVersion.id
              }
              onClick={(event) => {
                event.stopPropagation()
                retryMutation.mutate(document.currentVersion.id)
              }}
            >
              Nạp lại
            </Button>
          ) : null}
          <Button
            size="small"
            icon={<EyeOutlined />}
            onClick={(event) => {
              event.stopPropagation()
              navigate(`/documents/${document.id}`)
            }}
          >
            Xem
          </Button>
        </div>
      ),
    },
  ]

  const hasFilters = Boolean(query || category || status)

  return (
    <div>
      <PageHeader
        title="Kho tài liệu"
        description="Quản lý tài liệu nội bộ, theo dõi phiên bản và trạng thái nạp vào kho vector."
        actions={
          session?.role === 'ADMIN' ? (
            <Button
              type="primary"
              icon={<UploadOutlined />}
              onClick={() => navigate('/documents/upload')}
            >
              Tải tài liệu
            </Button>
          ) : null
        }
      />

      <div className="kpi-grid">
        <KpiCard label="Tổng tài liệu" value={counts.total} hint="Trong kho tri thức" />
        <KpiCard label="Đã nạp" value={counts.ingested} hint="Sẵn sàng tìm kiếm" />
        <KpiCard
          label="Đang xử lý"
          value={counts.processing}
          hint="Pipeline đang chạy"
        />
        <KpiCard label="Nạp lỗi" value={counts.failed} hint="Cần kiểm tra" />
      </div>

      <div className="toolbar">
        <Input
          prefix={<SearchOutlined />}
          placeholder="Tìm theo tiêu đề hoặc mã tài liệu"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          allowClear
          className="toolbar__search"
          aria-label="Tìm tài liệu"
        />
        <Select
          allowClear
          placeholder="Danh mục"
          value={category || undefined}
          onChange={(value) => {
            const next = value ?? ''
            setCategory(next)
            updateParams(next, status)
          }}
          options={DOCUMENT_CATEGORIES.map((item) => ({ value: item, label: item }))}
          className="toolbar__select"
        />
        <Select
          allowClear
          placeholder="Trạng thái"
          value={status || undefined}
          onChange={(value) => {
            const next = value ?? ''
            setStatus(next)
            updateParams(category, next)
          }}
          options={DOCUMENT_STATUSES.map((item) => ({
            value: item,
            label: STATUS_LABELS[item],
          }))}
          className="toolbar__select"
        />
        {hasFilters ? (
          <Button type="text" onClick={clearFilters}>
            Xóa bộ lọc
          </Button>
        ) : null}
        {selectedRowKeys.length > 0 ? (
          <Popconfirm
            title={`Xóa ${selectedRowKeys.length} tài liệu đã chọn?`}
            description="Toàn bộ phiên bản, đoạn trích, tệp gốc và vector sẽ bị xóa vĩnh viễn."
            okText="Xóa"
            cancelText="Hủy"
            okButtonProps={{ danger: true }}
            onConfirm={() => deleteMutation.mutate(selectedRowKeys)}
          >
            <Button
              danger
              icon={<DeleteOutlined />}
              loading={deleteMutation.isPending}
            >
              Xóa đã chọn ({selectedRowKeys.length})
            </Button>
          </Popconfirm>
        ) : null}
        <div className="toolbar__right muted text-sm">
          {filtered.length} / {documents.length} tài liệu
        </div>
      </div>

      {documentsQuery.isError ? (
        <ErrorState
          message="Không tải được danh sách tài liệu."
          onRetry={() => documentsQuery.refetch()}
        />
      ) : documents.length === 0 && !documentsQuery.isLoading ? (
        <EmptyState
          title="Kho tài liệu đang trống"
          description="Tải tài liệu PDF đầu tiên để bắt đầu xây dựng kho tri thức."
          action={
            session?.role === 'ADMIN' ? (
              <Button type="primary" icon={<UploadOutlined />} onClick={() => navigate('/documents/upload')}>
                Tải tài liệu
              </Button>
            ) : null
          }
        />
      ) : (
        <div className="table-card">
          <Table<DocumentSummary>
            rowKey="id"
            columns={columns}
            dataSource={filtered}
            loading={documentsQuery.isLoading}
            rowSelection={{
              selectedRowKeys,
              onChange: (keys) => setSelectedRowKeys(keys as string[]),
              getCheckboxProps: (document) => ({
                disabled: document.currentVersion.status === 'PROCESSING',
              }),
            }}
            pagination={{
              pageSize: 8,
              showSizeChanger: true,
              showTotal: (total) => `${total} tài liệu`,
            }}
            onRow={(document) => ({
              onClick: () => navigate(`/documents/${document.id}`),
              style: { cursor: 'pointer' },
            })}
            locale={{
              emptyText: (
                <EmptyState
                  title="Không có tài liệu phù hợp"
                  description="Thử thay đổi từ khóa hoặc bộ lọc."
                  action={
                    hasFilters ? (
                      <Button onClick={clearFilters}>Xóa bộ lọc</Button>
                    ) : null
                  }
                />
              ),
            }}
          />
        </div>
      )}

      <div className="docs-footnote">
        <FileTextOutlined /> Chỉ tài liệu ở trạng thái <strong>Đã nạp</strong> mới
        được dùng để trả lời và tìm kiếm.
      </div>
    </div>
  )
}
