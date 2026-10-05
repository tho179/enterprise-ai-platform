# 📘 CẤU TRÚC ĐỒ ÁN TỐT NGHIỆP

> **Đề tài:** Hệ thống quản lý tri thức doanh nghiệp và xử lý yêu cầu nghiệp vụ ứng dụng RAG và AI tạo sinh
>
> **Nhóm:** Thọ · Đạt · Đức

---

## MỞ ĐẦU

- Lý do chọn đề tài
- Mục tiêu nghiên cứu
- Đối tượng và phạm vi nghiên cứu
- Phương pháp nghiên cứu
- Ý nghĩa khoa học và thực tiễn
- Cấu trúc đồ án

---

## CHƯƠNG 1. TỔNG QUAN VỀ BÀI TOÁN VÀ HỆ THỐNG

### 1.1. Đặt vấn đề
### 1.2. Bối cảnh và nhu cầu thực tế
### 1.3. Bài toán cần giải quyết
### 1.4. Mục tiêu của đề tài
### 1.5. Phạm vi của đề tài
### 1.6. Đối tượng sử dụng
### 1.7. Phân tích yêu cầu
### 1.8. Các chức năng chính của hệ thống
### 1.9. Ý tưởng và điểm mới của đề tài
### 1.10. Tổng quan giải pháp
### 1.11. Kết luận chương

---

## CHƯƠNG 2. CÁC KỸ THUẬT AI/DEEP LEARNING VÀ THỰC NGHIỆM

*(Ghi chú: Chương này tập trung vào Kỹ thuật / Thuật toán là gì, tại sao chọn, và thực nghiệm lựa chọn. Không chứa logic code chi tiết).*

### 2.1. Tổng quan Deep Learning và Generative AI
### 2.2. Large Language Model (LLM)
### 2.3. Embedding và Semantic Representation
### 2.4. Các mô hình Embedding được lựa chọn
### 2.5. Tokenization
### 2.6. Các kỹ thuật AI sử dụng trong xử lý tài liệu
- **2.6.1. Document Parsing:** Trích xuất text từ tài liệu PDF/DOCX.
- **2.6.2. OCR:** Phương pháp nhận dạng ký tự quang học xử lý tài liệu scan.
- **2.6.3. Block/Structure Analysis:** Kỹ thuật nhận diện thành phần văn bản (Heading, Paragraph, Table).
- **2.6.4. Dynamic Hierarchy:** Thuật toán Stack để xác định phả hệ văn bản.
- **2.6.5. Adaptive Chunking:** Phân tích hạn chế của Fixed-size chunking và đề xuất chiến lược chunking dựa trên cấu trúc ngữ nghĩa (Structure-aware chunking).

### 2.7. Các kỹ thuật AI bổ sung
- **2.7.1. Entity Extraction**
- **2.7.2. Relationship Extraction**
- **2.7.3. Reranking**
- **2.7.4. Classification**

### 2.8. Thiết kế thực nghiệm
- Mô tả dataset, tiêu chí đánh giá các mô hình AI/DL (đặc biệt là mô hình Embedding).

### 2.9. Kết quả thử nghiệm và lựa chọn mô hình
- Trình bày kết quả đánh giá (Model A vs Model B) và quyết định lựa chọn.

### 2.10. Kết luận chương

---

## CHƯƠNG 3. KNOWLEDGE GRAPH VÀ RAG

*(Ghi chú: Chương này tập trung vào lý thuyết và thực nghiệm các phương pháp RAG).*

### 3.1. Tổng quan RAG
### 3.2. Vector Database
### 3.3. Vector Retrieval
### 3.4. Knowledge Graph
### 3.5. Graph Database (Neo4j)
### 3.6. Entity và Relationship
### 3.7. Graph Retrieval
### 3.8. GraphRAG
### 3.9. Hybrid Retrieval
- **3.9.1. Vector Search**
- **3.9.2. Graph Search**
- **3.9.3. Fusion (Kết hợp kết quả)**
- **3.9.4. Reranking**
*(Lưu ý: Sử dụng tên gọi "Hybrid GraphRAG" hoặc "Graph-enhanced RAG" để mô tả chính xác phạm vi cài đặt thực tế).*

