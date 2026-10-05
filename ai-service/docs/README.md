# Tài Liệu Hệ Thống Enterprise AI Platform (AI-Service)

Chào mừng bạn đến với thư mục tài liệu chính thức của khối `ai-service`.
Để đảm bảo tính khoa học và chuẩn mực của một dự án Enterprise, toàn bộ tài liệu (bao gồm báo cáo đồ án, thiết kế hệ thống, và API) được quy hoạch theo phân cấp dưới đây.

## Cấu Trúc Thư Mục

```text
docs/
├── thesis/           # Lưu trữ các Chương của Đồ án tốt nghiệp / Báo cáo khoa học
│   ├── chapter_01_introduction.md
│   ├── chapter_02_theoretical_basis.md
│   ├── chapter_03_document_processing_pipeline.md  <-- (Chương 3 Pipeline Xử lý tài liệu)
│   ├── chapter_04_vector_database_and_rag.md
│   └── chapter_05_conclusion.md
│
├── architecture/     # Tài liệu Thiết kế Hệ thống (System Design)
│   ├── document_pipeline.md      # Chi tiết kỹ thuật về 5 bước xử lý PDF
│   ├── qdrant_schema.md          # Thiết kế Schema cho Vector DB
│   └── rbac_security.md          # Cơ chế phân quyền RBAC
│
└── api/              # Tài liệu API giao tiếp (REST / gRPC)
    └── openapi.yaml              # API Spec giao tiếp với Spring Boot Backend
```

## Hướng Dẫn Định Dạng (Markdown Guidelines)

1. **Naming Convention**: 
   - Tên file sử dụng chuẩn `snake_case` thuần tiếng Anh hoặc tiếng Việt không dấu (vd: `chapter_03_document_processing_pipeline.md`).
   - Tuyệt đối không dùng dấu cách, ký tự đặc biệt, hay tiếng Việt có dấu ở tên file.
2. **Diagrams**: 
   - Mọi sơ đồ khối, luồng dữ liệu, phả hệ phải sử dụng cú pháp `mermaid` để vẽ trực tiếp trên Markdown, giúp dễ dàng version control (Git) và review.
3. **Code Snippets**: 
   - Mọi giải pháp kỹ thuật cần được dẫn chứng bằng đoạn Code lõi (Core logic snippet), ghi rõ ngôn ngữ (python, json, java, v.v.).
