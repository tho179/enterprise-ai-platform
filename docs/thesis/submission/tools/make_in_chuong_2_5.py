"""Combine Chapter 2 with Chapters 3-5 of do_an_chuong_3_6.md into in_chuong_2_5.md.

    python tools/assemble_chuong_3_6.py && python tools/make_in_chuong_2_5.py
"""
import re
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent

ch2 = (BASE / "chuong_2_thiet_ke.md").read_text(encoding="utf-8").strip()
rest = (BASE / "do_an_chuong_3_6.md").read_text(encoding="utf-8")
rest = rest[: rest.index("# CHƯƠNG 6.")].rstrip()
rest = re.sub(r"(\n---\s*)?(\n<!-- PAGEBREAK -->\s*)?$", "", rest).rstrip()
(BASE / "in_chuong_2_5.md").write_text(ch2 + "\n\n<!-- PAGEBREAK -->\n\n" + rest + "\n", encoding="utf-8")
print("wrote in_chuong_2_5.md")
