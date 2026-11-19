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
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT, WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.oxml import OxmlElement
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
# "> **Công thức 3.5.** $...$" after bold markers are stripped by clean_body.
FORMULA_RE = re.compile(r"^\**Công thức (\d+\.\d+)\.\**\s*(.*)$")

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


def _plain(cell: str) -> tuple[str, bool]:
    """Visible text of a cell and whether it is mostly inline code (Consolas 10 pt)."""
    code = "".join(re.findall(r"`([^`]*)`", cell))
    text = re.sub(r"[*`]", "", cell).strip()
    return text, bool(code) and len(code) >= 0.6 * max(1, len(text))


def _widths(rows, n_cols, total_cm=16.0, min_cm=1.8):
    """Column widths for 13 pt table text: every column is at least as wide as its
    longest word (bold in the header), so Word never breaks a word; the remaining
    width goes to the columns with the most text."""
    per_char, per_char_bold, per_char_code, pad = 0.235, 0.29, 0.19, 0.6
    mins, needs = [], []
    for c in range(n_cols):
        col_min, col_len = 0.9, 1
        for r, row in enumerate(rows):
            if c >= len(row):
                continue
            text, is_code = _plain(row[c])
            unit = per_char_code if is_code else (per_char_bold if r == 0 else per_char)
            # Word may break after "-" and "/", so those split words too.
            words = re.split(r"(?<=[-/])|\s+", text)
            longest = max((len(w) for w in words), default=1)
            col_min = max(col_min, unit * longest + pad)
            if r > 0:
                col_len = max(col_len, len(text))
        mins.append(col_min)
        needs.append(col_len)
    if sum(mins) >= total_cm:
        return [m * total_cm / sum(mins) for m in mins]
    spare = total_cm - sum(mins)
    weights = [max(0.0, n * per_char - m) for n, m in zip(needs, mins)]
    if sum(weights) == 0:
        weights = [1.0] * n_cols
    return [m + spare * w / sum(weights) for m, w in zip(mins, weights)]


bd.compute_table_widths = _widths


_orig_make_omml = bd.make_omml


def _make_omml_clean(latex: str):
    r"""Normalise LaTeX that latex2mathml renders badly: \arg\min / \arg\max appear
    verbatim, and \ln n runs together as "lnn"."""
    latex = re.sub(r"\\arg\s*\\(min|max)", r"\\mathrm{arg\\,\1}", latex)
    latex = re.sub(r"\\(ln|log|exp)(?![a-zA-Z])\s*(?=[A-Za-z0-9\\])", r"\\\1\\,", latex)
    return _orig_make_omml(latex)


bd.make_omml = _make_omml_clean


ROT_DIR = BASE / "assets" / "rot"
ROTATE_GAIN = 1.3           # turn a VP diagram 90° when that prints it >= 30 % larger
PRINT_LONG_CM = 23.0        # long side of a rotated figure on the page


