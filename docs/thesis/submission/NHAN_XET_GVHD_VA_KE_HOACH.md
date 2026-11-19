# Nhận xét của GVHD về bản Chương 2–5 và kế hoạch khắc phục

Ngày: 19/11/2026. Bản được nhận xét: `DO_AN_IN_CHUONG_2_5` (nộp 17/11/2026).

## 0. Nhận xét của thầy

- KB mà để dạng `.py` → **4đ**. Phải chuyển sang Cypher.
- Biểu đồ thiết kế layer không có chi tiết.
- Kết luận: **3,5đ**.
- Không thấy phân tích hợp thiết kế, KB (ghi là "LB") lưu ở đâu, RAG connect chỉ ra code → **4đ**.

Nguyên nhân chung: tài liệu mô tả "cái gì" kỹ, nhưng **tri thức, thiết kế và kết nối nằm trong mã Python** chứ không được thể hiện thành mô hình.

Ghi chú: "LB lưu ở đâu" được hiểu là gõ nhầm "KB lưu ở đâu" (K và L cạnh nhau trên bàn phím). Nếu thầy muốn hỏi về Load Balancer, xem mục 4d.

---

## 1. "KB để dạng .py" (4đ): lỗi nặng nhất

### Hiện trạng

Đã có 7 tệp `.cypher`, nhưng chúng chỉ **ghi dữ liệu**. **Tri thức** (luật, bản thể, ngưỡng) và **suy diễn** vẫn nằm trong Python:

| Tri thức | Đang nằm ở |
| :--- | :--- |
| Bản thể: chức danh, chủ đề, đồng nghĩa Anh–Việt | Từ điển `ROLE_ALIASES`, `TOPIC_ALIASES`, `ENGLISH_ALIASES` trong `ai-service/app/knowledge_graph/extract.py` (dòng 60–129) |
| Thuộc tính đơn trị (vốn điều lệ, mệnh giá) | `SINGLE_VALUED` trong `consistency.py` (dòng 143) |
| Độ tin cậy nguồn (pdf 1.0, web 0.6) | `SOURCE_TRUST` trong `extract.py` (dòng 434) |
| Luật giải quyết mâu thuẫn R1–R5 | Hàm `_priority` trong `consistency.py` (dòng 224) |
| Hợp nhất thực thể mờ, phát hiện trùng lặp | `resolve.py`, `find_duplicates`. Cypher chỉ ghi kết quả đã tính sẵn (`WRITE_CONFLICTS`, `WRITE_DUPLICATES`) |
| Luật tác tử R1–R9 | Các `lambda` trong `ai-service/app/agent/rules.py` |

Chương 4 có 18 khối code Python và chỉ 13 khối Cypher. Phần "hợp nhất mờ" và "song ngữ" được minh họa bằng Python.

### Vì sao bị trừ điểm

Môn KB yêu cầu tri thức được **biểu diễn** trong hệ quản trị tri thức và **suy diễn** bằng ngôn ngữ truy vấn của hệ đó. Hiện tại nếu xóa các tệp `.py` thì KB mất toàn bộ luật. Neo4j mới làm kho lưu, chưa phải cơ sở tri thức.

### Phương án

Chuyển tri thức thành node/cạnh và suy diễn thành Cypher. Python chỉ còn làm OCR, regex và I/O.

1. **`00_ontology.cypher`** (mới), là dữ liệu thuần Cypher:
   ```cypher
   MERGE (t:EntityType {name:'chuc_danh'})
   MERGE (e:Entity {name:'Hội đồng Quản trị'})-[:INSTANCE_OF]->(t)
   MERGE (:Alias {text:'HĐQT'})-[:ALIAS_OF]->(e)
   MERGE (:Alias {text:'Board of Directors', lang:'en'})-[:ALIAS_OF]->(e)
   MERGE (:Attribute {name:'Vốn điều lệ', single_valued:true, kind:'money'})
   MERGE (:SourceType {name:'web', trust:0.6})
   ```
   Sau đó `extract.py` đọc alias từ Neo4j (`MATCH (a:Alias)-[:ALIAS_OF]->(e)`), không dùng dict nữa.
