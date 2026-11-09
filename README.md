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

# Tạo cấu hình và điền các secret bắt buộc (mỗi giá trị: openssl rand -hex 48)
cp .env.example .env

# Khởi động 7 dịch vụ: frontend, backend, ai-service, postgres, redis, qdrant, neo4j
docker compose up -d
```

Compose dừng ngay kèm thông báo nếu thiếu `POSTGRES_PASSWORD`, `NEO4J_PASSWORD`,
`QDRANT_API_KEY`, `INTERNAL_API_TOKEN` hoặc `JWT_SECRET`.

### 3. Danh sách các dịch vụ & Cổng truy cập (Service Endpoints)

| Dịch vụ | Công nghệ | Cổng / URL | Mô tả |
| :--- | :--- | :--- | :--- |
| **Frontend** | React + nginx | [http://localhost:3000](http://localhost:3000) | Giao diện người dùng, cổng vào duy nhất cho trình duyệt |
| **Backend API** | Spring Boot 4 / Java 17 | [http://localhost:8080](http://localhost:8080) | JWT, RBAC, quản lý tài liệu, AI Gateway (`/api/ai/*`), audit, rate limit |
| **AI Service** | FastAPI / Python 3.11 | `127.0.0.1:8001` | OCR, chunking, embedding, GraphRAG. Chỉ nhận lời gọi có `X-Internal-Token` từ backend |
| **Qdrant** | Qdrant | `127.0.0.1:6333` | Vector 384 chiều, yêu cầu API key |
| **Neo4j** | Neo4j 5 Community | `127.0.0.1:7474`, `7687` | Knowledge graph, cùng `chunk_id` với Qdrant |
| **PostgreSQL** | Postgres 15 | `127.0.0.1:5432` (`POSTGRES_PORT`) | Dữ liệu nghiệp vụ, schema do Flyway quản lý |
| **Redis** | Redis 7 Alpine | `127.0.0.1:6379` | Bộ đếm rate limit của AI Gateway |
| **Ollama** (tùy chọn) | profile `local-llm` | `127.0.0.1:11434` | LLM cục bộ, API tương thích OpenAI |

Tài khoản demo do backend tạo trên DB trống: `admin@congty.vn`, `manager@congty.vn`,
`nva@congty.vn`, `it@congty.vn` (mật khẩu trong `DemoDataInitializer.java`).

### Bật LLM thật
Không cấu hình LLM thì câu trả lời là trích đoạn nguyên văn (`extractive-fallback`).

```bash
# Cục bộ (cần NVIDIA container runtime; bỏ dòng `gpus` trong compose để chạy CPU)
docker compose --profile local-llm up -d ollama
docker compose exec ollama ollama pull qwen2.5:3b
# Trong .env: LLM_BASE_URL=http://ollama:11434/v1 và LLM_MODEL=qwen2.5:3b

# Hoặc đám mây: đặt GEMINI_API_KEY hoặc OPENAI_API_KEY trong .env
```

### Phạm vi đã triển khai
| Mô-đun | Trạng thái |
| :--- | :--- |
| Xác thực, người dùng, RBAC | Chạy thật |
| Quản lý tài liệu, phiên bản, phân quyền xem theo vai trò | Chạy thật |
| Nạp PDF: OCR, chunk theo Chương/Mục/Điều, Qdrant + Neo4j | Chạy thật |
| Hỏi đáp có trích dẫn, tìm kiếm ngữ nghĩa, AI Gateway | Chạy thật |
| Nghỉ phép, phê duyệt, yêu cầu IT, thông báo | **Chỉ là giao diện mẫu** (`VITE_USE_MOCKS=true`), chưa có API |

### 4. Dừng hệ thống
```bash
docker compose down
```

---

## 📁 Cấu trúc thư mục Monorepo

```
enterprise-ai-platform/
├── frontend/              # React + Vite, phục vụ bằng nginx
├── backend/               # Mã nguồn Spring Boot (Java 17, JPA, JWT, Flyway, Postgres, Redis)
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

### Đổi embedding model / re-embed Qdrant:
Mặc định dùng `intfloat/multilingual-e5-small` (384 chiều). Query/passage prefix
được áp dụng trong code, không đặt trong Compose. Sau khi đổi model, chạy:
```bash
docker compose exec ai-service python scripts/12_reembed_qdrant.py
```

### Nạp lại tài liệu (sau khi đổi chunker hoặc model):
```bash
python ai-service/scripts/14_reindex_uploads.py --email admin@congty.vn --password <mật khẩu>
```

### Đồng bộ lại GraphRAG:
```bash
# Backfill chunk từ Qdrant vào Neo4j
docker compose exec ai-service python scripts/11_sync_qdrant_to_graph.py

# Tính lại entity và quan hệ từ các chunk đã có (sau khi sửa quy tắc trích xuất)
docker compose exec ai-service python scripts/13_reindex_graph_entities.py
```

### Đánh giá:
```bash
# So sánh flat_rag / graph_rag / hybrid_rag trên bộ câu hỏi đã gán nhãn
docker compose exec ai-service python scripts/15_run_eval.py --with-llm

# So sánh embedding có dấu và bỏ dấu
docker compose exec ai-service python scripts/17_benchmark_folding.py

# Kiểm thử đầu-cuối trên stack đang chạy
python ai-service/scripts/16_e2e_smoke.py --password <mật khẩu>
```
Kết quả và cách đọc số liệu: [docs/evaluation_graphrag.md](docs/evaluation_graphrag.md).

### Theo dõi vận hành:
- `GET /health/dependencies` (AI service): trạng thái Qdrant, Neo4j, LLM.
- `GET /api/v1/metrics/latency`: p50/p95 từng bước (embed, vector, graph, rerank, policy, LLM).
- `GET /api/ai/audit` (ADMIN): nhật ký câu hỏi qua gateway.

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

