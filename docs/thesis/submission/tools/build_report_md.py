"""Assemble the three chapters into one printable report (Markdown source)."""
from pathlib import Path
import re

BASE = Path(__file__).resolve().parent.parent
OUT = BASE / "bao_cao_3_chuong.md"

CHAPTERS = [
    BASE / "chuong_2_hoc_sau.md",
    BASE / "chuong_3_co_so_du_lieu.md",
    BASE / "chuong_4_co_so_tri_thuc.md",
]

COVER = """<!-- COVER:START -->
BỘ KHOA HỌC VÀ CÔNG NGHỆ
HỌC VIỆN CÔNG NGHỆ BƯU CHÍNH VIỄN THÔNG
KHOA CÔNG NGHỆ THÔNG TIN 1

---

**BÁO CÁO ĐỒ ÁN TỐT NGHIỆP**

**ĐỀ TÀI:**

# XÂY DỰNG NỀN TẢNG QUẢN LÝ TRI THỨC DOANH NGHIỆP ỨNG DỤNG HỌC SÂU VÀ TRUY XUẤT TĂNG CƯỜNG

Niên khóa: 2022–2027 — Hệ: Đại học chính quy

Giảng viên hướng dẫn: PGS.TS Trần Đình Quế

Sinh viên thực hiện:
- Nguyễn Quý Thọ – B22DCCN836
- Nguyễn Xuân Đạt – B22DCCN200
- Hoàng Lê Đức – B22DCCN224

Hà Nội - 2026
<!-- COVER:END -->
"""