2. **Luật thành node:** `(:Rule {id:'R2_hieu_luc_moi_hon', priority:2, kind:'conflict'})`. Giải quyết mâu thuẫn bằng **một truy vấn Cypher**: sắp các `Claim` của cùng `Attribute` theo `d.is_current`, `d.effective_date`, `st.trust`, `c.confidence`, đặt `status` và tạo `CONFLICTS_WITH {rule: r.id}`.
3. **Hợp nhất thực thể bằng Cypher:** dùng `db.index.vector.queryNodes` (đã có chỉ mục 384 chiều) cộng `apoc.text.sorensenDiceSimilarity` (thêm plugin APOC vào `docker-compose.yml`). Hàm thuộc mờ low/high viết bằng `CASE`.
4. **Luật tác tử thành node:** `(:AgentRule {name, priority, action, needs_attribute, needs_article, ...})`. Bước chọn luật trở thành truy vấn `MATCH (r:AgentRule) WHERE ... ORDER BY r.priority LIMIT 1`, với tham số là quan sát của câu hỏi.
5. **Sản phẩm nộp:** xuất toàn bộ KB thành `kb_export.cypher` (`apoc.export.cypher.all`). Chỉ cần chạy `cypher-shell -f` là dựng lại được KB mà không cần Python.
6. **Viết lại Chương 4:** mỗi mục (hợp nhất, mâu thuẫn, phiên bản, song ngữ) minh họa bằng Cypher kèm ảnh kết quả trên Neo4j Browser. Python đưa xuống phụ lục.

---

## 2. "Biểu đồ thiết kế layer không có chi tiết"

### Hiện trạng

- `assets/vp/H2_13_lop_thiet_ke_backend.png`: 20 hộp tên lớp nối bằng nét đứt. Không có thuộc tính, phương thức, stereotype hay ranh giới tầng; không có Entity/DTO.
- `assets/vp/TK_goi.png`: các gói rỗng.
- **ai-service, nơi chứa toàn bộ RAG, KB và tác tử, không có biểu đồ lớp nào.** Mục 2.10 chỉ ghi "được trình bày ở Chương 3, 4, 5".

### Phương án (vẽ bằng Visual Paradigm theo quy trình XML hiện có)

- **Biểu đồ kiến trúc phân tầng**: Presentation → Application/Service → Domain → Infrastructure/Data access. Mỗi tầng ghi tên lớp thật của cả backend và ai-service.
- **Biểu đồ lớp chi tiết theo từng tầng**, có thuộc tính, phương thức và stereotype `«RestController»`, `«Service»`, `«Repository»`, `«Entity»`, `«DTO»`:
  - Backend: tách theo module Document, AI Gateway, Auth/User.
  - ai-service: `ChatRouter` → `RuleBasedAgent` → `RetrieveTool`/`KBAttributeTool` → `RAGService` → `Retriever`/`QdrantService`/`Neo4jStore`/`RerankerService`/`LLMClient`.
- **Bảng tầng → lớp → phương thức chính → phụ thuộc được phép**, kèm quy tắc "tầng trên chỉ gọi tầng dưới".

---

## 3. "Không thấy phân tích hợp thiết kế"

### Hiện trạng

Chương 2 đi thẳng từ use case và kịch bản sang biểu đồ tuần tự và lớp cài đặt. Không có mô hình lớp phân tích, không có bảng truy vết, không có lý do chọn thiết kế. Người đọc không thấy thiết kế sinh ra từ phân tích như thế nào.

### Phương án

- **Biểu đồ lớp phân tích BCE** (Boundary – Control – Entity) cho từng use case chính (Hỏi đáp, Nạp tài liệu, Quản trị KB). Chỉ gồm khái niệm, chưa có công nghệ.
- **Ma trận truy vết**: Use case → lớp phân tích → lớp thiết kế → API → bảng PostgreSQL / node Neo4j.
- **Mục quyết định thiết kế**: với mỗi quyết định (microservice, polyglot persistence, KB trên Neo4j, tác tử luật) nêu phương án thay thế, tiêu chí và lý do chọn.

---

## 4. "KB lưu ở đâu" và "RAG connect chỉ ra code" (4đ)

### 4a. KB lưu ở đâu

Tài liệu chỉ ghi "Neo4j". Thực tế KB đang nằm ở ba nơi:

- Dữ liệu nằm trong Neo4j, database `neo4j`, volume `neo4j_data`.
- KB1, KB2 và KB không phải ba CSDL riêng mà là ba node `KnowledgeBase` trong cùng một DB.
- Luật và bản thể nằm trong file `.py`.

**Phương án:** thêm mục riêng **"Lưu trữ KB"**, gồm:

- Sơ đồ đi từ artifact KB, qua database Neo4j và volume, xuống đĩa.
- Giải thích cách phân vùng logic KB1/KB2/KB bằng node `KnowledgeBase`.
- Vị trí tệp nguồn, tệp `.cypher` và bản export, cùng cách sao lưu và khôi phục.

Sau khi làm xong mục 1, câu trả lời gọn lại: **toàn bộ KB nằm trong Neo4j**.

### 4b. Lỗi thực chất: KB1/KB2 không được RAG của người dùng dùng

API chat mặc định `CHAT_GRAPH_SOURCE_TYPE="upload"` (`ai-service/app/config.py`, dòng 131). Vì vậy **KB1 (35 PDF) và KB2 (10 trang web) mà Chương 4 xây dựng không được RAG của người dùng sử dụng**; chỉ script đánh giá mới dùng chúng. Mục 5.4 có nhắc điều này nhưng đi ngược với thông điệp "RAG nối KB".

