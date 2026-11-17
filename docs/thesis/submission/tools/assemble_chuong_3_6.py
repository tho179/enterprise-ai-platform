"""Assemble do_an_chuong_3_6.md: renumber Chapter 4, splice in the new KG part and Chapter 5/6.

    python tools/assemble_chuong_3_6.py

Input:  nguon_chuong_3_4_sua.md (Chapter 3 edited + old Chapter 4), chuong_4_kg_moi.md,
        chuong_5_kien_truc.md, chuong_6_ket_qua.md (optional)
Output: do_an_chuong_3_6.md (regenerated each run)
"""
from __future__ import annotations

import re
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
SOURCE = BASE / "nguon_chuong_3_4_sua.md"   # Chapter 3 (edited) + old Chapter 4
TARGET = BASE / "do_an_chuong_3_6.md"

CH4_TITLE = "# CHƯƠNG 4. XÂY DỰNG VÀ QUẢN TRỊ CƠ SỞ TRI THỨC ĐỒ THỊ"
CH4_PROBLEMS = """## 4.1. Vấn đề đặt ra và phạm vi giải quyết

Chương 3 cho hệ thống khả năng biểu diễn văn bản bằng vector. Để hỏi đáp có căn cứ, tri thức trong 35 tệp PDF, 10 trang web và các tài liệu người dùng tải lên còn phải được tổ chức thành một cơ sở tri thức (Knowledge Base, KB) có cấu trúc, truy vết được nguồn và cập nhật được. Khi xây dựng KB, nhóm gặp các vấn đề sau:

| Mã | Vấn đề | Câu hỏi cần trả lời |
| :--- | :--- | :--- |
| T1 | Biến tài liệu thô thành tri thức | PDF quét, OCR lỗi, cấu trúc Chương/Điều/Khoản: làm sao thành các đoạn có ngữ cảnh và trích dẫn được? |
| T2 | Biểu diễn KB | Lưu tri thức dưới dạng nào để vừa tìm theo nghĩa (vector) vừa duyệt theo quan hệ (đồ thị)? Mã truy vấn tổ chức ra sao? |
| T3 | Tích hợp nhiều nguồn (KB1 + KB2) | Trùng lặp, nhiều phiên bản, song ngữ Anh–Việt, nhiễu OCR, tên gọi khác nhau, dữ kiện mâu thuẫn được xử lý thế nào? |
| T4 | Không chắc chắn và mờ | Phép trích xuất nào đáng tin hơn? Hai tên gần giống nhau có phải một thực thể? |
| T5 | Nối KB với RAG | Câu hỏi đi qua KB như thế nào, đoạn mã nào thực hiện bước nào? |
| T6 | Cập nhật KB | Khi tài liệu được thêm, sửa, xóa, hoặc khi bộ trích xuất thay đổi thì làm gì? |
| T7 | Đánh giá KB | Mô hình có MRR và Recall@k; KB được đánh giá bằng gì? |

Chương này giải quyết lần lượt: T1 ở các mục 4.2–4.11 (pipeline thu nhận, cấu trúc, phân đoạn, metadata, vector, truy xuất, cổng trả lời); T2 ở mục 4.13–4.14 (đồ thị Neo4j, mã Cypher tổ chức thành tệp `.cypher`); T3 và T4 ở mục 4.15; T5 ở mục 4.16; T6 ở mục 4.17; T7 ở mục 4.18. Ngoài phạm vi: trích xuất quan hệ bằng mô hình ngôn ngữ lớn và suy luận logic trên đồ thị (ontology, luật suy diễn). Đồ án dùng trích xuất theo luật có độ tin cậy đo được.

---

"""

# "Hình 4.5", "Bảng 4.3", "Công thức 4.2" are figure/table/formula numbers, not sections.
_SECTION_REF = re.compile(r"(?<!Hình )(?<!Bảng )(?<!thức )(?<![\d,.])4\.(\d{1,2})(?=(?:\.\d+)*(?![\d,]))")


def renumber_ch4(text: str) -> str:
    """Shift section numbers 4.1-4.12 of the old chapter to 4.2-4.13."""
    def shift(match: re.Match) -> str:
        return f"4.{int(match.group(1)) + 1}"
    return _SECTION_REF.sub(shift, text)


def main() -> int:
    text = SOURCE.read_text(encoding="utf-8")
    start = text.index("# CHƯƠNG 4.")
    head, ch4 = text[:start], text[start:]
    title_end = ch4.index("\n")
    body = ch4[title_end:]
    body = body[body.index("## 4.1. "):]                     # drop the old "Mục tiêu" quote
    kg_start = body.index("## 4.12. ")
    old_part = renumber_ch4(body[:kg_start]).rstrip()
    if old_part.endswith("---"):
        old_part = old_part[:-3].rstrip()

    kg_new = (BASE / "chuong_4_kg_moi.md").read_text(encoding="utf-8").strip()
    parts = [head.rstrip(), "", CH4_TITLE, "", CH4_PROBLEMS + old_part, "", "---", "", kg_new]
    for name in ("chuong_5_kien_truc.md", "chuong_6_ket_qua.md"):
        path = BASE / name
        if path.exists():
            parts += ["", "---", "", "<!-- PAGEBREAK -->", "", path.read_text(encoding="utf-8").strip()]
    TARGET.write_text("\n".join(parts) + "\n", encoding="utf-8")
    print(f"wrote {TARGET.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
