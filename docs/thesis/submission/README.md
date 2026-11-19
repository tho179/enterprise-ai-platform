# Bộ hồ sơ in 2 chương (Chương 3–4) — EAKWP

Cập nhật: 05/11/2026

## 0. Bản nộp lần 2 (17/11/2026): Chương 2–5

| File | Nội dung |
| :--- | :--- |
| `DO_AN_IN_CHUONG_2_5.pdf` / `.docx` | **Bản chính để nộp**: bìa, mục lục, danh mục hình/bảng, Chương 2 (Phân tích và thiết kế microservice), Chương 3 (Học sâu, có mục 3.7.6 mô hình A/AB), Chương 4 (Cơ sở tri thức đồ thị), Chương 5 (Kiến trúc và tác tử). 129 trang, 31 hình, 59 bảng. |
| `chuong_2_thiet_ke.md` | Nguồn Chương 2 |
| `in_chuong_2_5.md` | Nguồn đã ghép của bản in |
| `assets/vp/EAKWP_chuong_2.vpp`, `EAKWP_chuong_5.vpp` | Project Visual Paradigm của 14 hình Chương 2 và 2 hình Chương 5 |
| `tools/vp_gen/` | Bộ sinh XML cho Visual Paradigm (`vpgen.py`, `ch2_diagrams.py`, `ch5_diagrams.py`) |
| `tools/fill_ch4_ch5.py` | Điền số liệu Chương 4–5 từ `ai-service/data/eval/results/*.json` và `assets/agent_traces_20261116.json` |

Hình và công thức:

- Hình VP xuất **SVG** (`ExportDiagramImage -type svg`, lưu nguyên bản ở `tools/vp_gen/vp_svg/`), làm sạch bằng `tools/vp_gen/fix_vp_svg.py`, rồi vẽ lại bằng Edge ở ~3.400 px qua `tools/vp_gen/svg2png.py`. Không dùng `-type pdf`: VP làm mất chữ tiếng Việt có dấu. PNG mặc định của VP chỉ tỉ lệ 1:1 nên bị mờ.
- `fix_vp_svg.py` sửa các lỗi của bản SVG do VP xuất:
  - bỏ `clip-path`, vốn làm đường nối bị đứt khúc và mất một nét của đầu mũi tên;
  - phóng to chữ và căn giữa trong hình;
  - sắp lại use case (`LAYOUTS`) và hình hộp (`BOX_LAYOUTS`: H2.1, H2.13, H5.1) để không đường nối nào cắt qua hình khác, kèm bộ kiểm tra tự động;
  - đặt nhãn «include»/«extend»/thông điệp vào chỗ trống;
  - thay chữ dạng glyph trong ghi chú bằng chữ thật.

  Lệnh chạy:
  ```bash
  python tools/vp_gen/fix_vp_svg.py tools/vp_gen/vp_svg <out_svg>
  python tools/vp_gen/svg2png.py <out_svg> assets/vp
  ```
- Bản build chỉ xoay một hình VP 90° (kèm chú thích) khi xoay giúp hình in to hơn ít nhất 30% (`ROTATE_GAIN`).
- Các hình không có khung ghi chú (note); phần giải thích nằm trong đoạn văn dưới hình. Logo "Powered By Visual Paradigm Community Edition" được giữ theo điều kiện của bản miễn phí.
- **Biểu đồ tuần tự** (H2.9–H2.11, H4.7) theo chuẩn Boundary – Control – Entity:
  - Bộ sinh và nội dung:
    - `tools/vp_gen/seqgen.py` dựng các thành phần sau:
      - Actor;
      - lifeline «boundary»/«control»/«entity»;
      - Message thật nối giữa các activation;
      - thông điệp trả về nét đứt, lời gọi `@Async`;
      - khối `alt`/`loop` có điều kiện canh.
    - `tools/vp_gen/seq_specs.py` chứa nội dung từng hình, lấy theo tên hàm và API trong code.
  - Lệnh chạy: `python tools/vp_gen/seq_specs.py <thư_mục_xml>`. Sau đó, với mỗi tệp: `ImportXML` vào một bản sao project, rồi `ExportDiagramImage -type svg`.