**Phương án:**

- Nạp 35 PDF qua backend để trích dẫn mở được, **hoặc**
- Cho phép trích dẫn dạng link với `source_type=web/pdf` (dùng `source_uri`), rồi bỏ bộ lọc `upload`.

### 4c. RAG connect: chỉ ra code

Code ở mục 4.16.2 và 5.3 đều "rút gọn" và dừng ở lời gọi hàm Python. Phần còn thiếu là **điểm kết nối thật**:

- Chuỗi env `NEO4J_URI` → `GraphDatabase.driver` (`knowledge_graph/store.py`, dòng 14) → `Neo4jStore.query` → truy vấn `GRAPH_CANDIDATES` (`cypher/05_retrieval.cypher`, dòng 15).
- Sau đó `_fuse_hits` trộn RRF → context của prompt.

**Phương án:**

- Viết mục **"Truy vết một câu hỏi"**: một câu hỏi thật → tham số Cypher đã gửi → các hàng Neo4j trả về → điểm RRF → đoạn đưa vào LLM → câu trả lời có trích dẫn.
- Code để nguyên văn với số dòng đúng (hiện có chỗ ghi "dòng 98-127" nhưng đã lệch).
- Biểu đồ tuần tự H4_7 ghi tên phương thức thật ở từng thông điệp.

### 4d. Nếu "LB" là Load Balancer

Kiến trúc hiện không có cân bằng tải hay API gateway. Nginx chỉ phục vụ frontend, mỗi dịch vụ chạy một bản sao, và `@Async` chạy trong tiến trình nên không mở rộng ngang được.

**Phương án:** thêm mục giải thích Nginx/Traefik upstream trước backend, `deploy.replicas`, và điều kiện cần có (hàng đợi cho tác vụ nạp, backend không giữ trạng thái).

---

## 5. Các khiếm khuyết khác trong dự án và tài liệu

| # | Vấn đề | Đề xuất |
| :--- | :--- | :--- |
| 1 | Luật R6 (truy xuất lai theo thực thể) tắt mặc định, trọng số đồ thị chỉ 0,2. KB đóng góp ít mà không có số liệu chứng minh | Thêm bảng ablation có/không có KB trên cùng bộ câu hỏi, nêu rõ KB thắng ở loại câu hỏi nào |
| 2 | Bộ đánh giá chỉ có 26 câu | Mở rộng lên ≥ 100 câu, chia theo loại (thuộc tính, dẫn chiếu, phiên bản) |
| 3 | Không có khóa ngoại vật lý, không có hàng đợi, lịch sử chat nằm ở `localStorage` (đã tự nhận ở 2.14) | Làm ít nhất migration Flyway V3 thêm FOREIGN KEY, vì chi phí thấp |
| 4 | `qdrant/qdrant:latest` không cố định phiên bản | Ghim phiên bản cụ thể |
| 5 | Backend chỉ có 3 tệp test | Thêm test cho `DocumentService`, `IngestionService` và phân quyền |
| 6 | Thư mục `submission/` có khoảng 10 bản trùng (`bao_cao_3_chuong`, `in_chuong_3_4`, `do_an_chuong_3_6`…) | Dễ nộp nhầm bản. Chuyển bản cũ vào `archive/`, giữ một nguồn duy nhất |
| 7 | Chương 6 (`chuong_6_ket_qua.md`) chưa có trong bản in | Ghép vào bản in |

---

## 6. Thứ tự thực hiện

1. **Chuyển KB sang Cypher** (mục 1), phần mất điểm nhiều nhất. Ước tính 2–3 ngày: viết ontology và luật dạng node, chuyển suy diễn sang Cypher, xuất `kb_export.cypher`, chạy lại `scripts/18_evaluate_kb.py` để chứng minh kết quả không đổi.
2. **Sửa đường RAG ↔ KB1/KB2** (4b) và viết mục "Truy vết một câu hỏi" (4c).
3. **Vẽ lại biểu đồ phân tầng chi tiết và biểu đồ lớp ai-service** (mục 2), thêm lớp phân tích BCE và ma trận truy vết (mục 3).
4. Viết mục "Lưu trữ KB" và mục cân bằng tải, rồi dựng lại bản in.

## 7. Tiến độ

| Hạng mục | Trạng thái |
| :--- | :--- |
| 1. KB sang Cypher | Chưa làm |
| 2. RAG ↔ KB1/KB2, truy vết câu hỏi | Chưa làm |
| 3. Biểu đồ phân tầng, BCE, ma trận truy vết | Chưa làm |
| 4. Lưu trữ KB, cân bằng tải, dựng lại bản in | Chưa làm |
