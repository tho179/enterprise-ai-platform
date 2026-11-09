"""Build the print edition (cover + TOC + Chapter 3 + Chapter 4) in the layout of `Đồ án v1.pdf`.

The two cover pages are the first two pages of the group's original report, unchanged.
Layout copied from it: TOC / list of figures / list of tables without page numbers,
italic chapter header with a rule, page number bottom-right restarting at 1 on the
first chapter, black text, captions in italics below figures and tables.

    python tools/build_do_an_form.py --pdf
"""
from __future__ import annotations

import argparse
import re
import shutil
import sys
from pathlib import Path

from docx.enum.section import WD_SECTION
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_docx as bd  # noqa: E402
import render_code_images as rci  # noqa: E402

BASE = Path(__file__).resolve().parent.parent
SOURCE_MD = BASE / "in_chuong_3_4.md"
OUT_DOCX = BASE / "DO_AN_IN_CHUONG_3_4.docx"
OUT_MD = BASE / "DO_AN_IN_CHUONG_3_4.md"
COVER_DIR = BASE / "assets" / "cover"
CODE_DIR = BASE / "assets" / "code"

BLACK = RGBColor(0, 0, 0)
CAPTION_RE = re.compile(r"^\*{1,2}(Hình|Bảng) \d+\.\d+\.")

# Black text only; inline code without grey shading.
bd.COLOR_TEXT = bd.COLOR_MUTED = bd.COLOR_ACCENT = BLACK
_orig_borders = bd.set_table_borders
bd.set_table_borders = lambda table, color="A6A6A6", size=4: _orig_borders(table, "000000", 4)
bd.set_cell_shading = lambda cell, fill: None
bd.shade_run = lambda *a, **k: None
_RGB = bd.RGBColor
bd.RGBColor = lambda r, g, b: BLACK if (r, g, b) == (0x8B, 0x1A, 0x1A) else _RGB(r, g, b)
_orig_inline = bd.add_inline


def _inline_no_zwsp(*a, **k):
    if len(a) >= 9:
        a = a[:8] + (False,) + a[9:]
    else:
        k["code_break"] = False
    return _orig_inline(*a, **k)


bd.add_inline = _inline_no_zwsp
_orig_widths = bd.compute_table_widths


def _widths(rows, n_cols, total_cm=16.0, min_cm=1.8):
    if n_cols == 12 and rows and rows[0][0].strip() == "Mô hình":
        return [2.9, 4.4, 2.8, 1.4, 1.8, 1.7, 1.5, 1.9, 1.5, 2.2, 2.0, 1.6]
    return _orig_widths(rows, n_cols, total_cm, min_cm)


bd.compute_table_widths = _widths


# ---------------------------------------------------------------------------
# Text preparation
# ---------------------------------------------------------------------------

def move_table_captions_below(text: str) -> str:
    pattern = re.compile(r"(\*\*Bảng \d+\.\d+\.[^\n]*\*\*)\n\n((?:\|[^\n]*\n)+)")
    return pattern.sub(lambda m: f"{m.group(2)}\n{m.group(1)}\n", text)


def _strip_marks(line: str) -> str:
    """Drop bold/italic markers outside inline code and formulas."""
    parts = re.split(r"(`[^`]*`|\$[^$]*\$)", line)
    for i in range(0, len(parts), 2):
        s = re.sub(r"\*\*(.+?)\*\*", r"\1", parts[i])
        s = re.sub(r"(?<![*\w])\*(?!\s)([^*\n]+?)(?<!\s)\*(?![*\w])", r"\1", s)
        parts[i] = s
    return "".join(parts)