- **Hình Chương 3–4** đều xuất từ VP:
  - `assets/vp/EAKWP_chuong_3_4.vpp` cho các hình H3.2, H4.1–H4.6, H4.8, H4.9.
  - `tools/vp_gen/ch34_diagrams.py` cho các hình bi-encoder, năm lớp tri thức, pipeline xây KB và truy xuất lai.
  - Chỉ hai biểu đồ cột số liệu (`dl_benchmark.png`, `kb_chunking.png`) vẽ ngoài VP.
- 9 đồ thị lớn của Chương 4 (Hình 4.6, 4.8, 4.9, 4.11–4.13, 4.15, 4.17, 4.19): `node tools/neo4j_capture/capture_kb_graphs.cjs <thư mục>` (cần `NEO4J_PASSWORD`, Neo4j đang chạy). Script chạy truy vấn Cypher thật trên Neo4j Browser, phóng khung đồ thị lên 1350 px và xuất bằng nút "Download as PNG" của chính Neo4j; truy vấn của từng hình được in trong chương ngay trước hình.
- Ảnh chụp Neo4j dạng bảng: `SCALE=2.5 node tools/neo4j_capture/capture_kb_v2.cjs <thư mục>`; ảnh code vẽ ở tỉ lệ 3 (`render_code_images.SCALE`).
- Word tự hạ ảnh xuống ~200 dpi khi xuất PDF; `build_do_an_form.py` thay lại ảnh gốc vào PDF (`restore_full_resolution`). Ảnh trong PDF hiện ≥ 241 dpi, trung vị 418 dpi.
- Dòng `> **Công thức N.M.** $...$` được dựng thành phương trình hiển thị của Word (OMML), căn giữa, số (N.M) căn phải; nhiều phương trình ghép bằng `;` hoặc `,` được tách mỗi dòng một phương trình.

Dựng lại:

```bash
python tools/fill_ch4_ch5.py        # chỉ cần khi còn {{...}} trong nguồn
python tools/assemble_chuong_3_6.py
# ghép chuong_2_thiet_ke.md + Chương 3-5 của do_an_chuong_3_6.md thành in_chuong_2_5.md
python tools/build_do_an_form.py --source in_chuong_2_5.md --out DO_AN_IN_CHUONG_2_5 --pdf
```

## 1. Bản nộp theo yêu cầu mới

| File | Nội dung | Dùng để |
| :--- | :--- | :--- |
| `DO_AN_IN_CHUONG_3_4.docx` / `.pdf` | **Bản in nộp theo form Đồ án v1**: 2 trang bìa lấy nguyên từ Đồ án v1 (`assets/cover/`), mục lục, danh mục hình và bảng, Chương 3 (Học sâu), Chương 4 (Cơ sở tri thức); header theo chương, số trang góc phải. PDF 69 trang (nội dung đánh số 1–62). Dựng bằng `tools/build_do_an_form.py --pdf` từ `in_chuong_3_4.md`. | **Bản chính để in và nộp** |
| `in_chuong_3_4.docx` / `.pdf` | Bản in 2 chương kiểu cũ (chưa theo form v1, chưa cập nhật số liệu Neo4j thật). | Đối chiếu |
| `in_chuong_3_4.md` | Markdown nguồn của bản in 2 chương | Chỉnh sửa, tra cứu |
| `bao_cao_3_chuong.docx` / `.pdf` | Bản tham chiếu đủ 3 chương: Chương 2 (Học sâu), Chương 3 (CSDL), Chương 4 (Cơ sở tri thức) + ghi chú biên tập + tài liệu tham khảo + phụ lục. Bản PDF 101 trang. | Đối chiếu; dùng khi cần bản đủ 3 mảng |
| `chuong_2_hoc_sau.docx` / `.pdf` / `.md` | Chương Học sâu, **vẫn đánh số 2** cho bản 3 chương | In riêng / tra cứu |
| `chuong_3_co_so_du_lieu.docx` / `.pdf` / `.md` | Chương Thiết kế cơ sở dữ liệu đa mô hình | In riêng nếu được yêu cầu |
| `chuong_4_co_so_tri_thuc.docx` / `.pdf` / `.md` | Chương Cơ sở tri thức và truy xuất tăng cường | In riêng / tra cứu |
| `original/bao_cao_goc_v5.pdf` | Báo cáo gốc 127 trang của nhóm | Đối chiếu, **không dùng thay bản mới** |
| `assets/` | 12 hình vẽ + `source_inventory.json` + `pdf_inventory.md` | Chèn lại / kiểm tra nguồn |
| `tools/` | Script tạo Markdown, DOCX, PDF, hình, inventory | Tái tạo báo cáo |

