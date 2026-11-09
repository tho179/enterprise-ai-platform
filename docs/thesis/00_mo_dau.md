# MỞ ĐẦU

### 1. Tính cấp thiết của đề tài

Trong các tổ chức và doanh nghiệp hiện nay, khối lượng tài liệu nội bộ (điều lệ, nội quy lao động, quy chế tài chính, quy trình kỹ thuật) ngày càng gia tăng. Việc khai thác nguồn tri thức này phần lớn vẫn dựa vào thao tác thủ công (mở thư mục, tra cứu từ khóa, đọc lướt văn bản), dẫn đến mất nhiều thời gian, dễ sai lệch phiên bản và gây quá tải cho các bộ phận hỗ trợ như Nhân sự (HR) và Công nghệ thông tin (IT). Bên cạnh đó, các yêu cầu nghiệp vụ phát sinh (xin nghỉ phép, yêu cầu hỗ trợ kỹ thuật) thường bị tách rời khỏi quy trình tra cứu chính sách, làm giảm tính liền mạch trong vận hành.

Mặc dù các Mô hình ngôn ngữ lớn (LLM) mang lại khả năng thấu hiểu và giao tiếp tự nhiên vượt trội, nhưng việc ứng dụng trực tiếp vào doanh nghiệp gặp phải hai rào cản lớn: hiện tượng "ảo giác" (hallucination) và việc không thể truy cập dữ liệu nội bộ bảo mật. Kỹ thuật RAG (Retrieval-Augmented Generation) kết hợp cùng Knowledge Graph ra đời nhằm khắc phục hạn chế này. Xuất phát từ nhu cầu thực tiễn đó, nhóm nghiên cứu thực hiện đề tài: **"Hệ thống quản lý tri thức doanh nghiệp và xử lý yêu cầu nghiệp vụ ứng dụng RAG và AI tạo sinh" (EAKWP)** nhằm cung cấp giải pháp tra cứu tri thức chính xác có trích dẫn nguồn và tự động hóa các luồng công việc nghiệp vụ.

---

### 2. Mục tiêu nghiên cứu

- **Mục tiêu tổng quát:** Xây dựng nền tảng Enterprise AI Knowledge & Workflow Platform (EAKWP) hợp nhất giữa quản lý tri thức nội bộ và xử lý yêu cầu nghiệp vụ, ứng dụng kỹ thuật RAG, Vector Search, Knowledge Graph và AI tạo sinh.
- **Mục tiêu cụ thể:**
  1. Xây dựng pipeline xử lý tài liệu thông minh 5 bước: tiếp nhận PDF (kể cả bản scan qua OCR), phân tích cấu trúc khối (Block Analysis), phân cấp động (Dynamic Hierarchy) và cắt đoạn thích ứng (**Adaptive Chunking**) bảo toàn ngữ cảnh pháp lý.
  2. Nghiên cứu thực nghiệm, đánh giá và lựa chọn mô hình nhúng vector (Embedding) tối ưu cho văn bản tiếng Việt; tích hợp cơ sở dữ liệu vector chuyên dụng Qdrant.
  3. Thiết kế kiến trúc tìm kiếm ngữ nghĩa kết hợp duyệt đồ thị tri thức (**Hybrid GraphRAG** trên Neo4j) giúp trả lời chính xác và minh bạch nguồn trích dẫn (Citation-grounded).
  4. Tự động hóa tiếp nhận và xử lý 2 quy trình nghiệp vụ điển hình: đơn xin nghỉ phép và yêu cầu hỗ trợ IT (phân loại tự động, định tuyến phê duyệt).
  5. Hiện thực hóa kiến trúc Microservices phân tách rõ ràng giữa Core Backend (Spring Boot) và AI Service (FastAPI), đóng gói chuẩn Docker Zero-Setup.

---

### 3. Đối tượng và phạm vi nghiên cứu

- **Đối tượng nghiên cứu:**
  - Tài liệu văn bản nội bộ doanh nghiệp bằng tiếng Việt (PDF native và PDF scan như Nội quy lao động, Điều lệ công ty).
  - Các kỹ thuật trích xuất văn bản, OCR, Text Embedding, Vector Database (Qdrant), Graph Database (Neo4j), LLM và quy trình nghiệp vụ workflow.
- **Phạm vi nghiên cứu:**
  - Triển khai trong mạng nội bộ / Private Cloud bảo đảm bảo mật dữ liệu.
  - Tập trung giải quyết 2 bài toán cốt lõi: Hỏi đáp tri thức kèm trích dẫn (Chương, Điều, Khoản, Trang) và Xử lý đơn nghỉ phép, Ticket IT.

---

### 4. Phương pháp nghiên cứu

- **Phương pháp lý thuyết:** Nghiên cứu các kiến trúc RAG tiên tiến, biểu diễn ngữ nghĩa Dense Embedding, mô hình Labeled Property Graph (LPG) và các kỹ thuật chống ảo giác cho LLM.
- **Phương pháp thực nghiệm (Benchmark):** Đo lường định lượng các mô hình Embedding bằng bộ chỉ số chuẩn (Recall@K, MRR, độ trễ suy luận) trên dữ liệu thực tế để chọn ra phương án tối ưu.
- **Phương pháp phân tích & thiết kế hướng đối tượng (OOAD):** Áp dụng quy trình phân tích ca sử dụng (Use Case), biểu đồ giao tiếp, biểu đồ tuần tự và biểu đồ lớp theo chuẩn kỹ nghệ phần mềm.

---

### 5. Ý nghĩa khoa học và thực tiễn

- **Ý nghĩa khoa học:** Đề xuất giải pháp Adaptive Chunking tôn trọng phả hệ văn bản hành chính Việt Nam; chứng minh hiệu quả của mô hình kết hợp Vector Search và Knowledge Graph trong việc giảm thiểu ảo giác của mô hình tạo sinh.
- **Ý nghĩa thực tiễn:** Giúp doanh nghiệp rút ngắn thời gian tìm kiếm quy định từ hàng chục phút xuống dưới 1 giây; giảm tải 70–80% các câu hỏi thường gặp cho bộ phận HR/IT; hỗ trợ tự động hóa nghiệp vụ trên cùng một giao diện tập trung.

---

### 6. Bố cục của đồ án

Báo cáo đồ án được kết cấu thành **5 chương**:

- **Chương 1: Tổng quan về bài toán và hệ thống:** Giới thiệu bối cảnh, bài toán, yêu cầu chức năng/phi chức năng, đối tượng sử dụng và tổng quan giải pháp đa tầng.
- **Chương 2: Các kỹ thuật AI/Deep Learning và thực nghiệm:** Trình bày lý thuyết về LLM, Embedding, Tokenization, các kỹ thuật xử lý tài liệu và kết quả benchmark lựa chọn mô hình.
- **Chương 3: Xử lý tài liệu và xây dựng dữ liệu cho RAG:** Trình bày chi tiết pipeline 5 bước bóc tách tài liệu, Vector DB, Knowledge Graph, quy trình Hybrid Retrieval và cơ chế Citation.
- **Chương 4: Thiết kế hệ thống và Pipeline:** Mô tả kiến trúc tổng thể, thiết kế cơ sở dữ liệu (PostgreSQL, Qdrant, Neo4j), đặc tả Use Case, biểu đồ tuần tự và thiết kế API giữa Spring Boot và FastAPI.
- **Chương 5: Triển khai, kiểm thử và kết quả:** Trình bày môi trường triển khai Docker, kết quả kiểm thử chức năng, đánh giá chất lượng truy xuất và giao diện demo thực tế của hệ thống.
