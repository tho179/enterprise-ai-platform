# Enterprise AI Platform

Đây là dự án hệ thống AI đa nền tảng, được tổ chức dưới dạng monorepo với các thành phần chính sau:

## Cấu trúc thư mục

- `backend/`: Chứa mã nguồn dự án Spring Boot (Core APIs).
- `ai-service/`: Chứa các dịch vụ Python FastAPI xử lý RAG và tích hợp LLM.
- `frontend/`: Giao diện người dùng viết bằng React (Sẽ phát triển sau).
- `infrastructure/`: Các script và tệp cấu hình triển khai, database, CI/CD.
- `docs/`: Tài liệu kiến trúc, báo cáo đồ án, sơ đồ cơ sở dữ liệu.

## Chạy các dịch vụ nội bộ (Infrastructure)

Để khởi động Database (PostgreSQL), Redis và Qdrant, sử dụng Docker Compose:

```bash
docker-compose up -d
```