**Quy ước số chương:** trong bản in 2 chương, Chương 3 là chương Học sâu (lấy từ `chuong_2_hoc_sau.md` và đổi toàn bộ 2.x → 3.x), Chương 4 giữ nguyên. Chương Cơ sở dữ liệu (`chuong_3_co_so_du_lieu.md`) chỉ nằm trong bản 3 chương, không có trong `in_chuong_3_4`.

Số trang hiện tại: bản in 2 chương **63 trang**; bản 3 chương **101 trang**; Chương 2 **22 trang**; Chương 3 (CSDL) **33 trang**; Chương 4 **42 trang**.

## 2. Nội dung mới cần biết

### Chương 3 — Học sâu
- Giữ cấu trúc lý thuyết → thực nghiệm → ứng dụng của chương Học sâu.
- **Bảng 3.1 in ngang cả trang** (12 cột, khổ A4 landscape): mô hình, đặc trưng, kiến trúc, số layer, hidden/heads, tham số, max token, learning rate, epoch, batch, Recall@1/@3, MRR.
- Code thật: benchmark embedding, embedding service, reranker, tích hợp Qdrant.

### Chương 4 — Cơ sở tri thức
- Mục **4.12.1–4.12.11** bổ sung:
  - Kiến trúc KB1 (PDF nội bộ), KB2 (link công khai) và KB hợp nhất.
  - Danh mục **35 PDF / 395 trang** và **10 URL** thật.
  - Code PDF → Neo4j, link → Neo4j, gộp KB1 + KB2 → KB, cập nhật theo hash/phiên bản.
  - Dạng KB output một trang, giải thích từng thành phần.
  - RAG nối KB với ví dụ IN/OUT và Cypher graph retrieval.
- Mục **4.13** kết luận chương, nêu rõ phần đã chạy và phần còn là prototype.
- Hình mới: `kb_graph_sources.png`, `kb_output_one_page.png`, `rag_kb_in_out.png`.

### Mã nguồn đồ thị tri thức
- `ai-service/app/knowledge_graph/`: `ids.py`, `extract.py`, `schema.py`, `store.py`, `pipeline.py`.
- CLI: `ai-service/scripts/10_build_neo4j_kb.py` với `--init`, `--pdf`, `--links`, `--merge`, `--export`, `--update`, `--dry-run`.
- Dữ liệu link: `ai-service/data/kb_sources/links.json`.
- Test: `ai-service/tests/test_knowledge_graph.py` — **6 test pass** (`python -m unittest tests.test_knowledge_graph -v`).
- Đã thêm service `neo4j` vào `docker-compose.yml` và driver `neo4j` vào `requirements.txt`.

