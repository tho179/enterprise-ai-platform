export function formatNumber(value: number | undefined | null): string {
  if (value === undefined || value === null || Number.isNaN(value)) return '—'
  return new Intl.NumberFormat('vi-VN').format(value)
}

export function formatPercent(value: number): string {
  return `${Math.round(value * 100)}%`
}

/**
 * Retrieval score of a citation. Cosine similarity (0..1) reads as a percent;
 * the fused score (cosine + keyword + article boost) can exceed 1, so it is
 * shown as a plain number instead of an impossible "149%".
 */
export function formatRelevance(value: number | undefined | null): string {
  if (value === undefined || value === null || Number.isNaN(value)) return '—'
  if (value >= 0 && value <= 1) return formatPercent(value)
  return value.toFixed(2)
}

export function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

export function initials(name: string): string {
  const parts = name.trim().split(/\s+/).filter(Boolean)
  if (parts.length === 0) return '?'
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase()
  return `${parts[0][0]}${parts[parts.length - 1][0]}`.toUpperCase()
}

export function truncate(value: string, max: number): string {
  if (value.length <= max) return value
  return `${value.slice(0, max).trimEnd()}…`
}