def rotate_wide_figures(body: str) -> str:
    """Turn wide Visual Paradigm figures 90° together with their caption.

    The caption is drawn into the picture (Times New Roman italic, 12 pt at print
    size) so both read when the page is turned clockwise; the Markdown caption line
    is dropped from the flow but stays in the list of figures (collected earlier)."""
    from PIL import Image, ImageDraw, ImageFont

    ROT_DIR.mkdir(parents=True, exist_ok=True)
    pattern = re.compile(r"!\[([^\]]*)\]\((assets/(?:vp|neo4j)/[^)]+\.png)\)\n\n(\*Hình \d+\.\d+\.[^\n]*\*)\n")

    def repl(m):
        src = BASE / m.group(2)
        raw = Image.open(src)
        if raw.mode in ("RGBA", "LA", "P"):
            raw = raw.convert("RGBA")
            im = Image.new("RGB", raw.size, "white")
            im.paste(raw, mask=raw.split()[-1])   # Neo4j exports a transparent background
        else:
            im = raw.convert("RGB")
        # Large Neo4j graph views are always turned so they print 23 cm long.
        always = src.name.startswith("neo4j_g")
        if not always:
            if m.group(2).startswith("assets/neo4j/"):
                return m.group(0)
            # Turn a VP diagram only when that prints it clearly larger (>= 30 %):
            # upright it gets 15.8 x 21.5 cm, turned 23 x 15.8 cm.
            upright = min(15.8 / im.width, 21.5 / im.height)
            turned = min(15.8 / im.height, PRINT_LONG_CM / im.width)
            if turned < ROTATE_GAIN * upright:
                return m.group(0)
        if always:
            # Neo4j's export keeps the whole canvas; trim the empty margin around the graph.
            from PIL import ImageChops
            box = ImageChops.difference(im, Image.new("RGB", im.size, "white")).getbbox()
            if box:
                pad = 40
                im = im.crop((max(0, box[0] - pad), max(0, box[1] - pad),
                              min(im.width, box[2] + pad), min(im.height, box[3] + pad)))
            # Keep whichever orientation prints the graph larger on a 15.8 x 23 cm area
            # (the caption takes ~1.5 cm of the height when upright).
            upright = min(15.8 / im.width, 21.5 / im.height)
            turned = min(15.8 / im.height, PRINT_LONG_CM / im.width)
            if upright >= turned:
                out = ROT_DIR / src.name
                im.save(out, optimize=True)
                return f"![{m.group(1)}]({out.relative_to(BASE).as_posix()})\n\n{m.group(3)}\n"
        caption = m.group(3).strip("*").strip()
        px_per_cm = im.width / PRINT_LONG_CM
        font = ImageFont.truetype(r"C:\Windows\Fonts\timesi.ttf", int(round(0.4233 * px_per_cm)))
        draw = ImageDraw.Draw(im)
        words, lines, cur = caption.split(), [], ""
        for w in words:
            test = (cur + " " + w).strip()
            if draw.textlength(test, font=font) > im.width * 0.92 and cur:
                lines.append(cur)
                cur = w
            else:
                cur = test
        lines.append(cur)
        line_h = int(font.size * 1.35)
        gap = int(0.45 * px_per_cm)
        canvas = Image.new("RGB", (im.width, im.height + gap + line_h * len(lines) + gap // 2), "white")
        canvas.paste(im, (0, 0))
        d = ImageDraw.Draw(canvas)
        y = im.height + gap
        for line in lines:
            d.text(((canvas.width - d.textlength(line, font=font)) / 2, y), line, font=font, fill="black")
            y += line_h
        out = ROT_DIR / src.name
        canvas.rotate(90, expand=True).save(out, optimize=True)
        return f"![rot]({out.relative_to(BASE).as_posix()})\n"

    return pattern.sub(repl, body)


def _text_direction(cell, value: str) -> None:
    tc_pr = cell._tc.get_or_add_tcPr()
    for old in tc_pr.findall(qn("w:textDirection")):
        tc_pr.remove(old)
    el = OxmlElement("w:textDirection")
    el.set(qn("w:val"), value)
    tc_pr.append(el)


def _no_borders(cell) -> None:
    tc_pr = cell._tc.get_or_add_tcPr()
    borders = OxmlElement("w:tcBorders")
    for edge in ("top", "bottom", "right"):
        el = OxmlElement(f"w:{edge}")
        el.set(qn("w:val"), "nil")
        borders.append(el)
    tc_pr.append(borders)


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
        self._rot = None
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
        if getattr(self, "_rot", None) is not None:
            if CAPTION_RE.match(text) and self._rot["caption"] is None:
                self._rot["caption"] = text
            else:
                self._rot["notes"].append(text)
            return
        if CAPTION_RE.match(text):
            p = self._new_para("Caption VN")
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            bd.add_inline(p, text.strip("*").strip(), italic=True, size=12, color=BLACK)
            return
        bd.add_inline(self._new_para("Normal"), text)

    def _image(self, alt, rel_path):
        if alt == "rot":
            from PIL import Image as _Img
            path = (self.base_dir / rel_path).resolve()
            w, h = _Img.open(path).size
            width_cm = min(15.8, PRINT_LONG_CM * w / h)
            p = self._new_para()
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p.paragraph_format.first_line_indent = Cm(0)
            p.paragraph_format.space_before = Pt(6)
            p.paragraph_format.space_after = Pt(6)
            p.paragraph_format.line_spacing = 1.0
            p.add_run().add_picture(str(path), width=Cm(width_cm))
            return
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
        if getattr(self, "_rot", None) is not None:
            self._rot["rows"] = rows
            return
        super()._table(rows, aligns)
        table = self.doc.tables[-1]
        for cell in table.rows[0].cells:
            cell.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
        # Same type as the body text: Times New Roman 13 pt, inline code Consolas 10 pt.
        m_ns = "http://schemas.openxmlformats.org/officeDocument/2006/math"
        for row in table.rows:
            for cell in row.cells:
                for p in cell.paragraphs:
                    p.paragraph_format.line_spacing = 1.1
                    for run in p.runs:
                        if run.font.name == bd.FONT_CODE:
                            run.font.size = Pt(10)
                        else:
                            run.font.name = bd.FONT_BODY
                            run._element.get_or_add_rPr().get_or_add_rFonts().set(qn("w:eastAsia"), bd.FONT_BODY)
                            run.font.size = Pt(13)
                    for omml in p._p.iter(f"{{{m_ns}}}oMath"):
                        bd.set_omml_size(omml, 13)
        # Keep each table on one page together with its caption (which follows it);
        # a table longer than a page repeats its header row instead.
        for i, row in enumerate(table.rows):
            tr_pr = row._tr.get_or_add_trPr()
            tr_pr.append(OxmlElement("w:cantSplit"))
            if i == 0:
                tr_pr.append(OxmlElement("w:tblHeader"))
            for cell in row.cells:
                for p in cell.paragraphs:
                    p.paragraph_format.keep_with_next = True
        # The spacer paragraph the base builder adds after every table sits between
        # the table and its caption: it must not allow a page break either.
        spacer = self.doc.paragraphs[-1]
        spacer.paragraph_format.keep_with_next = True
        if self._landscape:
            for row in table.rows:
                for cell in row.cells:
                    for p in cell.paragraphs:
                        p.paragraph_format.space_before = Pt(5)
                        p.paragraph_format.space_after = Pt(5)
                        for run in p.runs:
                            run.font.size = Pt(9) if run.font.name == bd.FONT_CODE else Pt(10.5)

    def _quote(self, line):
        m = FORMULA_RE.match(line.strip())
        if m and "$" in m.group(2):
            self._formula(m.group(1), m.group(2))
            return
        p = self._new_para("Quote Box")
        p.paragraph_format.left_indent = Cm(0.6)
        bd.border_paragraph(p, "left", "7F7F7F", 18, 8)
        bd.add_inline(p, line)

    def _formula(self, number: str, body: str):
        """Display equations: one centred line per equation, number (N.M) at the right
        of the last line, laid out in a borderless two-column table. Text written after
        the equations ("trong đó ...") becomes a normal paragraph below."""
        parts = re.split(r"(\$[^$]+\$)", body)
        equations, tail = [], ""
        for i, part in enumerate(parts):
            if part.startswith("$") and part.endswith("$") and len(part) > 2:
                if tail.strip(" ;,.") and equations:
                    # prose between equations: keep it (and the rest) as the explanation
                    tail = "".join(parts[i - 1:])
                    break
                equations.append(part[1:-1].strip())
                tail = ""
            else:
                tail += part
        tail = tail.strip().lstrip(";,").strip()

        table = self.doc.add_table(rows=len(equations), cols=2)
        table.alignment = WD_TABLE_ALIGNMENT.CENTER
        table.autofit = False
        tbl_pr = table._tbl.tblPr
        borders = tbl_pr.find(qn("w:tblBorders"))
        if borders is None:
            borders = OxmlElement("w:tblBorders")
            tbl_pr.append(borders)
        for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
            el = OxmlElement(f"w:{edge}")
            el.set(qn("w:val"), "nil")
            borders.append(el)
        widths = (Cm(14.4), Cm(1.6))
        for r, latex in enumerate(equations):
            row = table.rows[r]
            for c, cell in enumerate(row.cells):
                cell.width = widths[c]
                cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
                p = cell.paragraphs[0]
                pf = p.paragraph_format
                pf.first_line_indent = Cm(0)
                pf.left_indent = pf.right_indent = Cm(0)
                pf.space_before, pf.space_after, pf.line_spacing = Pt(4), Pt(4), 1.0
            eq_p = row.cells[0].paragraphs[0]
            eq_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            omml = bd.make_omml(latex)
            if omml is None:
                bd.add_math(eq_p, latex, size=13)
            else:
                bd.set_omml_size(omml, 13)
                para = OxmlElement("m:oMathPara")
                ppr = OxmlElement("m:oMathParaPr")
                jc = OxmlElement("m:jc")
                jc.set(qn("m:val"), "center")
                ppr.append(jc)
                para.append(ppr)
                inner = omml if omml.tag.endswith("}oMath") else omml.find(qn("m:oMath"))
                para.append(inner if inner is not None else omml)
                eq_p._p.append(para)
            num_p = row.cells[1].paragraphs[0]
            num_p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
            if r == len(equations) - 1:
                bd.set_run_font(num_p.add_run(f"({number})"), bd.FONT_BODY, 13, False, False, BLACK)
        self.doc.add_paragraph().paragraph_format.space_after = Pt(0)
        self.doc.paragraphs[-1].paragraph_format.line_spacing = 0.6
        if tail:
            text = tail[0].upper() + tail[1:]
            bd.add_inline(self._new_para("Normal"), text)

    # ---- rotated blocks (no landscape pages) ------------------------------
    # "<!-- LANDSCAPE:START/END -->" now means: turn the enclosed table 90° on a
    # portrait page. The table is transposed and every cell is written bottom-to-top,
    # so turning the page clockwise shows the original table; its caption becomes a
    # column on the right (= below the table once the page is turned).

    def _start_landscape(self):
        self._rot = {"rows": None, "caption": None, "notes": []}

    def _end_landscape(self):
        rot, self._rot = self._rot, None
        if rot and rot["rows"]:
            self._rotated_table(rot)

    def _rotated_table(self, rot):
        from docx.enum.table import WD_ROW_HEIGHT_RULE

        rows = rot["rows"]
        n_src_cols = len(rows[0])
        # Length of each page row (= width of a source column once the page is turned).
        # Cells are written bottom-to-top, so the text can only grow in length, never
        # in the number of lines, which is fixed by the page column width (~4 lines of
        # 13 pt). Each row therefore gets room for its longest cell in at most 4 lines,
        # and at least the longest header word in bold (~0.26 cm per character).
        mins, needs = [], []
        for k in range(n_src_cols):
            head = re.sub(r"[*`]", "", rows[0][k])
            cells = [re.sub(r"[*`]", "", r[k]) for r in rows[1:]]
            head_word = max((len(w) for w in head.split()), default=4)
            data_word = max((len(w) for c in cells for w in re.split(r"[\s/-]+", c)), default=4)
            mins.append(max(0.27 * head_word + 0.5, 0.235 * data_word + 0.5))
            needs.append(0.235 * max(len(c) for c in cells) / 4 + 0.4)
        budget = 23.5
        spare = max(0.0, budget - sum(mins))
        extra_need = [max(0.0, nd - mn) for nd, mn in zip(needs, mins)]
        total_extra = sum(extra_need) or 1.0
        widths = [mn + spare * e / total_extra for mn, e in zip(mins, extra_need)]
        scale = budget / sum(widths)
        extra = [t for t in [rot["caption"]] + rot["notes"] if t]
        brk = self.doc.add_paragraph()
        brk.add_run().add_break(WD_BREAK.PAGE)
        brk.paragraph_format.space_after = Pt(0)
        brk.paragraph_format.line_spacing = 1.0
        table = self.doc.add_table(rows=n_src_cols, cols=len(rows) + len(extra))
        table.alignment = WD_TABLE_ALIGNMENT.CENTER
        table.autofit = False
        bd.set_table_borders(table)
        side_w = 1.25
        data_w = (16.0 - side_w * len(extra)) / len(rows)
        for i in range(n_src_cols):
            src_col = n_src_cols - 1 - i            # first source column at the bottom
            row = table.rows[i]
            row.height = Cm(widths[src_col] * scale)
            row.height_rule = WD_ROW_HEIGHT_RULE.AT_LEAST
            tr_pr = row._tr.get_or_add_trPr()
            tr_pr.append(OxmlElement("w:cantSplit"))
            for j, src_row in enumerate(rows):
                cell = row.cells[j]
                cell.width = Cm(data_w)
                _text_direction(cell, "btLr")
                cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
                p = cell.paragraphs[0]
                p.paragraph_format.first_line_indent = Cm(0)
                p.paragraph_format.space_before = p.paragraph_format.space_after = Pt(2)
                p.paragraph_format.line_spacing = 1.0
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER if j == 0 else WD_ALIGN_PARAGRAPH.LEFT
                text = src_row[src_col].strip()
                bd.add_inline(p, text, bold=True if j == 0 else None, size=13, color=BLACK)
        for k, text in enumerate(extra):
            col = len(rows) + k
            top, bottom = table.cell(0, col), table.cell(n_src_cols - 1, col)
            merged = top.merge(bottom)
            for r in range(n_src_cols):
                table.cell(r, col).width = Cm(side_w)
            _text_direction(merged, "btLr")
            merged.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
            _no_borders(merged)
            p = merged.paragraphs[0]
            for extra_p in merged.paragraphs[1:]:
                extra_p._p.getparent().remove(extra_p._p)
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p.paragraph_format.first_line_indent = Cm(0)
            is_caption = k == 0 and rot["caption"] is not None
            bd.add_inline(p, text.strip("*").strip(), italic=True, size=12 if is_caption else 10.5, color=BLACK)
        self._pending_break = True

    def _rule(self):
        return None


# ---------------------------------------------------------------------------
# PDF export
# ---------------------------------------------------------------------------

def restore_full_resolution(pdf_path: Path, sources: list[Path]) -> None:
    """Word's PDF export downsamples pictures to ~200 dpi with no option to stop it.
    Put the original files back: each embedded image is matched to its source file
    by comparing 48x48 grey thumbnails, then replaced in place (same position/size)."""
    import fitz
    from PIL import Image, ImageChops, ImageStat

    def thumb(img):
        return img.convert("L").resize((48, 48), Image.BILINEAR)

    cands = []
    for src in dict.fromkeys(sources):
        if src.exists():
            im = Image.open(src)
            cands.append((src, im.width / im.height, im.width, thumb(im)))
    doc = fitz.open(str(pdf_path))
    done, replaced = set(), 0
    for page in doc:
        # skip the cover pages: their near-blank picture can otherwise match a
        # mostly-white diagram of the same aspect ratio and get replaced by it
        if "HỌC VIỆN CÔNG NGHỆ BƯU CHÍNH VIỄN THÔNG" in page.get_text():
            continue
        for info in page.get_images(full=True):
            xref, w, h = info[0], info[2], info[3]
            if xref in done or w < 300:
                continue
            done.add(xref)
            try:
                pix = fitz.Pixmap(doc, xref)
                if pix.alpha or pix.n > 3:
                    pix = fitz.Pixmap(fitz.csRGB, pix)
                emb = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
            except Exception:
                continue
            t = thumb(emb)
            if ImageStat.Stat(t).stddev[0] < 4:
                continue  # blank picture, nothing to restore
            best = None
            for src, ratio, width, ct in cands:
                if abs(ratio - w / h) / ratio > 0.02 or width <= w:
                    continue
                diff = ImageStat.Stat(ImageChops.difference(t, ct)).mean[0]
                if best is None or diff < best[0]:
                    best = (diff, src)
            if best and best[0] < 12:
                page.replace_image(xref, filename=str(best[1]))
                replaced += 1
    tmp = pdf_path.with_name(pdf_path.stem + "_hires.pdf")
    doc.save(str(tmp), garbage=3, deflate=True)
    doc.close()
    # a freshly written file is often held briefly by the virus scanner on Windows
    import os, time
    for attempt in range(20):
        try:
            os.replace(tmp, pdf_path)
            break
        except PermissionError:
            if attempt == 19:
                raise
            time.sleep(0.5)
    print(f"restored {replaced} images at full resolution")


def fit_display_equations(doc, min_size: float = 9.0) -> None:
    """Shrink display equations that Word wraps onto a second line until they fit
    on one line (measured by Word's own layout, line numbers of first/last char)."""
    wd_line = 10  # wdFirstCharacterLineNumber
    shrunk = 0
    for i in range(1, doc.OMaths.Count + 1):
        om = doc.OMaths(i)
        if om.Type != 0:  # 0 = display (our numbered formulas); skip inline math
            continue
        rng = om.Range
        size = rng.Font.Size if 1 < rng.Font.Size < 100 else 13.0
        while size > min_size:
            first = rng.Characters.First.Information(wd_line)
            last = rng.Characters.Last.Information(wd_line)
            if first == last:
                break
            size -= 0.5
            rng.Font.Size = size
            doc.Repaginate()
        if size < 13:
            shrunk += 1
    print(f"display equations shrunk to one line: {shrunk}")


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
    # Keep figures at full resolution (Word otherwise downsamples to 220 ppi on save).
    if d.settings.element.find(qn("w:doNotAutoCompressPictures")) is None:
        d.settings.element.append(OxmlElement("w:doNotAutoCompressPictures"))
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

        fit_display_equations(doc)
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
                style.ParagraphFormat.LeftIndent = (indent * 28.3465)
                style.ParagraphFormat.FirstLineIndent = -(hang * 28.3465)
                style.ParagraphFormat.RightIndent = (right * 28.3465)
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
    parser.add_argument("--source", default=SOURCE_MD.name, help="Markdown source, e.g. in_chuong_2_5.md")
    parser.add_argument("--out", default=OUT_DOCX.stem, help="output stem, e.g. DO_AN_IN_CHUONG_2_5")
    args = parser.parse_args()
    source_md = BASE / args.source
    out_docx = BASE / f"{args.out}.docx"
    out_md = BASE / f"{args.out}.md"

    clean = clean_body(bd.read_body(source_md))

    # Front matter (cover text) of the Markdown copy comes from the first print edition.
    old = (out_md if out_md.exists() else OUT_MD).read_text(encoding="utf-8")
    m = re.search(r"^# (MỤC LỤC|CHƯƠNG \d+\.)", old, flags=re.M)
    out_md.write_text(old[: m.start()] + clean, encoding="utf-8")

    body = move_table_captions_below(clean)
    body = rci.render(body, CODE_DIR, reuse=args.no_code_images)
    figures, tables = collect_captions(body)
    body = rotate_wide_figures(body)
    FormDocx(source_md, figures, tables).build(body, out_docx)
    print(f"wrote {out_docx} ({out_docx.stat().st_size:,} bytes); {len(figures)} hình, {len(tables)} bảng")
    if args.pdf:
        export_pdf(out_docx)
        images = [(BASE / m).resolve() for m in re.findall(r"!\[[^\]]*\]\(([^)]+)\)", body)]
        restore_full_resolution(out_docx.with_suffix(".pdf"), images)


if __name__ == "__main__":
    main()
