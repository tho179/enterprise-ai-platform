import { describe, expect, it } from 'vitest'
import { citationAnchor, extractCitationIndices, linkCitationMarkers } from '@/lib/citations'

describe('citation markers', () => {
  it('turns numeric markers into internal links', () => {
    expect(linkCitationMarkers('Theo quy định [1] và [2].')).toBe(
      'Theo quy định [1](#citation-1) và [2](#citation-2).',
    )
  })

  it('leaves real markdown links and non-numeric brackets alone', () => {
    const markdown = 'Xem [tài liệu](https://example.com) và [ghi chú].'
    expect(linkCitationMarkers(markdown)).toBe(markdown)
  })

  it('extracts unique, sorted citation indices', () => {
    expect(extractCitationIndices('A [3] B [1] C [3] D [2]')).toEqual([1, 2, 3])
    expect(extractCitationIndices('Không có trích dẫn')).toEqual([])
  })

  it('builds an anchor for a citation', () => {
    expect(citationAnchor(4)).toBe('#citation-4')
  })
})
