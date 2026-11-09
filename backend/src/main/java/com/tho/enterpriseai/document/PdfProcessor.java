package com.tho.enterpriseai.document;

import org.apache.pdfbox.Loader;
import org.apache.pdfbox.pdmodel.PDDestinationNameTreeNode;
import org.apache.pdfbox.pdmodel.PDDocument;
import org.apache.pdfbox.pdmodel.PDDocumentCatalog;
import org.apache.pdfbox.pdmodel.PDDocumentNameDictionary;
import org.apache.pdfbox.pdmodel.PDPage;
import org.apache.pdfbox.pdmodel.PDPageContentStream;
import org.apache.pdfbox.pdmodel.common.PDRectangle;
import org.apache.pdfbox.pdmodel.graphics.blend.BlendMode;
import org.apache.pdfbox.pdmodel.graphics.state.PDExtendedGraphicsState;
import org.apache.pdfbox.pdmodel.interactive.documentnavigation.destination.PDPageDestination;
import org.apache.pdfbox.pdmodel.interactive.documentnavigation.destination.PDPageFitRectangleDestination;
import org.apache.pdfbox.text.PDFTextStripper;
import org.springframework.stereotype.Component;

import java.io.IOException;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.regex.Pattern;

@Component
public class PdfProcessor {

    private static final int MAX_CHARS = 1400;
    private static final int OVERLAP_CHARS = 160;
    private static final int MAX_OVERLAP_CHARS = 400;
    private static final String EVIDENCE_DESTINATION = "evidence";
    private static final int MIN_CHARS = 40;
    // Dòng mục lục có dấu chấm/gạch dẫn trang (vd "Điều 1. Định nghĩa...... 4").
    private static final Pattern TOC_LEADER = Pattern.compile("(?:\\.{4,}|…{2,}|_{4,})");

    public PdfContent extract(Path file) {
        try (PDDocument pdf = Loader.loadPDF(file.toFile())) {
            int pageCount = pdf.getNumberOfPages();
            List<PageText> pages = new ArrayList<>();
            for (int pageNumber = 1; pageNumber <= pageCount; pageNumber++) {
                PDFTextStripper stripper = new PDFTextStripper();
                stripper.setSortByPosition(true);
                stripper.setStartPage(pageNumber);
                stripper.setEndPage(pageNumber);
                String text = clean(stripper.getText(pdf));
                if (!text.isBlank()) {
                    pages.add(new PageText(pageNumber, text, List.of()));
                }
            }
            return chunkPages(
                    pageCount,
                    pages,
                    "PDF không có lớp văn bản để trích xuất. Tệp scan cần OCR trước khi nạp."
            );
        } catch (IOException exception) {
            throw new IllegalStateException("Không đọc được tệp PDF: " + exception.getMessage(), exception);
        }
    }

    public PdfContent fromPages(int pageCount, List<PageText> pages) {
        return chunkPages(
                pageCount,
                pages,
                "Không trích xuất được văn bản từ PDF, kể cả OCR."
        );
    }

    /** Locate an AI-service chunk inside the word boxes of its first page. */
    public List<Rect> locateInPage(PageText page, String content) {
        return locate(page.words(), content);
    }

    private PdfContent chunkPages(int pageCount, List<PageText> pages, String emptyMessage) {
        List<ExtractedChunk> chunks = new ArrayList<>();
        int chunkIndex = 0;

        for (PageText page : pages) {
            String text = clean(page.text());
            if (text.isBlank() || isTableOfContents(text)) {
                continue;
            }
            List<Rect> pageWords = page.words();
            for (String part : splitText(text)) {
                if (part.length() < MIN_CHARS) {
                    continue;
                }
                if (!chunks.isEmpty() && chunks.get(chunks.size() - 1).content().equals(part)) {
                    continue;
                }
                chunks.add(new ExtractedChunk(
                        chunkIndex++,
                        page.page(),
                        part,
                        locate(pageWords, part)
                ));
            }
        }

        if (chunks.isEmpty()) {
            throw new IllegalStateException(emptyMessage);
        }
        return new PdfContent(pageCount, chunks);
    }