def clean_body(text: str) -> str:
    out, in_code = [], False
    for line in text.splitlines():
        if line.startswith("```"):
            in_code = not in_code
            out.append(line)
            continue
        if in_code:
            out.append(line)
            continue
        s = line.strip()
        if s.startswith("*Nguồn: quét trực tiếp"):
            continue
        if s.startswith("*Kiểm tra ngày"):
            out.append("Cả 10 URL đều trả HTTP 200 và đã được nạp vào Neo4j.")
            continue
        if s.startswith("*Nguồn:") and "Learning rate" in s:
            s = re.sub(r"^\*Nguồn:.*?Điều lệ Công ty\.\s*", "", s).rstrip("*")
            out.append(_strip_marks(s))
            continue
        line = line.replace(
            "Để tránh tuyên bố quá mức, bảng dưới tách rõ **đã có code**, **đã kiểm thử** và **đã chạy trong môi trường thật**",
            "Bảng dưới tổng hợp trạng thái từng hạng mục: đã có code, đã kiểm thử, đã chạy thật",
        )
        if CAPTION_RE.match(s):
            out.append(line)  # captions keep their markers; the builder renders them in italics
            continue
        out.append(_strip_marks(line))
    return "\n".join(out) + "\n"


def collect_captions(text: str):
    figures, tables = [], []
    for line in text.splitlines():
        s = line.strip()
        if CAPTION_RE.match(s):
            plain = s.strip("*").strip().rstrip(".")
            (figures if plain.startswith("Hình") else tables).append(plain)
    return figures, tables


# ---------------------------------------------------------------------------
# Document
# ---------------------------------------------------------------------------

