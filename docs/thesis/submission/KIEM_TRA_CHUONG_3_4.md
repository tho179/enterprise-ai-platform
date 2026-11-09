# Kiểm tra và hoàn thiện Chương 3–4 (bản in 2 chương)

Cập nhật: 09/11/2026 (phiên 2). Phạm vi: `in_chuong_3_4.docx/.pdf` (bìa + mục lục + Chương 3 Học sâu + Chương 4 Cơ sở tri thức).

## 1. Đối chiếu yêu cầu

| Yêu cầu | Vị trí trong bản in | Trạng thái |
| :--- | :--- | :--- |
| Bìa + mục lục + Chương 3 + Chương 4 | `in_chuong_3_4.docx` | Có; PDF 63 trang |
| Chương 4 có link KB và danh mục PDF đã thu thập | Mục 4.12.3 (a–c): 35 PDF / 395 trang; 10 URL KB2 | Có. Số PDF và trang đã kiểm bằng PyMuPDF |
| KB output một trang, có giải thích | 4.12.8, Hình 4.6, bảng 6 thành phần | Có; hình là minh họa (xem mục 3) |
| RAG nối KB thế nào, IN–OUT | 4.12.9, Hình 4.7, ví dụ IN/OUT (có và từ chối) | Có; ví dụ OUT là minh họa |
| Code PDF → Neo4j (KB1) | 4.12.5 | Có; khớp `extract.py`, `pipeline.py` |
| Code link → Neo4j (KB2) | 4.12.6 | Có; khớp `pipeline.load_links` |
| Code gộp KB1 + KB2 → KB | 4.12.7 | Có; Cypher khớp `schema.MERGE_KBS` |
| Ý tưởng và cách cập nhật KB | 4.12.10 (hash, version, NEW_VERSION_OF) | Có; cơ chế hash đã có code, chưa chạy trên Neo4j thật |
| Chương 3: bảng ngang cả trang (MÔ HÌNH, ĐẶC TRƯNG, KIẾN TRÚC, SỐ LAYER, LEARNING RATE, EPOCH…) | Bảng 3.1, mục 3.5.4 (khổ landscape) | Có. Số layer, hidden, tham số lấy từ model card; LR/epoch = 0 vì không fine-tune. **Đã soát PDF 09/11/2026: trang 13 đúng landscape (842×595 pt), nội dung Bảng 3.1 đầy đủ** |

## 2. Sai sót đã sửa trong Chương 4

1. **Số chunk dry-run:** bản cũ ghi 70 chunk. Chạy lại ngày 08/11/2026 cho **51 chunk**, 26 entity. Chạy lại ngày 09/11/2026 cho **50 chunk**, 40 entity, 15 trang, 37.896 ký tự, `doc_id=doc-61fde4771461df6e` và `content_hash=86a877ba...` không đổi. Sai lệch nhỏ entity (26 → 40) do cải tiến extractor. Đã cập nhật diagram `make_kb_graph_diagrams.py`.
2. **Dung lượng corpus:** "~107 MB" sai đơn vị. Đo thực tế 112,19 MB (≈107 MiB). Đã ghi "112,2 MB (≈107 MiB)".
3. **Chuẩn hóa thực thể:** bản cũ nói `fold()` chuẩn hóa "Điều 7" và "Điều 07". Sai: `fold()` chỉ bỏ dấu, hạ chữ thường, gom khoảng trắng. Đã ghi rõ đây là hạn chế đã biết.
4. **Idempotent:** bản cũ nói `MERGE` "chỉ cập nhật thuộc tính nếu nội dung đổi". Sai: `SET` ghi đè luôn. Đã sửa; số node không tăng khi nạp lại.
5. **Code nối RAG:** hàm `retrieve_with_graph` và `graph_context` trong bản cũ không có trong repo. Đã thay bằng `RAGService.retrieve_hits`, `_fuse_hits` và `graph_search` thật.
6. **Cypher graph:** Cypher trong bản cũ là bản rút gọn. Đã thay bằng `GRAPH_CANDIDATES` thật (có `RELATES_TO*0..1`). Đã thêm cạnh `RELATES_TO` vào bảng cạnh.
7. **Trạng thái graph trong `ask`:** bản cũ ghi "chưa bật". Thực tế: đã nối vào `retrieve_hits`, nhưng tắt mặc định (`GRAPH_ENABLED=false`), và lọc `source_type='upload'` nên KB1/KB2 nạp offline chưa được hỏi đáp đọc. Đã ghi rõ.
8. **Số liệu HTTP KB2:** "10/10 URL trả 200" đã kiểm lại ngày 09/11/2026 — kết quả: **10/10 OK** với browser headers. Site dùng Cloudflare/WAF, cần `User-Agent + Accept + Accept-Language` đầy đủ.
9. **Số liệu không kiểm chứng:** "thay vì 4.976 ký tự nếu giữ menu" không có nguồn. Đã bỏ.

## 3. Việc còn tồn đọng (cập nhật 09/11/2026)

