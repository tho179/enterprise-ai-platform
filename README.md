# Enterprise AI Platform

Hệ thống AI doanh nghiệp đa nền tảng (Enterprise AI Platform) tích hợp xử lý tài liệu thông minh (Intelligent Document Processing - IDP), OCR, Phân cấp cấu trúc cây động (Dynamic Structure Hierarchy), RAG đa ngữ (Multilingual Semantic Search), Vector Database (Qdrant), và Core APIs (Spring Boot).

---

## 🚀 Khởi động nhanh (Quickstart với Docker - Zero Setup)

Toàn bộ hệ thống đã được đóng gói container hóa hoàn chỉnh. Bạn **không cần cài đặt Java, Python, Tesseract, Poppler hay Database** lên máy host.

### 1. Yêu cầu duy nhất
- Đã cài đặt [Docker Desktop](https://www.docker.com/products/docker-desktop/) (Windows / macOS / Linux) và đang mở.

### 2. Khởi chạy toàn bộ hệ thống
```bash
# Clone dự án (nếu chưa có)
git clone https://github.com/tho179/enterprise-ai-platform.git
cd enterprise-ai-platform

# Khởi động toàn bộ 5 dịch vụ chỉ với 1 câu lệnh
docker compose up -d
```

### 3. Danh sách các dịch vụ & Cổng truy cập (Service Endpoints)

| Dịch vụ | Công nghệ | Cổng / URL | Mô tả |
| :--- | :--- | :--- | :--- |
| **Backend API** | Spring Boot 4 / Java 17 | [http://localhost:8080](http://localhost:8080) | Hệ thống quản lý người dùng, phân quyền JWT, Core Business API |
| **AI Service** | FastAPI / Python 3.11 | [http://localhost:8001](http://localhost:8001) | RAG Pipeline, PDF Parser, Tesseract OCR, Chunking, Embeddings |
| **AI Swagger Docs** | OpenAPI | [http://localhost:8001/docs](http://localhost:8001/docs) | Giao diện tương tác và thử nghiệm trực tiếp các API của AI Service |
| **Qdrant Vector DB** | Qdrant Engine | [http://localhost:6333](http://localhost:6333) | Vector Database lưu trữ Embedding 384 chiều đa ngữ |
| **Qdrant Dashboard** | Web UI | [http://localhost:6333/dashboard](http://localhost:6333/dashboard) | Giao diện trực quan xem các Collections và Vectors |
| **PostgreSQL** | Postgres 15 | `localhost:5432` | Cơ sở dữ liệu quan hệ (Database: `enterprise_ai_db`) |
| **Redis** | Redis 7 Alpine | `localhost:6379` | Cache tốc độ cao và hàng đợi xử lý nền |

### 4. Dừng hệ thống
```bash
docker compose down
```

---

## 📁 Cấu trúc thư mục Monorepo

```
enterprise-ai-platform/
├── backend/               # Mã nguồn Spring Boot (Java 17, JPA, JWT, Postgres, Redis)
│   ├── Dockerfile         # Multi-stage build (Maven 3.9 -> Eclipse Temurin JRE 17)
│   └── src/               # Java Controllers, Services, Repositories
├── ai-service/            # Mã nguồn AI Service (Python 3.11, FastAPI, PyTorch, PyMuPDF, OCR)
│   ├── Dockerfile         # Đóng gói kèm Tesseract OCR tiếng Việt, Poppler, PyTorch CPU
│   ├── app/               # Parser, OCR, Structure Analyzer, Embeddings, Qdrant, Retriever
│   ├── scripts/           # Ingest data, Test Semantic Retrieval, Debug scripts
│   ├── tests/             # Bộ Unit Tests tự động
│   └── data/              # Dữ liệu tài liệu mẫu (sample PDFs)
├── docker-compose.yml     # File điều phối toàn bộ cụm dịch vụ (Zero-Setup)
├── .env.example           # Mẫu biến môi trường cấu hình
├── SETUP.md               # Hướng dẫn chi tiết thiết lập môi trường
└── README.md              # Giới thiệu dự án và hướng dẫn khởi chạy
```

---

## 🛠️ Thao tác kiểm thử AI Service trong Docker

### Chạy Unit Test bên trong Container:
```bash
docker compose exec ai-service pytest tests/ -v
```

### Chạy nạp dữ liệu Vector vào Qdrant (Ingestion):
```bash
docker compose exec ai-service python scripts/07_run_qdrant_ingest.py
```

### Thử nghiệm tìm kiếm ngữ nghĩa (Semantic Search):
```bash
docker compose exec ai-service python scripts/08_test_retrieval.py
```

---

## 📋 Lệnh thao tác Docker thông dụng

| Nhu cầu | Lệnh thực hiện |
| :--- | :--- |
| **Xem logs toàn bộ hệ thống** | `docker compose logs -f` |
| **Xem logs riêng AI Service** | `docker compose logs -f ai-service` |
| **Xem logs riêng Backend** | `docker compose logs -f backend` |
| **Khởi động lại một dịch vụ** | `docker compose restart ai-service` |
| **Cập nhật & Rebuild khi sửa Dockerfile** | `docker compose up -d --build` |
| **Dừng hệ thống** | `docker compose down` |
| **Dừng & Xóa sạch toàn bộ dữ liệu (Reset)** | `docker compose down -v` |