INTRO = """<!-- BODY:START -->

## GHI CHÚ BIÊN TẬP VÀ CẤU TRÚC BÁO CÁO

### 1. Lý do cấu trúc lại

Bản báo cáo này được biên soạn lại trực tiếp từ phản hồi của giảng viên:

1. **Tên chương phải phản ánh đúng nội dung chính**, không dùng tên chung như “Các kỹ thuật AI” hay “Thiết kế hệ thống”.
2. **Chương Học sâu phải đủ chiều sâu**: có lý thuyết, công thức, thiết kế thực nghiệm, kết quả định lượng và phân tích.
3. **Chương Cơ sở tri thức phải đủ chiều sâu**: không chỉ mô tả pipeline, mà phải có mô hình tri thức, thuật toán phân đoạn, truy xuất lai, trích dẫn và đánh giá.
4. Nhiều nhóm bị **0,0 điểm** ở hai chương này vì nội dung mỏng, không gắn với sản phẩm, hoặc chỉ liệt kê công nghệ.

Ba chương dưới đây được viết lại theo hướng **“nội dung trước, công nghệ sau”**: mỗi chương trả lời một câu hỏi nghiên cứu, có mô hình lý thuyết, có quyết định thiết kế, có bằng chứng từ mã nguồn và thực nghiệm.

### 2. Đối chiếu cấu trúc cũ và mới

| Cấu trúc cũ | Cấu trúc mới | Ghi chú |
| :--- | :--- | :--- |
| Chương 2: “Các kỹ thuật AI/Deep Learning và thực nghiệm đánh giá mô hình” | **Chương 2: Deep Learning trong biểu diễn ngữ nghĩa: từ kiến trúc Transformer đến lựa chọn mô hình nhúng tiếng Việt** | Giữ mã chương 2; đổi tên theo nội dung; bổ sung toán học, InfoNCE, benchmark |
| Chương 3: “Knowledge Graph và RAG” | **Chương 4: Xây dựng Knowledge Base và cơ chế truy xuất tăng cường có trích dẫn** | Chuyển thành chương 4; đào sâu mô hình tri thức, phân đoạn, truy xuất lai, trích dẫn |
| Chương 4: “Thiết kế hệ thống và pipeline” — Phần III: Thiết kế cơ sở dữ liệu | **Chương 3: Thiết kế cơ sở dữ liệu đa mô hình cho nền tảng quản lý tri thức doanh nghiệp** | Tách Phần III (CSDL) thành chương 3; bổ sung mô hình 5 bảng, DDL, giao dịch, nhất quán đa kho |
| Chương 4: “Thiết kế hệ thống và pipeline” — các phần còn lại | Phần thiết kế hệ thống, triển khai, kiểm thử, kết luận | Chuyển sang Chương 5 (không nằm trong bản in ba chương này) |

Báo cáo gốc 127 trang của nhóm được lưu tại `original/bao_cao_goc_v5.pdf` để đối chiếu. Ba chương trong bản in này thay thế Chương 2, Chương 3 và Phần III của Chương 4 trong báo cáo gốc; phần thiết kế hệ thống còn lại của Chương 4 chuyển thành Chương 5 khi ghép bản đầy đủ.

Cách tách này giải quyết đúng hai vấn đề giảng viên nêu:

- **Tên chương** nói rõ chương nói về cái gì: “học sâu trong biểu diễn ngữ nghĩa”, “thiết kế cơ sở dữ liệu đa mô hình”, “xây dựng cơ sở tri thức và truy xuất có trích dẫn”.
- **Độ sâu** được đảm bảo bằng bốn lớp nội dung trong mỗi chương: cơ sở lý thuyết → thiết kế → triển khai thực tế → đánh giá và hạn chế.

### 3. Ba chương trong bản báo cáo

| Chương | Câu hỏi nghiên cứu | Đóng góp chính | Bằng chứng |
| :--- | :--- | :--- | :--- |
| **2. Học sâu** | Biểu diễn ngữ nghĩa tiếng Việt bằng mô hình nào, với kiến trúc và hàm mất mát nào, và mô hình nào phù hợp với EAKWP? | Transformer, self-attention, bi-encoder, InfoNCE, thiết kế thực nghiệm, chọn E5-Small | Benchmark 3 mô hình trên 152 chunk; Recall@3 100%, MRR 0,90 |
| **3. Cơ sở dữ liệu** | Làm sao lưu trữ tài liệu, phiên bản, đoạn trích và vector một cách nhất quán, truy vết được, mở rộng được? | Mô hình 5 bảng, DDL, chuẩn hóa, index, vòng đời phiên bản, Qdrant payload, nhất quán đa kho | Lược đồ thật, mã nguồn `IngestionService`, `QdrantService`, phân tích giao dịch |
| **4. Cơ sở tri thức** | Làm sao biến PDF thành tri thức có cấu trúc, truy xuất lai và trả lời có trích dẫn, không bịa? | Pipeline 6 tầng, phân đoạn thích ứng, metadata, truy xuất lai, shape gate, citation/refusal | 152 chunk; structure-aware 0% trộn section; 15 test answer gate; benchmark E5 |

### 4. Nguyên tắc trung thực học thuật

- Nội dung kỹ thuật **bám vào mã nguồn thật** của EAKWP: tên lớp, tham số, ngưỡng, luồng xử lý.
- Thành phần **chưa triển khai** (Neo4j, Redis queue, transactional outbox, ACL theo tài liệu, graph extraction) được ghi rõ là **thiết kế/định hướng**, không tuyên bố đã chạy.
- Số liệu benchmark lấy từ `docs/evaluation_embedding_benchmark.md`. Độ trễ có thể dao động giữa các lần chạy do CPU, cache và tải hệ thống; các chương có ghi chú điểm này.
- Hai đường nạp (offline corpus và online upload) được phân biệt rõ: đường offline dùng chunk theo section; đường online hiện dùng chunk theo trang.

### 5. Gợi ý chọn bản in

| Yêu cầu của giảng viên | In các chương |
| :--- | :--- |
| Học sâu + Cơ sở tri thức | Chương 2 + Chương 4 |
| Cơ sở dữ liệu + Cơ sở tri thức | Chương 3 + Chương 4 |
| Cả ba mảng | Chương 2 + Chương 3 + Chương 4 |

Bản Markdown và Word đi kèm đều chứa **cả ba chương**, để có thể in theo bất kỳ tổ hợp nào.

---

<!-- PAGEBREAK -->

## MỤC LỤC

<!-- TOC:START -->
<!-- TOC:END -->
"""