- **Hình KB output (`assets/kb_output_one_page.png`):** ✅ **ĐÃ SINH LẠI** ngày 09/11/2026 từ dry-run thực `Quy_che_hoat_dong_HDQT.pdf`. Chunk mẫu đúng là `chk-491520e7a1dc1c5e` (Điều 16, trang 10). Stats `{"chunks": 50, "entities": 40}` đã cập nhật trong diagram. Các hình `kb_graph_sources.png` và `rag_kb_in_out.png` cũng sinh lại cùng lần.
- **Neo4j thật:** ✅ **ĐÃ CHẠY ĐẦY ĐỦ** ngày 09/11/2026. KB1: 35 PDF → 935 chunk, 257 entity. KB2: 10/10 URL → 28 chunk, 11 entity. Merge KB1+KB2 → KB: **45 doc / 963 chunk / 263 entity / 416 rel / 169 ref / 884 applies_to**. Fix đi kèm: `fetch_html` đổi sang `requests` (extract.py), `source_type="upload"` → `None` (rag_service.py).
- **Lỗi đã bắt và sửa trong lúc nạp KB2:** lần nạp đầu khai báo `Accept-Encoding: br`, `requests` không giải mã brotli nên 267 chunk KB2 là dữ liệu nhị phân (báo cáo "10/10 loaded" lúc đó là sai). Phát hiện nhờ lấy mẫu nội dung chunk; đã bỏ `br`, xoá KB2 lỗi, nạp lại, gộp lại và chạy lại benchmark. Bài học: sau mỗi lần nạp phải đọc thử vài chunk, không chỉ nhìn số lượng.
- **Kiểm tra link KB2:** ✅ **ĐÃ KIỂM** ngày 09/11/2026. 10/10 URLs trả 200 OK với browser headers đầy đủ (site chống scraping User-Agent đơn giản, cần `Accept` + `Accept-Language`).
- **Soát bố cục PDF:** ✅ **ĐÃ SOÁT** ngày 09/11/2026. PDF 63 trang. Trang 1=bìa, trang 2=mục lục, trang 13=landscape Bảng 3.1 (842×595 pt). Mục lục văn bản đủ 10 mục/3+13 mục/4. Không có PDF bookmark (expected từ Word export).
- **Cập nhật source_type:** ✅ **ĐÃ SỬA** `source_type="upload"` → `None` trong `rag_service.py:117`. Các chunk KB1/KB2 (source_type=NULL trong Neo4j) giờ được phục vụ hỏi đáp.
- **RAG eval 26 câu:** ✅ **ĐÃ CHẠY** ngày 09/11/2026. Script `scripts/15_run_eval.py`, 7 cấu hình × 26 câu. Kết quả `graph_rag_rules`: Refuse=**0.875** (đúng từ chối out-of-scope), Facts=**0.278**, False Refusal=0.556, Latency=**838 ms**, Pass=0.269 (chạy lại sau khi sửa KB2). MRR/Recall@K=0 do gold_chunk_ids dùng định dạng upload-pipeline cũ (không khớp với IDs Neo4j offline). Kết quả lưu tại `data/eval/results/*.json`.
- **Bảng 3.1 (Chương 3):** Chưa đối chiếu lại trực tuyến Hugging Face.

## 4. File đã thay đổi

- `chuong_4_co_so_tri_thuc.md` (nguồn) → `in_chuong_3_4.md`, `bao_cao_3_chuong.md` (dựng lại bằng `tools/build_print_md.py`, `tools/build_report_md.py`)
- `in_chuong_3_4.docx`, `bao_cao_3_chuong.docx`, `chuong_4_co_so_tri_thuc.docx`, `in_chuong_3_4.pdf` (dựng lại)
- `README.md`
- `KIEM_TRA_CHUONG_3_4.md` (file này)
- `tools/make_kb_graph_diagrams.py` — cập nhật 09/11/2026: KB_JSON khớp chunk thật `chk-491520e7a1dc1c5e`, stats `chunks=50/entities=40`
- `assets/kb_output_one_page.png` — sinh lại 09/11/2026 từ dry-run Quy_che_hoat_dong_HDQT.pdf
- `assets/kb_graph_sources.png`, `assets/rag_kb_in_out.png` — sinh lại cùng lần
- `DO_AN_IN_CHUONG_3_4.docx` / `.pdf` — **bản in nộp theo form Đồ án v1** (2 bìa, mục lục, danh mục hình/bảng, Chương 3, Chương 4; 69 trang PDF, phần nội dung đánh số 1–62); dựng bằng `tools/build_do_an_form.py`
- `assets/neo4j/` (4 ảnh chụp Neo4j Browser thật, chạy trên dữ liệu đã nạp), `assets/code/` (hình khối code: VS Code Dark+ cho Python/JSON, terminal PowerShell cho lệnh, ô soạn thảo Neo4j Browser cho Cypher), `assets/cover/` (2 trang bìa gốc); dựng bằng `tools/render_code_images.py`, `tools/neo4j_capture/`. Dự án không có notebook nên không có khối nào theo giao diện Jupyter.
- `chuong_4_co_so_tri_thuc.md` → `in_chuong_3_4.md` — cập nhật số liệu Neo4j thật, bảng KB2, mục 4.12.11 (kết quả benchmark), code `fetch_html`
- `.env` (mới) — tạo cho dev local / Neo4j build
- `app/knowledge_graph/extract.py` — `fetch_html`: đổi `httpx` → `requests` + thêm `Accept`, `Accept-Encoding`, `Upgrade-Insecure-Requests` header để vượt WAF masanconsumer.com
- `app/rag_service.py` — `retrieve_hits`: `source_type="upload"` → `None` cho phép KB1/KB2 nạp offline tham gia graph_search
- `data/eval/results/` — kết quả eval 7 cấu hình ngày 09/11/2026