    /**
     * Định vị đoạn văn bản trong dòng từ của trang, trả về 1 khung mỗi dòng
     * (tọa độ tỷ lệ 0..1) để frontend/giám định tô vàng số đường dẫn chứng.
     * Trả về rỗng nếu không khớp đủ (tài liệu nạp từ PDFBox fallback không có words).
     */
    private List<Rect> locate(List<Rect> pageWords, String chunkContent) {
        if (pageWords == null || pageWords.isEmpty() || chunkContent.isBlank()) {
            return List.of();
        }
        Map<String, String> foldCache = new HashMap<>();
        List<String> pageTokens = new ArrayList<>(pageWords.size());
        for (Rect word : pageWords) {
            pageTokens.add(fold(foldCache, word.text()));
        }
        String[] chunkTokens = fold(foldCache, chunkContent).split(" ");
        List<String> validChunkTokens = new ArrayList<>(chunkTokens.length);
        for (String token : chunkTokens) {
            if (!token.isBlank()) {
                validChunkTokens.add(token);
            }
        }
        if (validChunkTokens.isEmpty() || validChunkTokens.size() > pageTokens.size()) {
            return List.of();
        }
        String[] targets = validChunkTokens.toArray(new String[0]);

        int bestStart = -1;
        int bestHits = 0;
        int limit = pageTokens.size() - targets.length;
        for (int start = 0; start <= limit; start++) {
            int hits = 0;
            for (int offset = 0; offset < targets.length; offset++) {
                if (pageTokens.get(start + offset).equals(targets[offset])) {
                    hits++;
                }
            }
            if (hits > bestHits) {
                bestHits = hits;
                bestStart = start;
                if (hits == targets.length) {
                    break;
                }
            }
        }
        // Cần khớp phần lớn nội dung mới tin được là đoạn này.
        if (bestStart < 0 || bestHits * 2 < targets.length) {
            return List.of();
        }

        return groupLines(pageWords.subList(bestStart, bestStart + targets.length));
    }

    private static String fold(Map<String, String> cache, String value) {
        return cache.computeIfAbsent(value, PdfProcessor::foldToken);
    }

    /**
     * Bỏ dấu tiếng Việt (ổ -> o, đ -> d), lowercase và nén khoảng trắng để text
     * của chunk khớp được với chuỗi từ khi OCR/extract đã làm lệch dấu.
     */
    private static String foldToken(String token) {
        String decomposed = java.text.Normalizer.normalize(token, java.text.Normalizer.Form.NFD);
        StringBuilder out = new StringBuilder(decomposed.length());
        for (int i = 0; i < decomposed.length(); ) {
            int codePoint = decomposed.codePointAt(i);
            int type = Character.getType(codePoint);
            boolean isCombining = type == Character.NON_SPACING_MARK || type == Character.COMBINING_SPACING_MARK;
            boolean isWhitespace = Character.isSpaceChar(codePoint) || Character.isWhitespace(codePoint);
            if (!isCombining) {
                out.append(isWhitespace ? ' ' : foldCodePoint(codePoint));
            }
            i += Character.charCount(codePoint);
        }
        return out.toString();
    }

    private static char foldCodePoint(int codePoint) {
        if (codePoint == 0x0110 || codePoint == 0x0111) {
            return 'd';
        }
        return (char) Character.toLowerCase(codePoint);
    }

    /** Gom các từ rời rạc theo dòng (y gần nhau) thành khung 1 dòng. */
    private static List<Rect> groupLines(List<Rect> words) {
        List<Rect> lines = new ArrayList<>();
        for (Rect word : words) {
            if (!lines.isEmpty()) {
                Rect current = lines.get(lines.size() - 1);
                double sameLineTolerance = 0.5 * (current.h() + word.h());
                if (Math.abs(current.y() - word.y()) <= sameLineTolerance) {
                    lines.set(lines.size() - 1, current.merge(word));
                    continue;
                }
            }
            lines.add(word);
        }
        return lines;
    }

    /** Trang mục lục: từ 3 dòng có dấu dẫn trang trở lên — bỏ khỏi kho tri thức. */
    private boolean isTableOfContents(String text) {
        int leaderLines = 0;
        for (String line : text.split("\n")) {
            if (TOC_LEADER.matcher(line).find()) {
                leaderLines++;
            }
        }
        return leaderLines >= 3;
    }

    private String clean(String raw) {
        return raw
                .replace("\u0000", " ")
                .replaceAll("[\\t\\x0B\\f\\r]+", " ")
                .replaceAll(" {2,}", " ")
                .replaceAll("\\n{3,}", "\n\n")
                .trim();
    }

    List<String> splitText(String text) {
        List<String> parts = new ArrayList<>();
        int start = 0;
        while (start < text.length()) {
            int end = Math.min(start + MAX_CHARS, text.length());
            if (end < text.length()) {
                int boundary = findBoundary(text, start, end);
                if (boundary > start + MAX_CHARS / 2) {
                    end = boundary;
                }
            }
            String part = text.substring(start, end).trim();
            if (!part.isBlank()) {
                parts.add(part);
            }
            if (end >= text.length()) {
                break;
            }
            start = Math.max(start + 1, nextChunkStart(text, end));
        }
        return parts;
    }