class FormDocx(bd.ThesisDocx):
    def __init__(self, md_path: Path, figures, tables):
        self.figures, self.tables = figures, tables
        self._chapters_started = 0
        super().__init__(md_path, "Đồ án tốt nghiệp", header_text="")

    def _setup_styles(self):
        super()._setup_styles()
        st = self.doc.styles
        for name, size, bold, italic, align in [
            ("Heading 1", 14, True, False, WD_ALIGN_PARAGRAPH.CENTER),
            ("Heading 2", 13, True, False, WD_ALIGN_PARAGRAPH.LEFT),
            ("Heading 3", 13, True, True, WD_ALIGN_PARAGRAPH.LEFT),
            ("Heading 4", 13, False, True, WD_ALIGN_PARAGRAPH.LEFT),
        ]:
            bd.set_style_font(st[name], bd.FONT_BODY, size, bold, italic, BLACK)
            st[name].paragraph_format.alignment = align
        st["Heading 1"].paragraph_format.space_after = Pt(14)
        bd.set_style_font(st["Caption VN"], bd.FONT_BODY, 12, False, True, BLACK)
        bd.set_style_font(st["Quote Box"], bd.FONT_BODY, 12.5, False, False, BLACK)

    def _p(self, text="", size=14, bold=False, align=WD_ALIGN_PARAGRAPH.CENTER, after=0):
        p = self.doc.add_paragraph()
        p.alignment = align
        pf = p.paragraph_format
        pf.first_line_indent = Cm(0)
        pf.space_before, pf.space_after, pf.line_spacing = Pt(0), Pt(after), 1.15
        if text:
            bd.set_run_font(p.add_run(text), bd.FONT_BODY, size, bold, False, BLACK)
        return p

    def _full_page_image(self, png: Path):
        s = self.doc.sections[-1]
        s.top_margin = s.bottom_margin = Cm(0.05)
        s.left_margin = s.right_margin = Cm(0.1)
        s.header_distance = s.footer_distance = Cm(0)
        p = self.doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        pf = p.paragraph_format
        pf.first_line_indent = Cm(0)
        pf.space_before = pf.space_after = Pt(0)
        pf.line_spacing = 1.0
        p.add_run().add_picture(str(png), width=Cm(20.6))

    def _new_section(self):
        section = self.doc.add_section(WD_SECTION.NEW_PAGE)
        self._setup_page(section)
        bd.continue_page_numbering(section)
        return section

    def _add_cover(self):
        self._full_page_image(COVER_DIR / "bia_1.png")

    def _add_body_section(self):
        self._pending_break = False
        self._new_section()
        self._full_page_image(COVER_DIR / "bia_2.png")

        self._new_section()
        self._p("MỤC LỤC", 14, True, after=12)
        toc = self._p("", align=WD_ALIGN_PARAGRAPH.LEFT)
        toc.paragraph_format.line_spacing = 1.0
        bd.add_field(toc, r'TOC \o "1-3" \h \z \u', "Cập nhật mục lục: chuột phải → Update Field.")
        self._list_page("DANH MỤC HÌNH VẼ", self.figures)
        self._list_page("DANH MỤC BẢNG BIỂU", self.tables)

    def _list_page(self, title, items):
        brk = self.doc.add_paragraph()
        brk.add_run().add_break(WD_BREAK.PAGE)
        brk.paragraph_format.space_after = Pt(0)
        self._p(title, 14, True, after=12)
        for item in items:
            self._p(item, 13, align=WD_ALIGN_PARAGRAPH.LEFT, after=8)

    def _begin_chapter(self, text: str):
        m = re.match(r"CHƯƠNG\s+(\d+):\s*(.*)", text)
        label = f"CHƯƠNG {m.group(1)}: {m.group(2).split(':')[0].strip()}" if m else text
        section = self._new_section()
        section.header.is_linked_to_previous = False
        section.footer.is_linked_to_previous = False
        hp = section.header.paragraphs[0]
        hp.alignment = WD_ALIGN_PARAGRAPH.LEFT
        hp.paragraph_format.first_line_indent = Cm(0)
        hp.paragraph_format.space_after = Pt(2)
        bd.set_run_font(hp.add_run(label), bd.FONT_BODY, 10.5, False, True, BLACK)
        bd.border_paragraph(hp, "bottom", "000000", 6, 1)
        fp = section.footer.paragraphs[0]
        fp.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        fp.paragraph_format.first_line_indent = Cm(0)
        bd.set_run_font(bd.add_field(fp, "PAGE", "1"), bd.FONT_BODY, 12, False, False, BLACK)
        if self._chapters_started == 0:
            bd.set_page_number_start(section, 1)
        self._chapters_started += 1
        self._pending_break = False

    def _heading(self, level, text):
        if level == 1:
            text = re.sub(r"^(CHƯƠNG\s+\d+)\.\s*", r"\1: ", text)
            self._begin_chapter(text)
        super()._heading(level, text)

    def _flush(self, buffer):
        if not buffer:
            return
        text = " ".join(buffer).strip()
        buffer.clear()
        if not text:
            return
        if CAPTION_RE.match(text):
            p = self._new_para("Caption VN")
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            bd.add_inline(p, text.strip("*").strip(), italic=True, size=12, color=BLACK)
            return
        bd.add_inline(self._new_para("Normal"), text)

    def _image(self, alt, rel_path):
        if alt.startswith("code"):
            width_px = int(alt.split("|")[1]) if "|" in alt else 700
            p = self._new_para()
            p.alignment = WD_ALIGN_PARAGRAPH.LEFT
            p.paragraph_format.first_line_indent = Cm(0)
            p.paragraph_format.space_before = Pt(4)
            p.paragraph_format.space_after = Pt(8)
            p.paragraph_format.line_spacing = 1.0
            p.add_run().add_picture(str((self.base_dir / rel_path).resolve()),
                                    width=Cm(min(width_px * rci.PX_TO_CM, 15.8)))
            return
        super()._image(alt, rel_path)
        self.doc.paragraphs[-1].paragraph_format.keep_with_next = True

    def _table(self, rows, aligns):
        super()._table(rows, aligns)
        table = self.doc.tables[-1]
        for cell in table.rows[0].cells:
            cell.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
        if self._landscape:
            for row in table.rows:
                for cell in row.cells:
                    for p in cell.paragraphs:
                        p.paragraph_format.space_before = Pt(5)
                        p.paragraph_format.space_after = Pt(5)
                        for run in p.runs:
                            run.font.size = Pt(9) if run.font.name == bd.FONT_CODE else Pt(10.5)

    def _quote(self, line):
        p = self._new_para("Quote Box")
        p.paragraph_format.left_indent = Cm(0.6)
        bd.border_paragraph(p, "left", "7F7F7F", 18, 8)
        bd.add_inline(p, line)

    def _rule(self):
        return None


# ---------------------------------------------------------------------------
# PDF export
# ---------------------------------------------------------------------------

