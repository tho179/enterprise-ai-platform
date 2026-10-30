import { useEffect, useRef, useState } from 'react'
import {
  ArrowLeftOutlined,
  CloudUploadOutlined,
  FilePdfOutlined,
  FileTextOutlined,
  InboxOutlined,
  ReloadOutlined,
} from '@ant-design/icons'
import {
  Alert,
  App as AntApp,
  Button,
  Form,
  Input,
  Progress,
  Result,
  Select,
  Steps,
  Tag,
  Upload,
} from 'antd'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { documentsApi } from '@/api/documents'
import type { UploadTicket } from '@/api/types'
import { PageHeader } from '@/components/ui/PageHeader'
import { Panel } from '@/components/ui/Panel'
import { DOCUMENT_CATEGORIES, MAX_UPLOAD_BYTES } from '@/lib/constants'
import { formatNumber } from '@/lib/format'
import { usePageTitle } from '@/lib/usePageTitle'

interface UploadFormValues {
  documentCode: string
  title: string
  category: string
}

const PIPELINE_STEPS = [
  { title: 'Tải tệp lên', description: 'Lưu PDF tạm và kiểm tra định dạng.' },
  { title: 'Trích xuất văn bản', description: 'Đọc cấu trúc trang và tiêu đề mục.' },
  { title: 'Chia đoạn', description: 'Chunk theo mục, giữ ngữ cảnh và số trang.' },
  { title: 'Tạo embedding', description: 'Vector hóa đoạn trích bằng model đa ngữ.' },
  { title: 'Ghi kho vector', description: 'Ghi Qdrant và đánh dấu phiên bản hiện hành.' },
]