**Trạng thái trung thực:** chưa chạy Neo4j thật, chưa nạp đủ 35 PDF + 10 link vào Neo4j, chưa chạy schema/constraints trên server. Các phần đã kiểm thử là pure functions (ID, parser, chunk, entity, plan update, RRF) và dry-run 1 PDF. Trong bản ghi thô `debug/kb_sample.json`, JSON chỉ có `doc`, `chunks`, `entities`; `relations` do `store.upsert_record` sinh từ `schema.py`, còn `stats` do `store.stats()` tính sau khi ghi — không phải trường có sẵn trong file JSON.

## 3. Trước khi in

- [ ] Mở `in_chuong_3_4.docx` bằng Microsoft Word.
- [ ] Kiểm tra bìa: Học viện Công nghệ Bưu chính Viễn thông, Khoa Công nghệ Thông tin 1, PGS.TS Trần Đình Quế, Nguyễn Quý Thọ – B22DCCN836, Nguyễn Xuân Đạt – B22DCCN200, Hoàng Lê Đức – B22DCCN224, Niên khóa 2022–2027.
- [ ] Cập nhật mục lục: `Ctrl+A` → `F9` → chọn **Update entire table**. Bản PDF đã cập nhật sẵn.
- [ ] Kiểm tra trang **12** (bảng ngang 3.1) in đúng khổ landscape, không bị cắt cột.
- [ ] Kiểm tra 3 hình mới của Chương 4 và bảng giải thích KB output.
- [ ] In A4, **100% scale** (không chọn “Fit to page”); lề trái 3 cm, phải 2 cm, trên/dưới 2,5 cm. Trang landscape đã đặt khổ 29,7 × 21 cm.
- [ ] Bản in 2 chương **không có** tài liệu tham khảo và phụ lục; nếu giảng viên yêu cầu, dùng `bao_cao_3_chuong.docx` hoặc in thêm phần đó.

## 4. Lưu ý nội dung

- Báo cáo bám mã nguồn thật của EAKWP: tên lớp, tham số, ngưỡng, luồng xử lý.
- Các thành phần **chưa triển khai** (Neo4j thật, Redis queue, transactional outbox, ACL theo tài liệu, graph extraction quy mô lớn) được ghi rõ là **prototype/định hướng**, không tuyên bố đã chạy.
- CSDL thật có **5 bảng**: `users`, `documents`, `document_versions`, `document_chunks`, `ingestion_tasks`; không có khóa ngoại vật lý; dùng `ddl-auto=update`.
- Số liệu benchmark lấy từ `docs/evaluation_embedding_benchmark.md`; độ trễ có thể dao động giữa các lần chạy.
- Hai đường nạp dữ liệu được phân biệt: offline corpus dùng chunk theo section; upload online hiện dùng chunk theo trang.
- Kết quả dry-run PDF mẫu: `Quy_che_hoat_dong_HDQT.pdf`, 15 trang, 37.896 ký tự, 51 chunk, 26 entity (đo lại 08/11/2026), `doc_id = doc-61fde4771461df6e`.
- KB2: 10 URL, 24.281 ký tự, 31 chunk; kiểm tra ngày 04/11/2026 tất cả trả HTTP 200.

## 5. Tái tạo báo cáo

```bash
python tools/make_diagrams.py
python tools/make_kb_graph_diagrams.py
python tools/build_print_md.py      # sinh in_chuong_3_4.md
python tools/build_report_md.py     # sinh bao_cao_3_chuong.md
python tools/build_docx.py --mode print
python tools/build_docx.py --mode all
python tools/export_pdf.py in_chuong_3_4.docx
python tools/export_pdf.py bao_cao_3_chuong.docx
```

- `build_docx.py --mode all` tạo bản 3 chương, bản in 2 chương và 3 file chương riêng.
- `export_pdf.py` cần Microsoft Word (COM); script tự cập nhật mục lục, nén dòng mục lục và xuất PDF.
- Sau khi sửa `chuong_2_hoc_sau.md` hoặc `chuong_4_co_so_tri_thuc.md`, phải chạy lại **cả** `build_print_md.py` và `build_report_md.py` trước khi build DOCX.
