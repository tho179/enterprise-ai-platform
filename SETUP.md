# Hướng dẫn Thiết lập Môi trường (Environment Setup Guide)

Dự án **Enterprise AI Platform** cung cấp 2 phương thức thiết lập môi trường:
1. **Phương pháp 1 (Khuyến nghị - Zero Setup):** Khởi chạy trọn gói qua **Docker** — Không cần cài đặt bất kỳ công cụ nào ngoài Docker Desktop.
2. **Phương pháp 2 (Dành cho nhà phát triển muốn chạy native trên máy host):** Cài đặt thủ công JDK, Python venv, Tesseract OCR, Poppler.

---

## 🚀 Phương pháp 1: Chạy trọn gói qua Docker (Khuyến nghị)

Toàn bộ môi trường bao gồm Java 17, Spring Boot, Python 3.11, FastAPI, Tesseract OCR tiếng Việt, Poppler, PyTorch CPU, PostgreSQL, Redis và Qdrant Vector DB đã được đóng gói sẵn trong Docker.

### 1. Chuẩn bị
- Cài đặt và bật [Docker Desktop](https://www.docker.com/products/docker-desktop/).

### 2. Khởi động toàn bộ dịch vụ
```bash
# Tại thư mục gốc của dự án:
docker compose up -d
```

### 3. Kiểm tra các dịch vụ
- **Backend API**: [http://localhost:8080](http://localhost:8080)
- **AI Service Swagger API**: [http://localhost:8001/docs](http://localhost:8001/docs)
- **Qdrant Vector Database**: [http://localhost:6333/dashboard](http://localhost:6333/dashboard)

### 4. Chạy Unit Tests và Scripts trong Docker
```bash
# Kiểm tra bộ test Document Parser & Structure Analyzer
docker compose exec ai-service pytest tests/ -v

# Nạp dữ liệu tài liệu vào Vector DB
docker compose exec ai-service python scripts/07_run_qdrant_ingest.py

# Test tìm kiếm ngữ nghĩa tiếng Việt
docker compose exec ai-service python scripts/08_test_retrieval.py
```

---

## 🛠️ Phương pháp 2: Cài đặt thủ công trên máy Host (Local Development)

Nếu bạn muốn debug trực tiếp mã nguồn trên máy cá nhân mà không qua container:

### 1. Yêu cầu hệ thống cho AI Service
- **Python**: Phiên bản 3.10 hoặc 3.11.
- **Tesseract OCR (Kèm tiếng Việt `vie`)**:
  - **Windows**: Tải từ [UB-Mannheim Tesseract](https://github.com/UB-Mannheim/tesseract/wiki), cài đặt vào `C:\Program Files\Tesseract-OCR` và thêm vào biến môi trường `PATH`. Tải thêm `vie.traineddata` đặt vào thư mục `tessdata`.
  - **macOS**: `brew install tesseract tesseract-lang`
  - **Ubuntu**: `sudo apt-get install tesseract-ocr tesseract-ocr-vie`
- **Poppler Utilities**:
  - **Windows**: Tải bản Release tại [Poppler for Windows](https://github.com/oschwartz10612/poppler-windows/releases/) và thêm `bin` vào `PATH`.
  - **macOS**: `brew install poppler`
  - **Ubuntu**: `sudo apt-get install poppler-utils`

### 2. Cài đặt Python Dependencies
```bash
cd ai-service
python -m venv venv

# Kích hoạt venv (Windows):
.\venv\Scripts\activate
# Kích hoạt venv (Linux/macOS):
source venv/bin/activate

pip install -r requirements.txt
```

### 3. Yêu cầu hệ thống cho Backend (Spring Boot)
- **JDK**: Eclipse Temurin hoặc OpenJDK 17+.
- **Maven**: Maven 3.9+ (hoặc dùng `./mvnw`).
```bash
cd backend
./mvnw clean compile
```

---

## ❓ Xử lý sự cố thường gặp (Troubleshooting)

1. **Lỗi Docker Desktop không nhận WSL 2 hoặc Hyper-V trên Windows:**
   - Mở PowerShell quyền Administrator: `wsl --update`
   - Bật tính năng ảo hóa trong BIOS (Intel VT-x hoặc AMD-V).
2. **Cổng mạng bị xung đột (Port conflict - 5432, 6379, 8080, 8001):**
   - Nếu máy bạn đang chạy PostgreSQL hoặc Redis cục bộ, hãy tắt dịch vụ cục bộ đó hoặc sửa cổng tương ứng trong `.env` (ví dụ `POSTGRES_PORT=5433`).