export function UploadPage() {
  usePageTitle('Tải tài liệu')
  const [form] = Form.useForm<UploadFormValues>()
  const { message } = AntApp.useApp()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [file, setFile] = useState<File | null>(null)
  const [fileError, setFileError] = useState<string | null>(null)
  const [task, setTask] = useState<UploadTicket | null>(null)
  const invalidatedRef = useRef(false)

  const uploadMutation = useMutation({
    mutationFn: (formData: FormData) => documentsApi.upload(formData),
    onSuccess: (ticket) => {
      setTask(ticket)
      invalidatedRef.current = false
    },
  })

  const statusQuery = useQuery({
    queryKey: ['ingestion', task?.taskId],
    queryFn: () => documentsApi.ingestionStatus(task?.taskId as string),
    enabled: Boolean(task?.taskId),
    refetchInterval: (query) =>
      query.state.data?.status === 'PROCESSING' ? 1400 : false,
    retry: 1,
  })

  const status = statusQuery.data
  const phase = uploadMutation.isPending
    ? 'uploading'
    : task
      ? (status?.status ?? 'PROCESSING')
      : 'idle'
  const failed = phase === 'FAILED' || statusQuery.isError
  const succeeded = phase === 'INGESTED'
  const activeStep = succeeded ? 4 : task ? Math.min(status?.step ?? 1, 3) : 0

  useEffect(() => {
    if (succeeded && !invalidatedRef.current) {
      invalidatedRef.current = true
      void queryClient.invalidateQueries({ queryKey: ['documents'] })
      if (task?.documentId) {
        void queryClient.invalidateQueries({ queryKey: ['document', task.documentId] })
      }
      message.success('Tài liệu đã nạp thành công vào kho tri thức.')
    }
  }, [succeeded, queryClient, task?.documentId, message])

  const handleSubmit = (values: UploadFormValues) => {
    if (uploadMutation.isPending || task) return
    if (!file) {
      setFileError('Vui lòng chọn tệp PDF.')
      return
    }
    if (!file.name.toLowerCase().endsWith('.pdf')) {
      setFileError('Chỉ hỗ trợ tệp PDF.')
      return
    }
    if (file.size > MAX_UPLOAD_BYTES) {
      setFileError('Tệp vượt quá 25 MB.')
      return
    }
    setFileError(null)
    const formData = new FormData()
    formData.append('documentCode', values.documentCode.trim().toUpperCase())
    formData.append('title', values.title.trim())
    formData.append('category', values.category)
    formData.append('file', file)
    uploadMutation.mutate(formData)
  }

  const resetUpload = () => {
    setTask(null)
    setFile(null)
    setFileError(null)
    uploadMutation.reset()
    form.resetFields()
    invalidatedRef.current = false
  }

  const percent = succeeded
    ? 100
    : failed
      ? 100
      : Math.min(90, 12 + activeStep * 20)

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
        title="Tải tài liệu"
        description="Đưa tài liệu PDF mới vào pipeline nạp tri thức. Tài liệu chỉ được dùng để trả lời sau khi pipeline hoàn tất."
        actions={
          <Button icon={<FileTextOutlined />} onClick={() => navigate('/documents')}>
            Danh sách tài liệu
          </Button>
        }
      />

      <div className="upload-layout">
        <div className="stack">
          {succeeded ? (
            <Panel title="Kết quả nạp tài liệu">
              <Result
                status="success"
                title="Nạp tài liệu thành công"
                subTitle={`Đã tạo ${formatNumber(status?.chunkCount ?? 0)} đoạn trích và đưa tài liệu vào kho vector.`}
                extra={[
                  <Button
                    key="view"
                    type="primary"
                    icon={<FileTextOutlined />}
                    onClick={() =>
                      navigate(
                        task?.documentId
                          ? `/documents/${task.documentId}`
                          : '/documents',
                      )
                    }
                  >
                    Xem tài liệu
                  </Button>,
                  <Button key="more" onClick={resetUpload}>
                    Tải tài liệu khác
                  </Button>,
                ]}
              />
            </Panel>
          ) : failed ? (
            <Panel title="Kết quả nạp tài liệu">
              <Result
                status="error"
                title="Nạp tài liệu thất bại"
                subTitle={
                  statusQuery.isError
                    ? 'Không kiểm tra được trạng thái nạp. Kiểm tra kết nối dịch vụ AI rồi thử lại.'
                    : status?.message ??
                      'Pipeline dừng trước khi hoàn tất. Kiểm tra dịch vụ AI và kho vector.'
                }
                extra={[
                  <Button
                    key="retry"
                    type="primary"
                    icon={<ReloadOutlined />}
                    onClick={resetUpload}
                  >
                    Thử lại
                  </Button>,
                  <Button key="back" onClick={() => navigate('/documents')}>
                    Về kho tài liệu
                  </Button>,
                ]}
              />
            </Panel>
          ) : (
            <Panel title="Thông tin tài liệu">
              {task && !succeeded ? (
                <div style={{ marginBottom: 18 }}>
                  <Alert
                    type="info"
                    showIcon
                    title="Pipeline đang xử lý tài liệu"
                    description="Trạng thái được cập nhật tự động. Không đóng trình duyệt nếu muốn theo dõi tiến trình."
                  />
                  <Progress
                    percent={percent}
                    status="active"
                    style={{ marginTop: 14 }}
                  />
                  <div className="row row--wrap" style={{ marginTop: 8 }}>
                    <Tag color="processing">
                      {PIPELINE_STEPS[activeStep]?.title ?? 'Đang xử lý'}
                    </Tag>
                    <span className="muted text-sm">
                      Bước {activeStep + 1}/5
                    </span>
                  </div>
                </div>
              ) : null}

              <Form
                form={form}
                layout="vertical"
                requiredMark={false}
                onFinish={handleSubmit}
                initialValues={{ category: 'Nội quy' }}
                disabled={phase !== 'idle'}
              >
                <div className="form-grid">
                  <Form.Item
                    label="Mã tài liệu"
                    name="documentCode"
                    rules={[
                      { required: true, message: 'Vui lòng nhập mã tài liệu.' },
                      {
                        pattern: /^[A-Za-z0-9-]+$/,
                        message: 'Chỉ dùng chữ, số và dấu gạch ngang.',
                      },
                      { max: 32, message: 'Tối đa 32 ký tự.' },
                    ]}
                  >
                    <Input placeholder="DOC-NQLD" style={{ textTransform: 'uppercase' }} />
                  </Form.Item>
                  <Form.Item
                    label="Danh mục"
                    name="category"
                    rules={[{ required: true, message: 'Chọn danh mục.' }]}
                  >
                    <Select
                      options={DOCUMENT_CATEGORIES.map((item) => ({
                        value: item,
                        label: item,
                      }))}
                    />
                  </Form.Item>
                </div>
                <Form.Item
                  label="Tiêu đề tài liệu"
                  name="title"
                  rules={[
                    { required: true, message: 'Vui lòng nhập tiêu đề.' },
                    { min: 5, message: 'Tiêu đề tối thiểu 5 ký tự.' },
                    { max: 200, message: 'Tiêu đề tối đa 200 ký tự.' },
                  ]}
                >
                  <Input placeholder="Ví dụ: Nội quy Lao động 2026" />
                </Form.Item>

                <Form.Item label="Tệp PDF" required>
                  <Upload.Dragger
                    accept=".pdf,application/pdf"
                    maxCount={1}
                    showUploadList={false}
                    disabled={phase !== 'idle'}
                    beforeUpload={(selected) => {
                      setFile(selected)
                      setFileError(
                        selected.size > MAX_UPLOAD_BYTES
                          ? 'Tệp vượt quá 25 MB.'
                          : !selected.name.toLowerCase().endsWith('.pdf')
                            ? 'Chỉ hỗ trợ tệp PDF.'
                            : null,
                      )
                      return false
                    }}
                  >
                    <p className="ant-upload-drag-icon">
                      <InboxOutlined />
                    </p>
                    <p className="ant-upload-text">
                      Kéo thả tệp PDF vào đây hoặc bấm để chọn
                    </p>
                    <p className="ant-upload-hint">
                      Tối đa 25 MB · Hệ thống giữ nguyên cấu trúc mục và số trang
                    </p>
                  </Upload.Dragger>
                </Form.Item>

                {file ? (
                  <div className="upload-file">
                    <FilePdfOutlined style={{ color: 'var(--danger)' }} />
                    <div className="grow">
                      <div style={{ fontWeight: 500 }}>{file.name}</div>
                      <div className="muted text-sm">
                        {formatNumber(Math.round(file.size / 1024))} KB
                      </div>
                    </div>
                    <Button
                      size="small"
                      onClick={() => setFile(null)}
                      disabled={phase !== 'idle'}
                    >
                      Bỏ chọn
                    </Button>
                  </div>
                ) : null}

                {fileError ? (
                  <Alert
                    type="warning"
                    showIcon
                    title={fileError}
                    style={{ marginTop: 12 }}
                  />
                ) : null}
                {uploadMutation.isError ? (
                  <Alert
                    type="error"
                    showIcon
                    title={uploadMutation.error.message}
                    style={{ marginTop: 12 }}
                  />
                ) : null}

                <Button
                  type="primary"
                  htmlType="submit"
                  icon={<CloudUploadOutlined />}
                  loading={uploadMutation.isPending}
                  disabled={phase !== 'idle'}
                  className="mt-16"
                >
                  Bắt đầu nạp tài liệu
                </Button>
              </Form>
            </Panel>
          )}

          <Panel title="Lưu ý trước khi nạp">
            <ul className="plain-list">
              <li>Tài liệu nên có cấu trúc chương/mục rõ ràng để trích dẫn chính xác.</li>
              <li>Không tải lên tài liệu chứa dữ liệu cá nhân chưa được phép xử lý.</li>
              <li>Mỗi mã tài liệu chỉ dùng cho một tài liệu; phiên bản mới dùng chức năng “Tải phiên bản mới”.</li>
              <li>Quá trình nạp có thể mất vài phút tùy số trang và tải của dịch vụ AI.</li>
            </ul>
          </Panel>
        </div>

        <Panel title="Quy trình nạp" className="stepper-card">
          <Steps
            direction="vertical"
            size="small"
            current={activeStep}
            status={failed ? 'error' : succeeded ? 'finish' : 'process'}
            items={PIPELINE_STEPS}
          />
          <div className="step-note">
            <strong>Kiểm soát phiên bản:</strong> bản mới chỉ thay thế bản hiện hành
            sau khi toàn bộ pipeline thành công.
          </div>
          {succeeded ? (
            <Tag color="success" icon={<FileTextOutlined />} style={{ marginTop: 12 }}>
              Sẵn sàng tìm kiếm
            </Tag>
          ) : null}
        </Panel>
      </div>
    </div>
  )
}
