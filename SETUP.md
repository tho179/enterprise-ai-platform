# Hướng dẫn Thiết lập Môi trường (Environment Setup)

Để chạy dự án **Enterprise AI Platform** và đặc biệt là chạy thành công các Unit Test liên quan đến phân tích tài liệu (PDF Parser, OCR), bạn cần cài đặt đầy đủ các thư viện phụ thuộc của hệ điều hành.

## 1. Yêu cầu hệ thống (System Dependencies)

Hệ thống trích xuất PDF và OCR (Optical Character Recognition) yêu cầu các phần mềm lõi sau đây phải được cài đặt trên máy tính của bạn:

### 🔹 Tesseract OCR (Bắt buộc cho PDF Scan)
Tesseract là engine lõi để đọc chữ từ hình ảnh (PDF Scan).
- **Windows:** Tải file cài đặt từ [UB-Mannheim Tesseract](https://github.com/UB-Mannheim/tesseract/wiki) và cài đặt (thường vào `C:\Program Files\Tesseract-OCR`).
  - **Bước 1: Thêm Tesseract vào PATH**
    1. Nhấn phím `Windows`, gõ `Environment Variables`.
    2. Chọn **Edit the system environment variables** ➡️ **Environment Variables...**.
    3. Ở phần **System variables**, tìm biến `Path` ➡️ chọn **Edit**.
    4. Nhấn **New**, thêm đường dẫn: `C:\Program Files\Tesseract-OCR`.
    5. Nhấn **OK** liên tục để lưu.
    6. **Quan trọng:** Đóng toàn bộ cửa sổ CMD/PowerShell hiện tại và mở cửa sổ mới để hệ thống nhận biến môi trường.
  - **Bước 2: Kiểm tra cài đặt thành công**
    - Mở Terminal mới, gõ: `tesseract --version`. (Nếu ra thông số phiên bản là đã nhận lệnh).
    - Sau đó gõ: `tesseract --list-langs`.
  - **Bước 3: Vấn đề Tiếng Việt (vie.traineddata)**
    - Nếu lệnh `tesseract --list-langs` chỉ trả về `eng`, `osd`... mà **không có `vie`**, nghĩa là máy bạn chưa có gói Tiếng Việt.
    - **Cách xử lý:** Hãy tải file [vie.traineddata](https://github.com/tesseract-ocr/tessdata/blob/main/vie.traineddata) từ repository chính thức của GitHub. Sau đó, copy và đặt file này vào thư mục: `C:\Program Files\Tesseract-OCR\tessdata`. Khởi động lại terminal và check lại.
- **macOS:** Mở Terminal và gõ: `brew install tesseract tesseract-lang`
- **Linux (Ubuntu):** Mở Terminal và gõ: `sudo apt-get install tesseract-ocr tesseract-ocr-vie`

### 🔹 Poppler (Bắt buộc để đọc file PDF)
Nhiều thư viện Python (như `pdf2image`) yêu cầu Poppler để chuyển đổi trang PDF thành ảnh trước khi đưa qua OCR.
- **Windows:** Tải bản Release cho Windows tại [Poppler for Windows](https://github.com/oschwartz10612/poppler-windows/releases/), giải nén và thêm thư mục `bin` vào biến môi trường `PATH`.
- **macOS:** Mở Terminal và gõ: `brew install poppler`
- **Linux (Ubuntu):** Mở Terminal và gõ: `sudo apt-get install poppler-utils`

---

## 2. Cài đặt thư viện Python (Python Dependencies)

Sau khi cài đặt xong Tesseract và Poppler, bạn tiến hành cài đặt các thư viện Python:

```bash
# Di chuyển vào thư mục ai-service
cd ai-service

# Tạo môi trường ảo (Khuyến nghị)
python -m venv venv

# Kích hoạt môi trường ảo
# Trên Windows:
.\venv\Scripts\activate
# Trên macOS/Linux:
source venv/bin/activate

# Cài đặt requirements
pip install -r requirements.txt
```

---

## 3. Chạy Unit Test (Kiểm thử hệ thống)

Để đảm bảo môi trường của bạn đã được thiết lập đúng 100%, hãy chạy các lệnh test sau. Tất cả các bài test phải hiển thị kết quả `OK`.

### Test 1: Kiểm tra Document Parser & OCR
Lệnh này sẽ trích xuất chữ từ cả PDF Native và PDF Scan. Nếu bạn chưa cài Tesseract, bài test này sẽ báo lỗi `FAIL` (do trả về 0 pages).
```bash
python -m unittest tests/test_document_parser.py
```
👉 **Kết quả:** Kiểm tra thư mục `data/test_outputs/test_output_document_parser.json` để xem raw text và metadata được trích xuất.

### Test 2: Kiểm tra Dynamic Structure Analyzer (Cây cấu trúc động)
Lệnh này test thuật toán nhận diện và phân cấp cấu trúc (Chương, Điều, Khoản...) độc quyền của dự án:
```bash
python -m unittest tests/test_block_analyzer.py
```
👉 **Kết quả:** Kiểm tra thư mục `data/test_outputs/test_output_block_analyzer.json` để xem từng Node văn bản đã được gắn `Depth`, `Confidence` và `section_path` chuẩn xác.

---

## 4. Troubleshooting (Khắc phục sự cố)

1. **Lỗi `tesseract is not installed or it's not in your PATH`**
   - Giải quyết: Kiểm tra lại biến môi trường `PATH` xem đã có đường dẫn tới thư mục cài đặt Tesseract chưa. Khởi động lại IDE/Terminal sau khi thêm PATH.
   
2. **Lỗi `Unable to get page count` hoặc liên quan đến `pdfinfo`**
   - Giải quyết: Do chưa cài đặt Poppler hoặc chưa đưa thư mục `bin` của Poppler vào biến môi trường `PATH`.
