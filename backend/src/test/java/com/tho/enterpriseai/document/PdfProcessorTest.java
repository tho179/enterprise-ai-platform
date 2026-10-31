package com.tho.enterpriseai.document;

import org.apache.pdfbox.Loader;
import org.apache.pdfbox.pdmodel.PDDocument;
import org.apache.pdfbox.pdmodel.PDPage;
import org.apache.pdfbox.rendering.PDFRenderer;
import org.junit.jupiter.api.Test;

import java.awt.image.BufferedImage;
import java.nio.file.Files;
import java.nio.file.Path;
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

    @Test
    void overlapStartsAtWordBoundary() {
        StringBuilder text = new StringBuilder();
        for (int i = 0; i < 120; i++) {
            text.append("Câu ").append(i)
                    .append(" nói về việc mua hoặc bán tài sản của Công ty. ");
        }
        List<String> parts = processor.splitText(text.toString());

        assertTrue(parts.size() > 1);
        int searchFrom = 0;
        for (String part : parts) {
            int index = text.indexOf(part, searchFrom);
            assertTrue(index >= 0, "Không tìm thấy chunk trong văn bản gốc");
            assertTrue(
                    part.startsWith("Câu "),
                    "Chunk không bắt đầu ở đầu câu: " + part.substring(0, Math.min(30, part.length()))
            );
            if (index > 0) {
                assertTrue(
                        Character.isWhitespace(text.charAt(index - 1)),
                        "Chunk bắt đầu giữa từ: " + part.substring(0, Math.min(20, part.length()))
                );
            }
            searchFrom = index + 1;
        }
    }

    @Test
    void writesYellowHighlightIntoRealPdf() throws Exception {
        Path file = Files.createTempFile("pdf-highlight", ".pdf");
        try {
            try (PDDocument document = new PDDocument()) {
                document.addPage(new PDPage());
                document.save(file.toFile());
            }

            byte[] highlighted = processor.renderPdfWithHighlight(
                    file, 1, List.of(new PdfProcessor.Rect(0.1, 0.1, 0.8, 0.2, ""))
            );

            try (PDDocument document = Loader.loadPDF(highlighted)) {
                assertEquals(1, document.getNumberOfPages());
                BufferedImage image = new PDFRenderer(document).renderImage(0, 1f);
                int yellow = 0;
                for (int y = 0; y < image.getHeight(); y++) {
                    for (int x = 0; x < image.getWidth(); x++) {
                        int rgb = image.getRGB(x, y);
                        int red = (rgb >> 16) & 0xff;
                        int green = (rgb >> 8) & 0xff;
                        int blue = rgb & 0xff;
                        if (red > 200 && green > 180 && blue < 140) {
                            yellow++;
                        }
                    }
                }
                assertTrue(yellow > 1000, "Không thấy vùng vàng trong PDF xuất ra");
            }
        } finally {
            Files.deleteIfExists(file);
        }
    }
}