    /**
     * Điểm bắt đầu chunk kế tiếp: lùi về đầu câu gần nhất (tối đa
     * MAX_OVERLAP_CHARS) để câu trả lời không mở đầu giữa câu/mid-word.
     */
    private int nextChunkStart(String text, int end) {
        int floor = Math.max(0, end - MAX_OVERLAP_CHARS);
        for (int i = end - 1; i >= floor; i--) {
            char current = text.charAt(i);
            boolean sentenceEnd = current == '.' || current == '!' || current == '?'
                    || current == ';';
            if (sentenceEnd && (i + 1 >= text.length() || Character.isWhitespace(text.charAt(i + 1)))) {
                int next = i + 1;
                while (next < end && Character.isWhitespace(text.charAt(next))) {
                    next++;
                }
                return next;
            }
        }
        int newline = text.lastIndexOf('\n', end - 1);
        if (newline >= floor) {
            int next = newline + 1;
            while (next < end && Character.isWhitespace(text.charAt(next))) {
                next++;
            }
            return next;
        }
        int candidate = Math.max(0, end - OVERLAP_CHARS);
        while (candidate < end && candidate > 0 && !Character.isWhitespace(text.charAt(candidate - 1))) {
            candidate++;
        }
        while (candidate < end && Character.isWhitespace(text.charAt(candidate))) {
            candidate++;
        }
        return candidate;
    }

    private int findBoundary(String text, int start, int end) {
        int lowerBound = start + MAX_CHARS / 2;
        int[] candidates = {
                text.lastIndexOf("\n\n", end),
                text.lastIndexOf(". ", end),
                text.lastIndexOf("; ", end),
                text.lastIndexOf("\n", end),
                text.lastIndexOf(' ', end)
        };
        for (int candidate : candidates) {
            if (candidate > lowerBound) {
                return candidate + 1;
            }
        }
        return end;
    }

    /** Khung chữ theo tỷ lệ 0..1 so với trang (x, y góc trên trái). */
    public record Rect(double x, double y, double w, double h, String text) {

        public Rect merge(Rect other) {
            double newX = Math.min(x, other.x);
            double newY = Math.min(y, other.y);
            double right = Math.max(x + w, other.x + other.w);
            double bottom = Math.max(y + h, other.y + other.h);
            return new Rect(newX, newY, right - newX, bottom - newY, text);
        }
    }

    public record PageText(int page, String text, List<Rect> words) {

        public PageText(int page, String text) {
            this(page, text, List.of());
        }
    }

    public record ExtractedChunk(int index, int page, String content, List<Rect> highlight) {
    }

    public record PdfContent(int pageCount, List<ExtractedChunk> chunks) {
    }

    /**
     * Render một trang PDF thành PNG và phủ khung vàng bán trong suốt lên vùng
     * dẫn chứng (tọa độ tỷ lệ 0..1 so với trang) phục vụ xem trích dẫn.
     */
    public byte[] renderPageWithHighlight(Path file, int pageNumber, List<Rect> rects, float scale) {
        try (PDDocument pdf = Loader.loadPDF(file.toFile())) {
            if (pageNumber < 1 || pageNumber > pdf.getNumberOfPages()) {
                throw new IllegalStateException("Trang " + pageNumber + " ngoài phạm vi tài liệu.");
            }
            org.apache.pdfbox.rendering.PDFRenderer renderer = new org.apache.pdfbox.rendering.PDFRenderer(pdf);
            java.awt.image.BufferedImage image = renderer.renderImage(pageNumber - 1, scale);
            java.awt.Graphics2D graphics = image.createGraphics();
            int width = image.getWidth();
            int height = image.getHeight();
            graphics.setColor(new java.awt.Color(255, 234, 0, 110));
            for (Rect rect : rects) {
                graphics.fillRect(
                        (int) Math.max(0, rect.x() * width),
                        (int) Math.max(0, rect.y() * height),
                        (int) Math.min(width - rect.x() * width, rect.w() * width + 1),
                        (int) Math.min(height - rect.y() * height, rect.h() * height + 1)
                );
            }
            graphics.dispose();
            try (java.io.ByteArrayOutputStream out = new java.io.ByteArrayOutputStream()) {
                javax.imageio.ImageIO.write(image, "png", out);
                return out.toByteArray();
            }
        } catch (IOException exception) {
            throw new IllegalStateException("Không render được trang PDF: " + exception.getMessage(), exception);
        }
    }

