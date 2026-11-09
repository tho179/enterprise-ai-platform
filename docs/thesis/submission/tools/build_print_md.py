"""Build the two-chapter print source: cover + TOC + Chapter 3 + Chapter 4.

The Deep Learning chapter keeps the same content as `chuong_2_hoc_sau.md`
but is renumbered from 2.x to 3.x so the printed booklet starts at Chapter 3,
matching the instructor's numbering. Chapter 4 keeps its own number.
"""
from __future__ import annotations

import re
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
DEEP_LEARNING = BASE / "chuong_2_hoc_sau.md"
KNOWLEDGE = BASE / "chuong_4_co_so_tri_thuc.md"
OUT = BASE / "in_chuong_3_4.md"


def renumber_deep_learning(text: str) -> str:
    text = text.replace("# CHƯƠNG 2.", "# CHƯƠNG 3.", 1)
    text = re.sub(r"(?<![\d.])2\.(\d+)(?![\d])", r"3.\1", text)
    return text


def adapt_knowledge_for_print(text: str) -> str:
    old = (
        "Cùng với chương Học sâu và chương Cơ sở dữ liệu, chương này hoàn thành "
        "bộ ba nền tảng của EAKWP: **biểu diễn tri thức bằng vector**, "
        "**lưu trữ và đồng bộ dữ liệu**, và **xây dựng–khai thác cơ sở tri thức có trích dẫn**."
    )
    new = (
        "Cùng với chương Học sâu, chương này hoàn thành hai nền tảng của EAKWP: "
        "**biểu diễn tri thức bằng vector** và "
        "**xây dựng–khai thác cơ sở tri thức có trích dẫn**."
    )
    if old not in text:
        raise SystemExit("Không tìm thấy câu kết cần đổi cho bản in 2 chương.")
    return text.replace(old, new, 1)


def main() -> None:
    deep_learning = renumber_deep_learning(DEEP_LEARNING.read_text(encoding="utf-8").strip())
    knowledge = adapt_knowledge_for_print(KNOWLEDGE.read_text(encoding="utf-8").strip())

    if "# CHƯƠNG 3." not in deep_learning:
        raise SystemExit("Chương Học sâu chưa được đổi sang số 3.")
    if re.search(r"(?<![\d.])2\.\d+", deep_learning):
        raise SystemExit("Còn số mục 2.x sau khi đổi số.")

    body = deep_learning + "\n\n<!-- PAGEBREAK -->\n\n" + knowledge + "\n"
    OUT.write_text(body, encoding="utf-8")
    print(f"wrote {OUT} ({len(body):,} chars, {len(body.split()):,} words)")


if __name__ == "__main__":
    main()