### 3.10. Quy trình sinh câu trả lời
### 3.11. Citation và truy xuất nguồn
### 3.12. Thử nghiệm và đánh giá RAG
- **3.12.1. Dataset thử nghiệm**
- **3.12.2. Retrieval evaluation**
- **3.12.3. Answer quality**
- **3.12.4. Citation accuracy**
- **3.12.5. So sánh Vector RAG vs GraphRAG vs Hybrid GraphRAG**

### 3.13. Kết luận chương

---

## CHƯƠNG 4. THIẾT KẾ HỆ THỐNG VÀ PIPELINE

*(Ghi chú: Dành cho Thiết kế Hệ thống + Service + Implementation Pipeline hoạt động thực tế).*

### 4.1. Kiến trúc tổng thể
### 4.2. Kiến trúc các Service
- Frontend
- Spring Boot
- AI Service

### 4.3. Thiết kế cơ sở dữ liệu
- ERD
- PostgreSQL

### 4.4. Thiết kế các module (Backend/Nghiệp vụ)
### 4.5. Document Processing Pipeline
- Trình bày chi tiết luồng xử lý: `document_parser.py` → `block_analyzer.py` → `structure_analyzer.py` → `adaptive_chunker.py` → `metadata_enricher.py`.

### 4.6. Knowledge Base Construction Pipeline
### 4.7. RAG / GraphRAG Pipeline
### 4.8. Business Workflow
### 4.9. Thiết kế API / Service Communication
### 4.10. Use Case Diagram
### 4.11. Activity Diagram
### 4.12. Sequence Diagram
### 4.13. Component / Package Diagram
### 4.14. Deployment Architecture
### 4.15. Kết luận chương

---

## CHƯƠNG 5. TRIỂN KHAI, KIỂM THỬ VÀ KẾT QUẢ

*(Ghi chú: Chương này không đi sâu vào DevOps, mà tập trung chứng minh hệ thống hoạt động thực tế và các kết quả kiểm thử).*

### 5.1. Môi trường triển khai
### 5.2. Triển khai hệ thống
- Mô tả ngắn gọn cách cấu hình chạy Docker (PostgreSQL, Qdrant, Neo4j) và các service để chứng minh hệ thống khả thi.

### 5.3. Kịch bản kiểm thử (Test Cases)
- 5.3.1. Test Case Authentication
- 5.3.2. Test Case Document Management
- 5.3.3. Test Case RAG
- 5.3.4. Test Case Knowledge Graph
- 5.3.5. Test Case Workflow
- 5.3.6. Test Case RBAC

### 5.4. Kết quả kiểm thử chức năng
- Bảng thống kê kết quả Pass/Fail cho các Test Cases nghiệp vụ.

### 5.5. Kết quả kiểm thử AI/RAG
- Đánh giá chất lượng xử lý văn bản, tỷ lệ trích xuất đúng, độ chính xác của Citation.

### 5.6. Kết quả đánh giá Vector RAG / GraphRAG / Hybrid
- Tóm tắt lại kết quả thực nghiệm phương pháp tìm kiếm tốt nhất.

### 5.7. Kết quả thực hiện các nghiệp vụ
- Thực tế xử lý đơn nghỉ phép, yêu cầu IT, phân quyền người dùng...

### 5.8. Kết quả Demo hệ thống
- Các màn hình giao diện (UI) chính và luồng trải nghiệm người dùng thực tế.

### 5.9. Đánh giá hệ thống
### 5.10. Hạn chế
### 5.11. Kết luận chương

---

## KẾT LUẬN

- Kết quả đạt được
- Những đóng góp của đề tài
- Hạn chế
- Hướng phát triển

---

## TÀI LIỆU THAM KHẢO

---

## PHỤ LỤC

- Phụ lục A: Chi tiết các Test Case (Bảng số liệu chi tiết)
- Phụ lục B: Bộ câu hỏi thử nghiệm RAG
- Phụ lục C: Mã nguồn các thuật toán cốt lõi