    /**
     * Trả về PDF gốc đã vẽ đè khung vàng lên trang chứa dẫn chứng (tọa độ tỷ lệ
     * 0..1, gốc trên trái) để trình xem PDF thật hiển thị đúng vùng bôi vàng.
     */
    public byte[] renderPdfWithHighlight(Path file, int pageNumber, List<Rect> rects) {
        try (PDDocument pdf = Loader.loadPDF(file.toFile())) {
            if (pageNumber < 1 || pageNumber > pdf.getNumberOfPages()) {
                throw new IllegalStateException("Trang " + pageNumber + " ngoài phạm vi tài liệu.");
            }
            PDPage page = pdf.getPage(pageNumber - 1);
            PDRectangle box = page.getCropBox();
            float pageWidth = box.getWidth();
            float pageHeight = box.getHeight();
            float minX = box.getLowerLeftX();
            float maxX = box.getUpperRightX();
            float maxY = box.getUpperRightY();
            float minY = maxY - 24;
            if (!rects.isEmpty()) {
                minX = Float.MAX_VALUE;
                minY = Float.MAX_VALUE;
                maxX = -Float.MAX_VALUE;
                maxY = -Float.MAX_VALUE;
                try (PDPageContentStream content = new PDPageContentStream(
                        pdf, page, PDPageContentStream.AppendMode.APPEND, true)) {
                    content.setNonStrokingColor(new java.awt.Color(255, 234, 0));
                    // Nhân bản màu để chữ/ảnh scan bên dưới vẫn đọc được.
                    PDExtendedGraphicsState blend = new PDExtendedGraphicsState();
                    blend.setBlendMode(BlendMode.MULTIPLY);
                    content.setGraphicsStateParameters(blend);
                    for (Rect rect : rects) {
                        float width = (float) (rect.w() * pageWidth);
                        float height = (float) (rect.h() * pageHeight);
                        float x = box.getLowerLeftX() + (float) (rect.x() * pageWidth);
                        float y = box.getLowerLeftY() + (float) ((1 - rect.y() - rect.h()) * pageHeight);
                        content.addRect(x, y, width, height);
                        content.fill();
                        minX = Math.min(minX, x);
                        minY = Math.min(minY, y);
                        maxX = Math.max(maxX, x + width);
                        maxY = Math.max(maxY, y + height);
                    }
                }
            }
            addEvidenceDestination(pdf, page, minX, minY, maxX, maxY);
            try (java.io.ByteArrayOutputStream out = new java.io.ByteArrayOutputStream()) {
                pdf.save(out);
                return out.toByteArray();
            }
        } catch (IOException exception) {
            throw new IllegalStateException("Không tạo được PDF bôi vàng: " + exception.getMessage(), exception);
        }
    }

    /**
     * Điểm đến có tên để trình xem PDF nhảy thẳng tới vùng vàng thay vì mở ở
     * đầu trang; fragment #nameddest=evidence dùng được cả với blob URL.
     */
    private void addEvidenceDestination(
            PDDocument pdf, PDPage page, float left, float bottom, float right, float top
    ) throws IOException {
        float margin = 12f;
        PDDocumentCatalog catalog = pdf.getDocumentCatalog();
        PDDocumentNameDictionary names = catalog.getNames();
        if (names == null) {
            names = new PDDocumentNameDictionary(catalog);
            catalog.setNames(names);
        }
        PDDestinationNameTreeNode destinations = names.getDests();
        Map<String, PDPageDestination> entries =
                destinations == null ? new HashMap<>() : destinations.getNames();
        entries = entries == null ? new HashMap<>() : new HashMap<>(entries);

        PDRectangle box = page.getCropBox();
        PDPageFitRectangleDestination destination = new PDPageFitRectangleDestination();
        destination.setPage(page);
        destination.setLeft((int) Math.max(box.getLowerLeftX(), Math.floor(left - margin)));
        destination.setBottom((int) Math.max(box.getLowerLeftY(), Math.floor(bottom - margin)));
        destination.setRight((int) Math.min(box.getUpperRightX(), Math.ceil(right + margin)));
        destination.setTop((int) Math.min(box.getUpperRightY(), Math.ceil(top + margin)));
        entries.put(EVIDENCE_DESTINATION, destination);

        if (destinations == null) {
            destinations = new PDDestinationNameTreeNode();
            names.setDests(destinations);
        }
        destinations.setNames(entries);
    }
}