def export_pdf(docx_path: Path):
    import fitz
    import win32com.client
    from docx import Document

    pdf = docx_path.with_suffix(".pdf")
    tmp = docx_path.with_name(docx_path.stem + "_export.docx")
    shutil.copy2(docx_path, tmp)
    d = Document(str(tmp))
    for el in d.settings.element.findall(qn("w:updateFields")):
        d.settings.element.remove(el)
    d.save(str(tmp))
    word = doc = None
    try:
        word = win32com.client.DispatchEx("Word.Application")
        word.Visible = False
        word.DisplayAlerts = 0
        doc = word.Documents.Open(str(tmp), ReadOnly=False, AddToRecentFiles=False)

        def update_toc():
            for field in doc.Fields:
                if field.Type == 13:
                    field.Update()

        update_toc()
        # (bold, left cm, hanging cm, right cm, space before pt, space after pt)
        fmt = {
            "toc 1": (True, 0.0, 0.0, 2.5, 10, 4),
            "toc 2": (True, 0.8, 0.0, 0.0, 0, 2),
            "toc 3": (False, 1.6, 0.0, 0.0, 0, 1),
        }
        for i in range(1, doc.Styles.Count + 1):
            style = doc.Styles.Item(i)
            try:
                name = style.NameLocal.lower()
            except Exception:
                continue
            key = "toc " + name[-1] if name.startswith(("toc ", "mục lục ")) else None
            if key in fmt:
                bold, indent, hang, right, before, after = fmt[key]
                style.Font.Name = "Times New Roman"
                style.Font.Size = 12
                style.Font.Bold = bold
                style.Font.Color = 0
                style.ParagraphFormat.Alignment = 0
                style.ParagraphFormat.LeftIndent = word.CentimetersToPoints(indent)
                style.ParagraphFormat.FirstLineIndent = -word.CentimetersToPoints(hang)
                style.ParagraphFormat.RightIndent = word.CentimetersToPoints(right)
                style.ParagraphFormat.SpaceBefore = before
                style.ParagraphFormat.SpaceAfter = after
                style.ParagraphFormat.LineSpacingRule = 0
        doc.Repaginate()
        update_toc()
        doc.Repaginate()
        doc.Save()
        doc.ExportAsFixedFormat(str(pdf), 17)
        doc.Close(SaveChanges=0)
        doc = None
    finally:
        for closer in (lambda: doc.Close(SaveChanges=0) if doc is not None else None,
                       lambda: word.Quit() if word is not None else None):
            try:
                closer()
            except Exception:
                pass
    shutil.copy2(tmp, docx_path)
    tmp.unlink()

    # Put the original (vector) cover pages in front of the exported PDF.
    out = fitz.open(str(pdf))
    out.delete_pages(0, 1)
    cover = fitz.open(str(COVER_DIR / "bia_2_trang.pdf"))
    out.insert_pdf(cover, start_at=0)
    tmp_pdf = pdf.with_name(pdf.stem + "_tmp.pdf")
    out.save(str(tmp_pdf), garbage=3, deflate=True)
    out.close()
    shutil.move(str(tmp_pdf), str(pdf))
    print(f"exported {pdf} ({pdf.stat().st_size:,} bytes)")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--pdf", action="store_true")
    parser.add_argument("--no-code-images", action="store_true", help="reuse images already in assets/code")
    args = parser.parse_args()

    clean = clean_body(bd.read_body(SOURCE_MD))

    old = OUT_MD.read_text(encoding="utf-8")
    m = re.search(r"^# CHƯƠNG 3\.", old, flags=re.M)
    OUT_MD.write_text(old[: m.start()] + clean, encoding="utf-8")

    body = move_table_captions_below(clean)
    body = rci.render(body, CODE_DIR)
    figures, tables = collect_captions(body)
    FormDocx(SOURCE_MD, figures, tables).build(body, OUT_DOCX)
    print(f"wrote {OUT_DOCX} ({OUT_DOCX.stat().st_size:,} bytes); {len(figures)} hình, {len(tables)} bảng")
    if args.pdf:
        export_pdf(OUT_DOCX)


if __name__ == "__main__":
    main()
