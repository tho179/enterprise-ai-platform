# Kiểm tra và hoàn thiện Chương 3–4 (bản in 2 chương)

Cập nhật: 08/11/2026. Phạm vi: `in_chuong_3_4.docx/.pdf` (bìa + mục lục + Chương 3 Học sâu + Chương 4 Cơ sở tri thức).

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
| Chương 3: bảng ngang cả trang (MÔ HÌNH, ĐẶC TRƯNG, KIẾN TRÚC, SỐ LAYER, LEARNING RATE, EPOCH…) | Bảng 3.1, mục 3.5.4 (khổ landscape) | Có. Số layer, hidden, tham số lấy từ model card; LR/epoch = 0 vì không fine-tune. Chưa mở lại trang PDF để soát khổ ngang |

## 2. Sai sót đã sửa trong Chương 4

1. **Số chunk dry-run:** bản cũ ghi 70 chunk. Chạy lại ngày 08/11/2026 cho **51 chunk**, 26 entity, 15 trang, 37.896 ký tự, `doc_id` và `content_hash` không đổi. Đã sửa ở 4.12.5, 4.12.11 và `README.md`.
2. **Dung lượng corpus:** "~107 MB" sai đơn vị. Đo thực tế 112,19 MB (≈107 MiB). Đã ghi "112,2 MB (≈107 MiB)".
3. **Chuẩn hóa thực thể:** bản cũ nói `fold()` chuẩn hóa "Điều 7" và "Điều 07". Sai: `fold()` chỉ bỏ dấu, hạ chữ thường, gom khoảng trắng. Đã ghi rõ đây là hạn chế đã biết.
4. **Idempotent:** bản cũ nói `MERGE` "chỉ cập nhật thuộc tính nếu nội dung đổi". Sai: `SET` ghi đè luôn. Đã sửa; số node không tăng khi nạp lại.
5. **Code nối RAG:** hàm `retrieve_with_graph` và `graph_context` trong bản cũ không có trong repo. Đã thay bằng `RAGService.retrieve_hits`, `_fuse_hits` và `graph_search` thật.
6. **Cypher graph:** Cypher trong bản cũ là bản rút gọn. Đã thay bằng `GRAPH_CANDIDATES` thật (có `RELATES_TO*0..1`). Đã thêm cạnh `RELATES_TO` vào bảng cạnh.
7. **Trạng thái graph trong `ask`:** bản cũ ghi "chưa bật". Thực tế: đã nối vào `retrieve_hits`, nhưng tắt mặc định (`GRAPH_ENABLED=false`), và lọc `source_type='upload'` nên KB1/KB2 nạp offline chưa được hỏi đáp đọc. Đã ghi rõ.
8. **Số liệu không đo lại được:** "10/10 URL trả 200" là kết quả ngày 04/11/2026. Hôm nay sandbox không có mạng nên không kiểm lại được. Đã ghi rõ ngày kiểm.
9. **Số liệu không kiểm chứng:** "thay vì 4.976 ký tự nếu giữ menu" không có nguồn. Đã bỏ.

## 3. Việc còn tồn đọng (chưa làm)

- **Hình KB output (`assets/kb_output_one_page.png`):** vẽ bằng PIL với chunk_id `chk-a45f...` lấy từ ví dụ RAG, không lấy từ mẫu dry-run (chunk đầu thật là `chk-f3bc80d1a0dc0312`). Hình đã có chú thích trung thực trong văn bản. Cần sinh lại từ `debug/kb_sample.json` nếu muốn hình khớp 100%.
- **Neo4j thật:** chưa chạy `--init`, `--pdf`, `--links`, `--merge`. Đây là bằng chứng mạnh nhất còn thiếu. Chạy: `docker compose up neo4j`, sau đó `python scripts/10_build_neo4j_kb.py --init` rồi nạp KB1, KB2, merge.
- **Cập nhật source_type:** để KB hợp nhất thật sự phục vụ hỏi đáp, cần đổi điều kiện `source_type="upload"` trong `retrieve_hits` rồi kiểm thử lại answer gate (15 câu).
- **Kiểm tra link:** chạy lại kiểm tra HTTP 200 khi có mạng.
- **Bảng 3.1 (Chương 3):** số tham số, max token và "Nguồn: config.json trên Hugging Face" chưa đối chiếu lại trực tuyến trong lần này.
- **Soát bố cục PDF:** mở lại `in_chuong_3_4.pdf` để kiểm tra trang bảng ngang và mục lục sau khi xuất lại (63 trang).

## 4. File đã thay đổi

- `chuong_4_co_so_tri_thuc.md` (nguồn) → `in_chuong_3_4.md`, `bao_cao_3_chuong.md` (dựng lại bằng `tools/build_print_md.py`, `tools/build_report_md.py`)
- `in_chuong_3_4.docx`, `bao_cao_3_chuong.docx`, `chuong_4_co_so_tri_thuc.docx`, `in_chuong_3_4.pdf` (dựng lại)
- `README.md`
- `KIEM_TRA_CHUONG_3_4.md` (file này)
