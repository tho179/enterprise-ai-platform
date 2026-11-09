# Đánh giá pipeline GraphRAG

Số liệu đo trên hệ thống đang chạy, kho gồm 7 tài liệu và 321 chunk. Cách chạy lại:
`docker compose exec ai-service python scripts/15_run_eval.py --with-llm`.
Kết quả chi tiết từng câu nằm trong `ai-service/data/eval/results/`.

## Kết luận chính

- Kết hợp vector và đồ thị cho truy xuất tốt nhất (MRR 0,713), nhưng phần tăng so với vector thuần nhỏ (0,676): chênh một câu ở Recall@1 trên 18 câu, chưa đủ để khẳng định có ý nghĩa thống kê.
- Đóng góp lớn nhất đến từ cross-encoder và việc giữ dấu tiếng Việt khi nhúng, không phải từ đồ thị.
- Đồ thị dùng riêng kém hơn vector (MRR 0,556), vì quan hệ được trích xuất bằng luật.
- Chế độ không LLM từ chối đúng 5/8 câu ngoài phạm vi. Ba câu còn lại đều gần chủ đề của tài liệu, ví dụ hỏi về "Ban Kiểm soát" khi công ty chỉ có Ủy ban Kiểm toán.

## Bộ đánh giá

`ai-service/data/eval/eval_questions.json` có 26 câu: 18 câu có chunk đúng được gán nhãn thủ công và 8 câu phải từ chối.

Khi đối chiếu với tài liệu, nhiều đáp án của bộ câu hỏi cũ không có căn cứ và đã được sửa. Ba câu hỏi về thông tin tài liệu không có (q003, q004, q009) được chuyển sang nhóm phải từ chối. Nhãn được chốt trước khi chạy pipeline.

| Chỉ số | Cách tính |
| :--- | :--- |
| MRR, Recall@k | Thứ hạng chunk đúng đầu tiên, trước bước lọc câu trả lời |
| Trích dẫn đúng | Có ít nhất một nguồn được trích là chunk đúng |
| Đủ sự kiện | Tỷ lệ sự kiện then chốt có trong câu trả lời, không phân biệt dấu |
| Từ chối đúng | Tỷ lệ câu ngoài phạm vi bị từ chối |
| Từ chối oan | Tỷ lệ câu trong phạm vi bị từ chối |
| Đạt | Câu trong phạm vi: trích đúng và đủ sự kiện. Câu ngoài phạm vi: bị từ chối |

## Kết quả

| Cấu hình | MRR | R@1 | R@3 | Trích đúng | Đủ sự kiện | Từ chối đúng | Từ chối oan | Đạt |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Vector (`flat_rag`) | 0,676 | 61% | 78% | 78% | 83% | 63% | 6% | 73% |
| Đồ thị (`graph_rag`) | 0,556 | 50% | 61% | 67% | 67% | 75% | 28% | 69% |
| **Kết hợp (`hybrid_rag`), cấu hình mặc định** | **0,713** | **67%** | **78%** | **78%** | **83%** | **63%** | **6%** | **73%** |
| Kết hợp, thêm luật theo chủ đề | 0,713 | 67% | 78% | 72% | 81% | 75% | 11% | 73% |
| Kết hợp, có luật, không cross-encoder | 0,530 | 39% | 61% | 72% | 64% | 38% | 6% | 54% |
| Kết hợp + LLM cục bộ `qwen2.5:3b` | 0,713 | 67% | 78% | 67% | 67% | 100% | 33% | 77% |

Độ trễ trung bình trên CPU là khoảng 4 giây không có LLM và 11 giây với LLM cục bộ. Số đo chạy khi máy bận nên chỉ mang tính tham khảo. `GET /api/v1/metrics/latency` trả về p50/p95 từng bước.

## Giữ dấu hay bỏ dấu khi nhúng

So sánh chỉ bằng cosine với `intfloat/multilingual-e5-small`, 18 câu có nhãn:

| Tiền xử lý | MRR | R@1 | R@3 | R@10 |
| :--- | ---: | ---: | ---: | ---: |
| Bỏ dấu (cách cũ) | 0,169 | 6% | 22% | 39% |
| **Giữ dấu (hiện tại)** | **0,806** | **72%** | **89%** | **100%** |

Hệ thống đã chuyển sang giữ dấu khi nhúng. Bỏ dấu chỉ còn dùng để khớp từ khóa, nhằm chịu được lỗi OCR.

## Giới hạn cần nêu khi bảo vệ

- **Mẫu nhỏ:** 18 câu có nhãn và 8 câu từ chối, mỗi câu tương ứng khoảng 4–6 điểm phần trăm.
- **Một số quyết định xem kết quả trên chính bộ này:** việc bỏ dấu, tắt luật chủ đề và áp ngưỡng từ chối được quyết định sau khi xem kết quả trên bộ câu hỏi này. Giá trị ngưỡng -1,5 có sẵn từ trước, không dò lại. Cần một bộ câu hỏi độc lập để có số liệu tổng quát hóa.
- **Dữ liệu OCR:** Chính sách An ninh thông tin và Quy trình đánh giá nhà cung cấp không có tiêu đề nhận dạng được, nên nguồn trích dẫn chỉ ghi số trang.
- **LLM cục bộ không dùng để chấm điểm:** `qwen2.5:3b` cho điểm 0 với nhiều câu trả lời đúng, nên các điểm faithfulness, relevance, correctness của lượt này không được báo cáo.
- **Chưa có số liệu LLM đầy đủ với Gemini:** gói miễn phí giới hạn 20 yêu cầu/ngày cho mỗi model, trong khi một lượt đánh giá cần khoảng 50 yêu cầu. Lượt chạy với `gemini-3.5-flash` hết quota giữa chừng: 8 câu do Gemini trả lời, 12 câu rơi về trích đoạn, chỉ 3 câu được giám khảo chấm. Vì vậy không báo cáo số liệu của lượt này. File `results/hybrid_rag_llm.json` hiện lưu lượt chưa hoàn chỉnh đó; cần chạy lại khi có đủ quota.
- **Trích xuất đồ thị dùng luật:** quan hệ gồm `REFERENCES`, `APPLIES_TO` và đồng xuất hiện, chưa dùng LLM hay GLiNER.