REFERENCES = """
<!-- PAGEBREAK -->

# TÀI LIỆU THAM KHẢO

> Danh mục dưới đây gồm các công trình nền tảng và tài liệu kỹ thuật được tham khảo trong quá trình thực hiện. Các chương trình bày nội dung theo hướng chuyên đề, không trích dẫn theo số thứ tự; danh mục giúp người đọc tra cứu nguồn gốc lý thuyết và công nghệ.

## A. Công trình khoa học

1. Vaswani, A., Shazeer, N., Parmar, N., Uszkoreit, J., Jones, L., Gomez, A. N., Kaiser, Ł., & Polosukhin, I. (2017). *Attention Is All You Need*. Advances in Neural Information Processing Systems (NeurIPS), 30.
2. Devlin, J., Chang, M.-W., Lee, K., & Toutanova, K. (2019). *BERT: Pre-training of Deep Bidirectional Transformers for Language Understanding*. Proceedings of NAACL-HLT, 4171–4186.
3. Reimers, N., & Gurevych, I. (2019). *Sentence-BERT: Sentence Embeddings using Siamese BERT-Networks*. Proceedings of EMNLP-IJCNLP, 3982–3992.
4. Karpukhin, V., Oğuz, B., Min, S., Lewis, P., Wu, L., Edunov, S., Chen, D., & Yih, W.-t. (2020). *Dense Passage Retrieval for Open-Domain Question Answering*. Proceedings of EMNLP, 6769–6781.
5. Lewis, P., Perez, E., Piktus, A., Petroni, F., Karpukhin, V., Goyal, N., Küttler, H., Lewis, M., Yih, W.-t., Rocktäschel, T., Riedel, S., & Kiela, D. (2020). *Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks*. Advances in Neural Information Processing Systems (NeurIPS), 33.
6. Wang, L., Yang, N., Huang, X., Jiao, B., Yang, L., Jiang, D., Majumder, R., & Wei, F. (2022). *Text Embeddings by Weakly-Supervised Contrastive Pre-training*. arXiv:2212.03533. (Mô hình E5)
7. Nogueira, R., & Cho, K. (2019). *Passage Re-ranking with BERT*. arXiv:1901.04085.
8. Robertson, S., & Zaragoza, H. (2009). *The Probabilistic Relevance Framework: BM25 and Beyond*. Foundations and Trends in Information Retrieval, 3(4), 333–389.
9. Malkov, Y. A., & Yashunin, D. A. (2020). *Efficient and Robust Approximate Nearest Neighbor Search Using Hierarchical Navigable Small World Graphs*. IEEE Transactions on Pattern Analysis and Machine Intelligence, 42(4), 824–836.
10. Liu, N. F., Lin, K., Hewitt, J., Paranjape, A., Bevilacqua, M., Petroni, F., & Liang, P. (2023). *Lost in the Middle: How Language Models Use Long Contexts*. arXiv:2307.03172.
11. Gao, Y., Xiong, Y., Gao, X., Jia, K., Pan, J., Bi, Y., Dai, Y., Sun, J., Wang, M., & Wang, H. (2023). *Retrieval-Augmented Generation for Large Language Models: A Survey*. arXiv:2312.10997.
12. Es, S., James, J., Espinosa-Anke, L., & Schockaert, S. (2023). *RAGAS: Automated Evaluation of Retrieval Augmented Generation*. arXiv:2309.15217.
13. Nguyen, D. Q. (2020). *PhoBERT: Pre-trained Language Models for Vietnamese*. Findings of EMNLP 2020.
14. Jurafsky, D., & Martin, J. H. (2023). *Speech and Language Processing* (3rd draft). Stanford University.
15. Manning, C. D., Raghavan, P., & Schütze, H. (2008). *Introduction to Information Retrieval*. Cambridge University Press.

## B. Sách và giáo trình hệ thống

16. Silberschatz, A., Korth, H. F., & Sudarshan, S. (2019). *Database System Concepts* (7th ed.). McGraw-Hill.
17. Kleppmann, M. (2017). *Designing Data-Intensive Applications*. O’Reilly Media.
18. Hibernate ORM Documentation. *Hibernate ORM 6 User Guide*.
19. Spring Boot Documentation. *Spring Boot Reference Documentation*.

## C. Tài liệu kỹ thuật và mã nguồn

20. PostgreSQL Global Development Group. *PostgreSQL 15 Documentation*.
21. Qdrant. *Qdrant Vector Database Documentation*.
22. Neo4j. *Neo4j Graph Database Documentation*.
23. PyMuPDF. *PyMuPDF Documentation*.
24. Tesseract OCR. *Tesseract Documentation*.
25. Hugging Face. *Transformers Documentation*.
26. Hugging Face. *Multilingual-E5-Small Model Card*.
27. Hugging Face. *BKAI Vietnamese Bi-Encoder Model Card*.
28. Sentence-Transformers. *Cross-Encoders Documentation*.
29. FastAPI. *FastAPI Documentation*.
30. React. *React Documentation*.

## D. Dữ liệu và mã nguồn nội bộ

31. EAKWP Repository. *Điều lệ Công ty* (PDF, 39 trang) và corpus 152 chunk dùng cho thực nghiệm.
32. EAKWP Repository. *Báo cáo đánh giá embedding* (`docs/evaluation_embedding_benchmark.md`).
33. EAKWP Repository. *Mã nguồn backend* (`backend/src/main/java/com/tho/enterpriseai`).
34. EAKWP Repository. *Mã nguồn AI service* (`ai-service/app`).

---

# PHỤ LỤC A — BẢN ĐỒ MÃ NGUỒN THEO CHƯƠNG

Bảng dưới đây giúp người đọc đối chiếu nội dung báo cáo với mã nguồn thật của EAKWP.

| Chương | Nội dung | Tệp mã nguồn chính |
| :--- | :--- | :--- |
| 2 | Nhúng câu, chuẩn hóa văn bản | `ai-service/app/embedding_service.py` |
| 2 | Cross-encoder rerank | `ai-service/app/reranker_service.py` |
| 2 | Benchmark ba mô hình | `ai-service/scripts/benchmark_embeddings.py`, `docs/evaluation_embedding_benchmark.md` |
| 3 | Thực thể JPA | `backend/src/main/java/com/tho/enterpriseai/*/entity/*.java` |
| 3 | Nạp tài liệu, vòng đời phiên bản | `backend/src/main/java/com/tho/enterpriseai/document/IngestionService.java` |
| 3 | Upload/xóa tài liệu | `backend/src/main/java/com/tho/enterpriseai/document/DocumentService.java` |
| 3 | Cấu hình Qdrant, payload, point ID | `ai-service/app/qdrant_service.py` |
| 3 | Cấu hình PostgreSQL/Qdrant | `docker-compose.yml`, `backend/src/main/resources/application.yml` |
| 4 | Bóc tách PDF/OCR | `ai-service/app/document_parser.py`, `ai-service/app/font_converter.py` |
| 4 | Phân tích block, heading, header/footer | `ai-service/app/block_analyzer.py` |
| 4 | Cây cấu trúc, section path | `ai-service/app/structure_analyzer.py` |
| 4 | Phân đoạn thích ứng | `ai-service/app/adaptive_chunker.py` |
| 4 | Làm giàu metadata | `ai-service/app/metadata_enricher.py` |
| 4 | Truy xuất lai | `ai-service/app/retriever.py` |
| 4 | Ý định, cửa sổ trả lời, citation | `ai-service/app/rag_service.py` |
| 4 | Kiểm thử answer gate | `ai-service/tests/test_answer_gate.py` |

**Thành phần chỉ ở mức thiết kế/định hướng (chưa triển khai trong mã nguồn hiện tại):**

- Neo4j và đồ thị tri thức (Chương 4, mục 4.12).
- Redis queue/cache (có trong `docker-compose.yml` nhưng backend chưa dùng).
- Transactional outbox và job reconciliation (Chương 3, mục 3.7.5).
- ACL theo tài liệu và lọc `access_level` trong Qdrant (Chương 3, mục 3.9.1).
- Migration Flyway/Liquibase (Chương 3, mục 3.9.4).

---

# PHỤ LỤC B — BỘ CÂU HỎI KIỂM CHỨNG NHANH

Dùng để demo trước hội đồng. Các câu hỏi dưới đây đã được đối chiếu với logic `_answer_shape` và corpus hiện tại.

| # | Câu hỏi | Kỳ vọng | Điểm kiểm chứng |
| :---: | :--- | :--- | :--- |
| 1 | Điều 43 quy định gì? | Trả về nội dung “Trả cổ tức”, giữ tiêu đề điều | `test_focused_excerpt_keeps_article_heading` |
| 2 | Công ty có bao nhiêu thành viên Hội đồng Quản trị? | “Từ 03 đến 11 thành viên” | `test_count_question_accepts_board_size_clause` |
| 3 | Công ty có bao nhiêu cổ đông? | Từ chối / không trả lời | `test_count_question_rejects_shareholder_rights_clause` |
| 4 | Nhiệm kỳ của Hội đồng Quản trị là bao lâu? | “Không quá năm (05) năm” | `test_term_question_accepts_term_clause_not_meeting_window` |
| 5 | Thời gian hoãn họp Đại hội đồng cổ đông tối đa là bao lâu? | “Không quá ba ngày làm việc” | `test_postponement_question_accepts_correct_duration_only` |
| 6 | Công ty có bắt buộc phải kiểm toán không? | Có, theo quy định pháp luật | `test_audit_question_rejects_committee_membership_clause` |
| 7 | Ai có quyền ký hợp đồng thay Công ty? | Tổng Giám đốc | `test_who_signs_contract_accepts_director_clause` |
| 8 | Cổ tức được trả khi nào? | Khi đã hoàn thành nghĩa vụ thuế và tài chính | `test_dividend_question_accepts_payment_condition` |
| 9 | Cách làm bánh pizza hải sản? | Từ chối vì ngoài phạm vi | `test_out_of_scope_question_is_not_answered` |

**Lưu ý khi demo:** nếu câu trả lời từ chối, hãy kiểm tra tài liệu đã ở trạng thái `INGESTED` và `is_current = true`; nếu vẫn từ chối, kiểm tra log rerank để biết cửa sổ có vượt ngưỡng `-6.0` hay không.
"""


