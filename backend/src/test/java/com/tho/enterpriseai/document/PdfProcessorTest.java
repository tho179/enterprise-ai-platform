package com.tho.enterpriseai.document;

import org.junit.jupiter.api.Test;

import java.util.List;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

class PdfProcessorTest {

    private final PdfProcessor processor = new PdfProcessor();

    @Test
    void chunksOcrPagesAndKeepsTheirPageNumbers() {
        String text = ("Điều 1. Quyền của cổ đông. " + "Nội dung điều lệ. ".repeat(120)).repeat(2);

        PdfProcessor.PdfContent content = processor.fromPages(
                3,
                List.of(
                        new PdfProcessor.PageText(1, " "),
                        new PdfProcessor.PageText(2, text),
                        new PdfProcessor.PageText(3, "Trang cuối.")
                )
        );

        assertEquals(3, content.pageCount());
        assertFalse(content.chunks().isEmpty());
        assertTrue(content.chunks().stream().allMatch(chunk -> chunk.page() == 2));
        assertEquals(0, content.chunks().get(0).index());
    }

    @Test
    void skipsTableOfContentsPages() {
        String toc = "MỤC LỤC\n"
                + "CHƯƠNG I. ĐỊNH NGHĨA CÁC THUẬT NGỮ ........................ 4\n"
                + "Điều 1. Định nghĩa ........................ 4\n"
                + "Điều 2. Phạm vi điều chỉnh ........................ 5";
        String body = "Điều 1. Quyền của cổ đông. " + "Nội dung điều lệ. ".repeat(80);

        PdfProcessor.PdfContent content = processor.fromPages(
                2,
                List.of(
                        new PdfProcessor.PageText(1, toc),
                        new PdfProcessor.PageText(2, body)
                )
        );

        assertFalse(content.chunks().isEmpty());
        assertTrue(content.chunks().stream().allMatch(chunk -> chunk.page() == 2));
    }

    @Test
    void rejectsPagesWithoutUsableText() {
        IllegalStateException error = assertThrows(
                IllegalStateException.class,
                () -> processor.fromPages(1, List.of(new PdfProcessor.PageText(1, "   ")))
        );

        assertTrue(error.getMessage().contains("OCR"));
    }

    @Test
    void locatesChunkOnWordBoxesForHighlight() {
        String filler = "nội dung điều lện chi tiết. ";
        String page = "Cổ đông có quyền tranh chấp. " + filler.repeat(30);
        List<PdfProcessor.Rect> words = new java.util.ArrayList<>();
        int index = 0;
        for (String token : page.split(" ")) {
            if (token.isBlank()) {
                continue;
            }
            words.add(new PdfProcessor.Rect(
                    0.05 + (index % 10) * 0.05,
                    0.20 + (index / 10) * 0.02,
                    0.04,
                    0.015,
                    token));
            index++;
        }

        PdfProcessor.PdfContent content = processor.fromPages(
                1,
                List.of(new PdfProcessor.PageText(1, page, words))
        );

        assertTrue(content.chunks().size() >= 1);
        List<PdfProcessor.Rect> rects = content.chunks().get(0).highlight();
        assertFalse(rects.isEmpty());
        assertEquals(0.05, rects.get(0).x(), 1e-6);
        assertEquals(0.20, rects.get(0).y(), 1e-6);
    }

    @Test
    void keepsEmptyHighlightWhenWordsDoNotAlignWithText() {
        String page = "Đoạn văn bản hoàn thành " + "nội dung bổ sung chi tiết. ".repeat(40);
        List<PdfProcessor.Rect> words = List.of(
                new PdfProcessor.Rect(0.1, 0.2, 0.1, 0.02, "không"),
                new PdfProcessor.Rect(0.2, 0.2, 0.1, 0.02, "liên"),
                new PdfProcessor.Rect(0.3, 0.2, 0.1, 0.02, "quan")
        );

        PdfProcessor.PdfContent content = processor.fromPages(
                1,
                List.of(new PdfProcessor.PageText(1, page, words))
        );

        assertFalse(content.chunks().isEmpty());
        assertTrue(content.chunks().get(0).highlight().isEmpty());
    }
}
