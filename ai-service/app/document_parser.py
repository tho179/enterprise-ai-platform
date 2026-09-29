import io
import logging
from pathlib import Path
import pymupdf

try:
    # pyrefly: ignore [missing-import]
    import pytesseract
    # pyrefly: ignore [missing-import]
    from PIL import Image
    HAS_OCR = True
except ImportError:
    pytesseract = None
    Image = None
    HAS_OCR = False

try:
    from app.font_converter import normalize_vietnamese_text
except ImportError:
    from font_converter import normalize_vietnamese_text

logger = logging.getLogger(__name__)


def ocr_page(page, dpi: int = 300, lang: str = "vie") -> dict:
    """
    Thực hiện OCR trên đối tượng Trang của PyMuPDF không cần dùng thư viện pdf2image.
    Kết xuất trang thành ảnh PNG trong bộ nhớ, sau đó chạy Tesseract OCR.
    Trả về dictionary gồm 'text' (đoạn văn bản tổng) và 'words' (danh sách từng từ kèm tọa độ).
    """
    if not HAS_OCR or pytesseract is None or Image is None:
        logger.warning("pytesseract hoặc Pillow chưa được cài đặt. Bỏ qua OCR fallback.")
        return {"text": "", "words": []}

    try:
        pix = page.get_pixmap(dpi=dpi)
        img = Image.open(io.BytesIO(pix.tobytes("png")))
        
        # Lấy dữ liệu chi tiết kèm bounding box
        data = pytesseract.image_to_data(img, lang=lang, output_type=pytesseract.Output.DICT)
        
        words_data = []
        lines_map = {}
        
        for i in range(len(data['text'])):
            conf = int(data['conf'][i])
            word_text = data['text'][i].strip()
            
            if conf > -1 and word_text:
                # Ghi nhận thông tin từ và bounding box
                words_data.append({
                    "text": word_text,
                    "x": data['left'][i],
                    "y": data['top'][i],
                    "width": data['width'][i],
                    "height": data['height'][i],
                    "confidence": conf
                })
                
                # Gom nhóm theo block, paragraph, line để nối thành văn bản hoàn chỉnh
                key = (data['block_num'][i], data['par_num'][i], data['line_num'][i])
                if key not in lines_map:
                    lines_map[key] = []
                lines_map[key].append(word_text)
                
        # Tái tạo văn bản: nối từ cùng dòng bằng khoảng trắng, nối các dòng bằng ký tự xuống dòng
        full_text = "\n".join([" ".join(words) for words in lines_map.values()])
        
        return {
            "text": full_text.strip(),
            "words": words_data
        }
    except Exception as e:
        logger.warning(f"Lỗi OCR cho trang {page.number + 1}: {e}")
        return {"text": "", "words": []}


def extract_text_from_pdf(file_path: str, min_text_len: int = 30) -> list[dict]:
    """
    Trình phân tích PDF hỗn hợp (Hybrid PDF Parser):
    1. Cố gắng trích xuất lớp văn bản (Text Layer) thông qua PyMuPDF.
    2. Nếu không có lớp văn bản hoặc quá ngắn (PDF dạng Scan), chuyển sang dùng Tesseract OCR.
    3. Chuẩn hóa các bảng mã phông chữ cũ (TCVN3 / VNI) chỉ dành riêng cho phần trích xuất từ lớp văn bản.

    Trả về:
        [{"page": 1, "text": "..."}, ...]
    """
    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"File không tồn tại: {file_path}")

    pages = []

    with pymupdf.open(file_path) as document:
        for page_number, page in enumerate(document, start=1):
            raw_text = page.get_text("text").strip()

            words_data = []

            # 1. Nhánh xử lý lớp văn bản (Text Layer)
            if len(raw_text) >= min_text_len:
                text = normalize_vietnamese_text(raw_text)
                source = "native"
                
                # Trích xuất bounding boxes từ PyMuPDF nếu muốn đồng bộ kiến trúc (Optional)
                for block in page.get_text("dict").get("blocks", []):
                    if "lines" in block:
                        for line in block["lines"]:
                            for span in line["spans"]:
                                span_text = span["text"].strip()
                                if span_text:
                                    bbox = span["bbox"]
                                    words_data.append({
                                        "text": normalize_vietnamese_text(span_text),
                                        "x": bbox[0],
                                        "y": bbox[1],
                                        "width": bbox[2] - bbox[0],
                                        "height": bbox[3] - bbox[1],
                                        "confidence": 100
                                    })

            # 2. Nhánh dự phòng OCR (PDF Scan)
            else:
                ocr_result = ocr_page(page)
                text = ocr_result["text"]
                words_data = ocr_result["words"]
                source = "ocr"

            if not text:
                continue

            pages.append({
                "page": page_number,
                "text": text,
                "source": source,
                "words": words_data
            })

    return pages


def extract_text_from_txt(file_path: str) -> list[dict]:
    """
    Đọc file TXT, coi toàn bộ nội dung là trang 1.
    Tự động chuẩn hóa các bảng mã phông chữ cũ.

    Trả về:
        [{"page": 1, "text": "..."}]
    """
    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"File không tồn tại: {file_path}")

    try:
        raw_text = path.read_text(encoding="utf-8").strip()
    except UnicodeDecodeError:
        raw_text = path.read_text(encoding="latin1", errors="ignore").strip()

    if not raw_text:
        return []

    normalized_text = normalize_vietnamese_text(raw_text)

    return [{
        "page": 1,
        "text": normalized_text,
        "source": "native",
        "words": []
    }]


def extract_text(file_path: str) -> list[dict]:
    """
    Tự động nhận diện định dạng file và gọi trình phân tích tương ứng.

    Hỗ trợ các định dạng: .pdf, .txt
    """
    extension = Path(file_path).suffix.lower()

    if extension == ".pdf":
        return extract_text_from_pdf(file_path)

    if extension == ".txt":
        return extract_text_from_txt(file_path)

    raise ValueError(f"Định dạng chưa được hỗ trợ: {extension}")