def headings(text: str):
    out = []
    for line in text.splitlines():
        m = re.match(r"^(#{1,2})\s+(.*)$", line.strip())
        if m:
            level = len(m.group(1))
            title = m.group(2).strip()
            if title.upper() == "MỤC LỤC":
                continue
            out.append((level, title))
    return out


def toc_markdown(all_text: str) -> str:
    lines = []
    for level, title in headings(all_text):
        if level == 1:
            lines.append(f"- **{title}**")
        else:
            lines.append(f"  - {title}")
    return "\n".join(lines)


def main():
    chapter_texts = []
    for path in CHAPTERS:
        text = path.read_text(encoding="utf-8").strip()
        chapter_texts.append(text)

    body = INTRO + "<!-- PAGEBREAK -->\n\n"
    for i, text in enumerate(chapter_texts):
        body += text + "\n\n"
        if i < len(chapter_texts) - 1:
            body += "<!-- PAGEBREAK -->\n\n"

    body += REFERENCES
    combined = COVER + "\n" + body

    toc = toc_markdown(body)
    combined = combined.replace(
        "<!-- TOC:START -->\n<!-- TOC:END -->",
        "<!-- TOC:START -->\n" + toc + "\n<!-- TOC:END -->",
    )

    OUT.write_text(combined, encoding="utf-8")
    print(f"wrote {OUT} ({len(combined):,} chars, {len(combined.split()):,} words)")


if __name__ == "__main__":
    main()
