const CITATION_MARKER = /\[(\d+)\](?!\()/g

/**
 * Turns citation markers like [1] into internal markdown links so ReactMarkdown
 * can render them as buttons without touching normal markdown links.
 */
export function linkCitationMarkers(markdown: string): string {
  return markdown.replace(CITATION_MARKER, '[$1](#citation-$1)')
}

export function extractCitationIndices(markdown: string): number[] {
  const found = new Set<number>()
  for (const match of markdown.matchAll(CITATION_MARKER)) {
    const value = Number(match[1])
    if (Number.isFinite(value)) found.add(value)
  }
  return [...found].sort((a, b) => a - b)
}

export function citationAnchor(index: number): string {
  return `#citation-${index}`
}
