import type { AgentTraceStep } from '@/api/types'

const ACTION_LABELS: Record<string, string> = {
  kb_attribute: 'Tra giá trị trong cơ sở tri thức',
  'retrieve:flat_rag': 'Tìm theo vector',
  'retrieve:hybrid_rag': 'Tìm kết hợp vector và đồ thị',
  respond: 'Trả lời',
  refuse: 'Từ chối',
}

const RESULT_LABELS: Record<string, string> = {
  found: 'có giá trị',
  not_found: 'không có giá trị',
  answered: 'đủ căn cứ',
  gate_refused: 'chưa đủ căn cứ',
}

const SHAPE_LABELS: Record<string, string> = {
  count: 'hỏi số lượng',
  time: 'hỏi thời gian',
  yes_no: 'hỏi có/không',
  list: 'hỏi liệt kê',
  article: 'hỏi theo điều khoản',
  open: 'câu hỏi mở',
}

/** Collapsible list of the agent's decisions under an answer. */
export function AgentTrace({ trace }: { trace?: AgentTraceStep[] }) {
  if (!trace || trace.length < 2) return null
  const perception = trace[0]?.perception
  const steps = trace.slice(1)
  return (
    <details className="agent-trace">
      <summary>Cách hệ thống xử lý ({steps.length} bước)</summary>
      {perception ? (
        <p className="agent-trace__perception">
          Nhận diện: {SHAPE_LABELS[perception.shape ?? ''] ?? perception.shape}
          {perception.attribute ? ` · thuộc tính "${perception.attribute}"` : ''}
          {perception.article ? ` · Điều ${perception.article}` : ''}
          {perception.entities?.length ? ` · thực thể: ${perception.entities.join(', ')}` : ''}
        </p>
      ) : null}
      <ol className="agent-trace__steps">
        {steps.map((step) => (
          <li key={step.step}>
            <span className="mono">{step.rule}</span>
            {' → '}
            {ACTION_LABELS[step.action ?? ''] ?? step.action}
            {step.result ? ` (${RESULT_LABELS[step.result] ?? step.result})` : ''}
            {step.ms !== undefined ? <span className="muted"> · {Math.round(step.ms)} ms</span> : null}
          </li>
        ))}
      </ol>
    </details>
  )
}
