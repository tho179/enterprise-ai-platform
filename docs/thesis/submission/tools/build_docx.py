"""
Build a formatted A4 .docx from the thesis Markdown.

Features:
- Vietnamese thesis layout: Times New Roman 13pt, 1.5 line spacing, A4 margins.
- Cover page, automatic TOC field, headers/footers with page numbers.
- Markdown headings, paragraphs, bold/italic, inline code, lists, blockquotes.
- Pipe tables with header shading and borders.
- Images with captions, scaled to the text width.
- Native Word equations (OMML) converted from LaTeX via latex2mathml + Office XSL.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Iterable, List, Optional, Tuple

from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.section import WD_ORIENT
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor
from lxml import etree
from PIL import Image

try:
    import latex2mathml.converter as latex2mathml
except Exception:  # pragma: no cover
    latex2mathml = None


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

FONT_BODY = "Times New Roman"
FONT_CODE = "Consolas"
COLOR_TEXT = RGBColor(0x20, 0x21, 0x24)
COLOR_MUTED = RGBColor(0x5F, 0x63, 0x68)
COLOR_ACCENT = RGBColor(0x1A, 0x73, 0xE8)

OMML_XSL_CANDIDATES = [
    Path(r"C:\Program Files\Microsoft Office\root\Office16\MML2OMML.XSL"),
    Path(r"C:\Program Files (x86)\Microsoft Office\root\Office16\MML2OMML.XSL"),
]
OMML_TRANSFORM = None
for candidate in OMML_XSL_CANDIDATES:
    if candidate.exists():
        try:
            OMML_TRANSFORM = etree.XSLT(etree.parse(str(candidate)))
            break
        except Exception:
            OMML_TRANSFORM = None

TOKEN_RE = re.compile(
    r"(\*\*.+?\*\*|`[^`]+`|\$[^$]+\$|\[[^\]]+\]\([^)]+\)|\*[^*]+\*)"
)
HEADING_RE = re.compile(r"^(#{1,6})\s+(.*)$")
IMAGE_RE = re.compile(r"^!\[([^\]]*)\]\(([^)]+)\)\s*$")
BULLET_RE = re.compile(r"^(\s*)[-*+]\s+(.*)$")
NUMBER_RE = re.compile(r"^(\s*)(\d+)[.)]\s+(.*)$")
RULE_RE = re.compile(r"^-{3,}\s*$")


# ---------------------------------------------------------------------------
# Low-level docx helpers
# ---------------------------------------------------------------------------

def set_run_font(run, name=FONT_BODY, size=None, bold=None, italic=None, color=None):
    run.font.name = name
    rpr = run._element.get_or_add_rPr()
    rfonts = rpr.find(qn("w:rFonts"))
    if rfonts is None:
        rfonts = OxmlElement("w:rFonts")
        rpr.insert(0, rfonts)
    rfonts.set(qn("w:ascii"), name)
    rfonts.set(qn("w:hAnsi"), name)
    rfonts.set(qn("w:eastAsia"), name)
    rfonts.set(qn("w:cs"), name)
    if size is not None:
        run.font.size = Pt(size)
    if bold is not None:
        run.font.bold = bold
    if italic is not None:
        run.font.italic = italic
    if color is not None:
        run.font.color.rgb = color


def set_style_font(style, name=FONT_BODY, size=None, bold=None, italic=None, color=None):
    style.font.name = name
    rpr = style.element.get_or_add_rPr()
    rfonts = rpr.find(qn("w:rFonts"))
    if rfonts is None:
        rfonts = OxmlElement("w:rFonts")
        rpr.insert(0, rfonts)
    for attr in ("w:asciiTheme", "w:hAnsiTheme", "w:eastAsiaTheme", "w:cstheme"):
        if rfonts.get(qn(attr)) is not None:
            del rfonts.attrib[qn(attr)]
    for attr in ("w:ascii", "w:hAnsi", "w:eastAsia", "w:cs"):
        rfonts.set(qn(attr), name)
    if size is not None:
        style.font.size = Pt(size)
    if bold is not None:
        style.font.bold = bold
    if italic is not None:
        style.font.italic = italic
    if color is not None:
        style.font.color.rgb = color


def shade_paragraph(paragraph, fill: str):
    ppr = paragraph._p.get_or_add_pPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), fill)
    ppr.append(shd)


def border_paragraph(paragraph, side="left", color="1A73E8", size=18, space=8):
    ppr = paragraph._p.get_or_add_pPr()
    pbdr = ppr.find(qn("w:pBdr"))
    if pbdr is None:
        pbdr = OxmlElement("w:pBdr")
        ppr.append(pbdr)
    el = OxmlElement(f"w:{side}")
    el.set(qn("w:val"), "single")
    el.set(qn("w:sz"), str(size))
    el.set(qn("w:space"), str(space))
    el.set(qn("w:color"), color)
    pbdr.append(el)


def shade_run(run, fill: str):
    rpr = run._element.get_or_add_rPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), fill)
    rpr.append(shd)


def add_field(paragraph, instruction: str, placeholder: str = "1"):
    run = paragraph.add_run()
    begin = OxmlElement("w:fldChar")
    begin.set(qn("w:fldCharType"), "begin")
    instr = OxmlElement("w:instrText")
    instr.set(qn("xml:space"), "preserve")
    instr.text = instruction
    separate = OxmlElement("w:fldChar")
    separate.set(qn("w:fldCharType"), "separate")
    text = OxmlElement("w:t")
    text.text = placeholder
    end = OxmlElement("w:fldChar")
    end.set(qn("w:fldCharType"), "end")
    for el in (begin, instr, separate, text, end):
        run._r.append(el)
    return run


def add_toc(paragraph):
    add_field(paragraph, r'TOC \o "1-2" \h \z \u', "Mục lục sẽ được cập nhật khi mở bằng Microsoft Word.")


def set_table_borders(table, color="A6A6A6", size=4):
    tbl = table._tbl
    tblpr = tbl.tblPr
    borders = OxmlElement("w:tblBorders")
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        el = OxmlElement(f"w:{edge}")
        el.set(qn("w:val"), "single")
        el.set(qn("w:sz"), str(size))
        el.set(qn("w:space"), "0")
        el.set(qn("w:color"), color)
        borders.append(el)
    tblpr.append(borders)


def set_table_cell_margins(table, left=80, right=80, top=30, bottom=30):
    tbl = table._tbl
    tblpr = tbl.tblPr
    mar = OxmlElement("w:tblCellMar")
    for edge, value in (("top", top), ("left", left), ("bottom", bottom), ("right", right)):
        el = OxmlElement(f"w:{edge}")
        el.set(qn("w:w"), str(value))
        el.set(qn("w:type"), "dxa")
        mar.append(el)
    tblpr.append(mar)


def set_cell_shading(cell, fill: str):
    tcpr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), fill)
    tcpr.append(shd)


def set_repeat_table_header(row):
    tr = row._tr
    trpr = tr.get_or_add_trPr()
    header = OxmlElement("w:tblHeader")
    header.set(qn("w:val"), "true")
    trpr.append(header)


def set_cant_split(row):
    trpr = row._tr.get_or_add_trPr()
    cant = OxmlElement("w:cantSplit")
    trpr.append(cant)


def compute_table_widths(rows: List[List[str]], n_cols: int, total_cm: float = 16.0, min_cm: float = 1.8) -> List[float]:
    """Content-aware widths; avoids Word squeezing the first column to one character."""
    # Data-dictionary tables have predictable needs: "Cột", "Kiểu", "Null", "Ý nghĩa", "Ràng buộc".
    if n_cols == 5 and rows and rows[0] and rows[0][0].strip() == "Cột":
        return [2.9, 2.9, 1.8, 4.2, 4.2]
    max_lens = []
    for c in range(n_cols):
        vals = [r[c] for r in rows if c < len(r)]
        max_lens.append(max((len(v) for v in vals), default=1))
    weights = []
    for length in max_lens:
        if length <= 2:
            weights.append(1.0)
        elif length <= 5:
            weights.append(1.8)
        else:
            weights.append(min(length, 50) ** 0.75)
    total_weight = sum(weights) or 1.0
    widths = [total_cm * w / total_weight for w in weights]
    for _ in range(6):
        fixed = [i for i, w in enumerate(widths) if w < min_cm]
        if not fixed:
            break
        for i in fixed:
            widths[i] = min_cm
        rest = total_cm - min_cm * len(fixed)
        flex = [i for i in range(n_cols) if i not in fixed]
        if not flex or rest <= 0:
            break
        flex_total = sum(weights[i] for i in flex) or 1.0
        for i in flex:
            widths[i] = rest * weights[i] / flex_total
    scale = total_cm / (sum(widths) or 1.0)
    return [w * scale for w in widths]


def set_table_fixed_widths(table, widths_cm: List[float]):
    tblpr = table._tbl.tblPr
    for tag in ("w:tblW", "w:tblLayout"):
        for old in tblpr.findall(qn(tag)):
            tblpr.remove(old)
    tblw = OxmlElement("w:tblW")
    tblw.set(qn("w:w"), str(int(sum(widths_cm) * 567)))
    tblw.set(qn("w:type"), "dxa")
    tblpr.append(tblw)
    layout = OxmlElement("w:tblLayout")
    layout.set(qn("w:type"), "fixed")
    tblpr.append(layout)
    for i, width in enumerate(widths_cm):
        table.columns[i].width = Cm(width)
        for cell in table.columns[i].cells:
            cell.width = Cm(width)


def set_page_number_start(section, start=1):
    sectpr = section._sectPr
    for old in sectpr.findall(qn("w:pgNumType")):
        sectpr.remove(old)
    pgnum = OxmlElement("w:pgNumType")
    pgnum.set(qn("w:start"), str(start))
    sectpr.append(pgnum)


def continue_page_numbering(section):
    """Keep the PAGE field counting across landscape/portrait section breaks."""
    sectpr = section._sectPr
    for old in sectpr.findall(qn("w:pgNumType")):
        sectpr.remove(old)


def set_update_fields(doc):
    settings = doc.settings.element
    update = OxmlElement("w:updateFields")
    update.set(qn("w:val"), "true")
    settings.append(update)


def set_core_properties(doc, title: str, subject: str = "Báo cáo đồ án tốt nghiệp"):
    cp = doc.core_properties
    cp.title = title
    cp.subject = subject
    cp.author = "Nguyễn Quý Thọ; Nguyễn Xuân Đạt; Hoàng Lê Đức"
    cp.last_modified_by = "Nguyễn Quý Thọ; Nguyễn Xuân Đạt; Hoàng Lê Đức"
    cp.keywords = "EAKWP, RAG, học sâu, cơ sở dữ liệu, cơ sở tri thức, tiếng Việt"
    cp.comments = "Báo cáo được tạo từ Markdown; cập nhật mục lục bằng Ctrl+A, F9 trong Word."
    cp.category = "Đồ án tốt nghiệp"
    cp.language = "vi-VN"


# ---------------------------------------------------------------------------
# Math
# ---------------------------------------------------------------------------

def latex_to_text(latex: str) -> str:
    """Readable fallback when OMML conversion is unavailable."""
    s = latex
    s = s.replace(r"\|", "‖").replace(r"\cdot", "·").replace(r"\times", "×")
    s = s.replace(r"\le", "≤").replace(r"\ge", "≥").replace(r"\ne", "≠")
    s = s.replace(r"\approx", "≈").replace(r"\infty", "∞")
    s = s.replace(r"\rightarrow", "→").replace(r"\to", "→")
    s = s.replace(r"\in", "∈").replace(r"\cap", "∩").replace(r"\cup", "∪")
    s = s.replace(r"\sum", "Σ").replace(r"\sqrt", "√")
    s = s.replace(r"\log", "log").replace(r"\exp", "exp")
    s = s.replace(r"\max", "max").replace(r"\min", "min")
    s = s.replace(r"\arg\min", "argmin").replace(r"\arg\max", "argmax")
    s = s.replace(r"\mathbb{1}", "1").replace(r"\mathbb{R}", "R")
    s = s.replace(r"\mathcal{L}", "L").replace(r"\mathcal{X}", "X").replace(r"\mathcal{Y}", "Y")
    s = s.replace(r"\theta", "θ").replace(r"\tau", "τ").replace(r"\sigma", "σ")
    s = s.replace(r"\lambda", "λ").replace(r"\beta", "β").replace(r"\eta", "η")
    s = s.replace(r"\epsilon", "ε").replace(r"\mu", "μ").replace(r"\Delta", "Δ")
    s = s.replace(r"\partial", "∂").replace(r"\hat", "")
    s = s.replace(r"\left", "").replace(r"\right", "")
    s = s.replace(r"\,", " ").replace(r"\;", " ").replace(r"\!", "")
    s = s.replace(r"\quad", "  ")
    # \frac{a}{b} -> (a)/(b), repeat for simple nesting
    frac = re.compile(r"\\frac\{([^{}]*)\}\{([^{}]*)\}")
    for _ in range(4):
        s = frac.sub(r"(\1)/(\2)", s)
    # \text{...} and \mathrm{...}
    s = re.sub(r"\\text\{([^{}]*)\}", r"\1", s)
    s = re.sub(r"\\mathrm\{([^{}]*)\}", r"\1", s)
    # Remove remaining braces used for grouping/subscripts
    s = re.sub(r"_\{([^{}]*)\}", r"_\1", s)
    s = re.sub(r"\^\{([^{}]*)\}", r"^\1", s)
    s = s.replace("{", "").replace("}", "")
    return s.strip()


def make_omml(latex: str):
    if OMML_TRANSFORM is None or latex2mathml is None:
        return None
    try:
        # latex2mathml keeps the backslash in \text{page\_start}; Word would show it.
        latex = latex.replace("\\_", "_")
        mathml = latex2mathml.convert(latex)
        root = etree.fromstring(mathml.encode("utf-8"))
        result = OMML_TRANSFORM(root)
        return result.getroot()
    except Exception:
        return None


def set_omml_size(omml, size: float):
    """Apply a Word run size to every math run so long display formulas fit."""
    m_ns = "http://schemas.openxmlformats.org/officeDocument/2006/math"
    w_ns = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
    half_points = str(int(round(size * 2)))
    for r in omml.iter(f"{{{m_ns}}}r"):
        for old in r.findall(f"{{{w_ns}}}rPr"):
            r.remove(old)
        rpr = etree.Element(f"{{{w_ns}}}rPr")
        sz = etree.SubElement(rpr, f"{{{w_ns}}}sz")
        sz.set(f"{{{w_ns}}}val", half_points)
        szcs = etree.SubElement(rpr, f"{{{w_ns}}}szCs")
        szcs.set(f"{{{w_ns}}}val", half_points)
        idx = 1 if r.find(f"{{{m_ns}}}rPr") is not None else 0
        r.insert(idx, rpr)


def add_math(paragraph, latex: str, size: Optional[float] = None):
    omml = make_omml(latex)
    if omml is not None:
        if size:
            set_omml_size(omml, size)
        paragraph._p.append(omml)
    else:
        run = paragraph.add_run(latex_to_text(latex))
        set_run_font(run, FONT_BODY, size or 13, italic=True)


# ---------------------------------------------------------------------------
# Inline Markdown
# ---------------------------------------------------------------------------

def add_inline(paragraph, text: str, bold=None, italic=None, size=None, color=None, font=FONT_BODY, math_size=None, code_break=False):
    pos = 0
    for match in TOKEN_RE.finditer(text):
        if match.start() > pos:
            run = paragraph.add_run(text[pos:match.start()])
            set_run_font(run, font, size, bold, italic, color)
        token = match.group(0)
        if token.startswith("**") and token.endswith("**") and len(token) > 4:
            add_inline(paragraph, token[2:-2], True, italic, size, color, font, math_size, code_break)
        elif token.startswith("`") and token.endswith("`") and len(token) > 2:
            code_text = token[1:-1]
            if code_break:
                # Zero-width spaces let Word wrap long test names at underscores/slashes.
                code_text = re.sub(r"([_/.])", "\\1\u200b", code_text)
            run = paragraph.add_run(code_text)
            set_run_font(run, FONT_CODE, (size - 1) if size else 10, bold, italic, RGBColor(0x8B, 0x1A, 0x1A))
            shade_run(run, "F1F3F4")
        elif token.startswith("$") and token.endswith("$") and len(token) > 2:
            add_math(paragraph, token[1:-1], math_size)
        elif token.startswith("[") and "](" in token and token.endswith(")"):
            label, url = re.match(r"\[([^\]]+)\]\(([^)]+)\)", token).groups()
            run = paragraph.add_run(label)
            set_run_font(run, font, size, bold, italic, COLOR_ACCENT)
            run.font.underline = True
            if not url.startswith("assets/") and not url.startswith("#"):
                tail = paragraph.add_run(f" ({url})")
                set_run_font(tail, font, (size - 1) if size else 9, False, True, COLOR_MUTED)
        elif token.startswith("*") and token.endswith("*") and len(token) > 2:
            add_inline(paragraph, token[1:-1], bold, True, size, color, font, math_size, code_break)
        else:
            run = paragraph.add_run(token)
            set_run_font(run, font, size, bold, italic, color)
        pos = match.end()
    if pos < len(text):
        run = paragraph.add_run(text[pos:])
        set_run_font(run, font, size, bold, italic, color)


# ---------------------------------------------------------------------------
# Converter
# ---------------------------------------------------------------------------

class ThesisDocx:
    def __init__(self, md_path: Path, cover_title: str, is_excerpt=False, chapter_label="", header_text=""):
        self.md_path = md_path
        self.base_dir = md_path.parent
        self.cover_title = cover_title
        self.is_excerpt = is_excerpt
        self.chapter_label = chapter_label
        self.header_text = header_text or "BÁO CÁO ĐỒ ÁN TỐT NGHIỆP — EAKWP"
        self.doc = Document()
        self._setup_page(self.doc.sections[0])
        self._setup_styles()
        self._add_cover()
        self._add_body_section()
        self._fig_no = 0
        self._table_no = 0
        self._pending_break = False
        self._landscape = False
        self._text_width_cm = 16.0
        self._max_img_w = 15.8
        self._max_img_h = 20.5

    # ---- setup ---------------------------------------------------------

    def _setup_page(self, section):
        section.orientation = WD_ORIENT.PORTRAIT
        section.page_width = Cm(21)
        section.page_height = Cm(29.7)
        section.top_margin = Cm(2.5)
        section.bottom_margin = Cm(2.5)
        section.left_margin = Cm(3.0)
        section.right_margin = Cm(2.0)
        section.header_distance = Cm(1.2)
        section.footer_distance = Cm(1.2)

    def _setup_styles(self):
        styles = self.doc.styles

        normal = styles["Normal"]
        set_style_font(normal, FONT_BODY, 13, False, False, COLOR_TEXT)
        pf = normal.paragraph_format
        pf.line_spacing = 1.5
        pf.space_after = Pt(6)
        pf.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        pf.first_line_indent = Cm(1.0)

        for name, size, bold, italic, before, after, align in [
            ("Heading 1", 17, True, False, 12, 12, WD_ALIGN_PARAGRAPH.CENTER),
            ("Heading 2", 14, True, False, 12, 6, WD_ALIGN_PARAGRAPH.LEFT),
            ("Heading 3", 13, True, False, 10, 4, WD_ALIGN_PARAGRAPH.LEFT),
            ("Heading 4", 13, True, True, 8, 4, WD_ALIGN_PARAGRAPH.LEFT),
        ]:
            style = styles[name]
            set_style_font(style, FONT_BODY, size, bold, italic, COLOR_TEXT)
            p = style.paragraph_format
            p.first_line_indent = Cm(0)
            p.space_before = Pt(before)
            p.space_after = Pt(after)
            p.line_spacing = 1.2
            p.alignment = align
            p.keep_with_next = True

        from docx.enum.style import WD_STYLE_TYPE
        caption = styles.add_style("Caption VN", WD_STYLE_TYPE.PARAGRAPH)
        caption.base_style = styles["Normal"]
        set_style_font(caption, FONT_BODY, 10, False, False, COLOR_MUTED)
        cp = caption.paragraph_format
        cp.first_line_indent = Cm(0)
        cp.alignment = WD_ALIGN_PARAGRAPH.CENTER
        cp.space_before = Pt(2)
        cp.space_after = Pt(10)
        cp.line_spacing = 1.1

        code = styles.add_style("Code Block", WD_STYLE_TYPE.PARAGRAPH)
        code.base_style = styles["Normal"]
        set_style_font(code, FONT_CODE, 8.5, False, False, COLOR_TEXT)
        cop = code.paragraph_format
        cop.first_line_indent = Cm(0)
        cop.left_indent = Cm(0.5)
        cop.right_indent = Cm(0.3)
        cop.space_before = Pt(4)
        cop.space_after = Pt(6)
        cop.line_spacing = 1.0
        cop.alignment = WD_ALIGN_PARAGRAPH.LEFT

        quote = styles.add_style("Quote Box", WD_STYLE_TYPE.PARAGRAPH)
        quote.base_style = styles["Normal"]
        set_style_font(quote, FONT_BODY, 12.5, False, False, COLOR_TEXT)
        qp = quote.paragraph_format
        qp.first_line_indent = Cm(0)
        qp.left_indent = Cm(0.8)
        qp.right_indent = Cm(0.8)
        qp.space_before = Pt(5)
        qp.space_after = Pt(5)
        qp.line_spacing = 1.2
        qp.alignment = WD_ALIGN_PARAGRAPH.LEFT

        tochead = styles.add_style("TOC Heading VN", WD_STYLE_TYPE.PARAGRAPH)
        tochead.base_style = styles["Normal"]
        set_style_font(tochead, FONT_BODY, 16, True, False, COLOR_TEXT)
        tp = tochead.paragraph_format
        tp.first_line_indent = Cm(0)
        tp.alignment = WD_ALIGN_PARAGRAPH.CENTER
        tp.space_before = Pt(0)
        tp.space_after = Pt(10)
        tp.line_spacing = 1.2

        note = styles.add_style("Note Small", WD_STYLE_TYPE.PARAGRAPH)
        note.base_style = styles["Normal"]
        set_style_font(note, FONT_BODY, 9, False, True, COLOR_MUTED)
        np_ = note.paragraph_format
        np_.first_line_indent = Cm(0)
        np_.alignment = WD_ALIGN_PARAGRAPH.LEFT
        np_.space_before = Pt(2)
        np_.space_after = Pt(6)
        np_.line_spacing = 1.1

    # ---- cover ---------------------------------------------------------

    def _cover_para(self, text, size=13, bold=False, italic=False, before=0, after=0, color=COLOR_TEXT):
        p = self.doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        pf = p.paragraph_format
        pf.first_line_indent = Cm(0)
        pf.space_before = Pt(before)
        pf.space_after = Pt(after)
        pf.line_spacing = 1.25
        run = p.add_run(text)
        set_run_font(run, FONT_BODY, size, bold, italic, color)
        return p

    def _add_cover(self):
        self._cover_para("", 12, after=0)
        self._cover_para("BỘ KHOA HỌC VÀ CÔNG NGHỆ", 11, True, after=1)
        self._cover_para("HỌC VIỆN CÔNG NGHỆ BƯU CHÍNH VIỄN THÔNG", 13, True, after=1)
        self._cover_para("KHOA CÔNG NGHỆ THÔNG TIN 1", 13, True, after=0)
        for _ in range(2):
            self._cover_para("", 12)
        self._cover_para("BÁO CÁO ĐỒ ÁN TỐT NGHIỆP", 18, True, after=8)
        if self.is_excerpt and self.chapter_label:
            self._cover_para(f"BẢN TRÍCH {self.chapter_label}", 12, False, True, after=4)
        self._cover_para("ĐỀ TÀI:", 14, True, after=6)
        title_size = 20 if len(self.cover_title) < 90 else 18
        self._cover_para(self.cover_title.upper(), title_size, True, after=8)
        self._cover_para("Niên khóa: 2022–2027 — Hệ: Đại học chính quy", 12, after=0)
        self._cover_para("", 12)
        self._cover_para("Giảng viên hướng dẫn: PGS.TS Trần Đình Quế", 13, after=4)
        self._cover_para("Sinh viên thực hiện:", 13, after=2)
        self._cover_para("Nguyễn Quý Thọ – B22DCCN836", 13, after=1)
        self._cover_para("Nguyễn Xuân Đạt – B22DCCN200", 13, after=1)
        self._cover_para("Hoàng Lê Đức – B22DCCN224", 13, after=0)
        for _ in range(2):
            self._cover_para("", 12)
        self._cover_para("Hà Nội - 2026", 13, False, True, after=0)

    def _add_body_section(self):
        section = self.doc.add_section(WD_SECTION.NEW_PAGE)
        self._setup_page(section)
        section.header.is_linked_to_previous = False
        section.footer.is_linked_to_previous = False

        # Header
        header = section.header
        hp = header.paragraphs[0]
        hp.text = ""
        hp.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        hp.paragraph_format.first_line_indent = Cm(0)
        hp.paragraph_format.space_after = Pt(2)
        run = hp.add_run(self.header_text)
        set_run_font(run, FONT_BODY, 9, False, False, COLOR_MUTED)
        border_paragraph(hp, "bottom", "BFBFBF", 4, 1)

        # Footer with page number
        footer = section.footer
        fp = footer.paragraphs[0]
        fp.text = ""
        fp.alignment = WD_ALIGN_PARAGRAPH.CENTER
        fp.paragraph_format.first_line_indent = Cm(0)
        run = fp.add_run("Trang ")
        set_run_font(run, FONT_BODY, 10, False, False, COLOR_MUTED)
        field = add_field(fp, "PAGE", "1")
        set_run_font(field, FONT_BODY, 10, False, False, COLOR_MUTED)
        set_page_number_start(section, 1)

    def _start_landscape(self):
        """Insert a landscape section for wide comparison tables."""
        section = self.doc.add_section(WD_SECTION.NEW_PAGE)
        continue_page_numbering(section)
        section.orientation = WD_ORIENT.LANDSCAPE
        section.page_width = Cm(29.7)
        section.page_height = Cm(21)
        section.top_margin = Cm(1.8)
        section.bottom_margin = Cm(1.8)
        section.left_margin = Cm(2.0)
        section.right_margin = Cm(2.0)
        section.header_distance = Cm(1.0)
        section.footer_distance = Cm(1.0)
        section.header.is_linked_to_previous = True
        section.footer.is_linked_to_previous = True
        self._landscape = True
        self._text_width_cm = 25.7
        self._max_img_w = 25.0
        self._max_img_h = 16.0

    def _end_landscape(self):
        section = self.doc.add_section(WD_SECTION.NEW_PAGE)
        continue_page_numbering(section)
        self._setup_page(section)
        section.header_distance = Cm(1.2)
        section.footer_distance = Cm(1.2)
        self._landscape = False
        self._text_width_cm = 16.0
        self._max_img_w = 15.8
        self._max_img_h = 20.5

    # ---- blocks --------------------------------------------------------

    def _new_para(self, style=None):
        p = self.doc.add_paragraph(style=style) if style else self.doc.add_paragraph()
        if self._pending_break:
            p.paragraph_format.page_break_before = True
            self._pending_break = False
        return p

    def _flush(self, buffer: List[str]):
        if not buffer:
            return
        text = " ".join(buffer).strip()
        buffer.clear()
        if not text:
            return

        # Caption lines: *Hình ...* / **Bảng ...**
        stripped = text.strip()
        if (stripped.startswith("*Hình") or stripped.startswith("*Bảng") or
                stripped.startswith("**Hình") or stripped.startswith("**Bảng")):
            p = self._new_para("Caption VN")
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            add_inline(p, stripped, size=10, color=COLOR_MUTED)
            return

        p = self._new_para("Normal")
        add_inline(p, text)

    def _heading(self, level, text):
        if text.strip().upper() == "MỤC LỤC":
            p = self._new_para("TOC Heading VN")
            run = p.add_run("MỤC LỤC")
            set_run_font(run, FONT_BODY, 16, True, False, COLOR_TEXT)
            return
        level = min(level, 4)
        style = f"Heading {level}"
        p = self._new_para(style)
        add_inline(p, text)

    def _code_block(self, lines: List[str]):
        p = self._new_para("Code Block")
        # Long DDL blocks must be allowed to split; otherwise the heading is
        # stranded alone on a nearly blank page.
        p.paragraph_format.keep_together = len(lines) <= 18
        shade_paragraph(p, "F7F7F7")
        border_paragraph(p, "left", "D0D7DE", 12, 6)
        border_paragraph(p, "top", "D0D7DE", 4, 2)
        border_paragraph(p, "bottom", "D0D7DE", 4, 2)
        for i, line in enumerate(lines):
            if i:
                p.add_run().add_break()
            run = p.add_run(line)
            set_run_font(run, FONT_CODE, 8.5, False, False, COLOR_TEXT)

    def _image(self, alt: str, rel_path: str):
        path = (self.base_dir / rel_path).resolve()
        if not path.exists():
            p = self._new_para()
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            run = p.add_run(f"[Thiếu ảnh: {rel_path}]")
            set_run_font(run, FONT_BODY, 10, False, True, RGBColor(0xC5, 0x22, 0x1F))
            return
        try:
            with Image.open(path) as im:
                px_w, px_h = im.size
            aspect = px_w / px_h if px_h else 1.5
        except Exception:
            aspect = 1.5
        max_w, max_h = self._max_img_w, self._max_img_h
        width = max_w
        height = width / aspect
        if height > max_h:
            height = max_h
            width = height * aspect
        p = self._new_para()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.first_line_indent = Cm(0)
        p.paragraph_format.space_before = Pt(6)
        p.paragraph_format.space_after = Pt(2)
        run = p.add_run()
        run.add_picture(str(path), width=Cm(width))

    def _table(self, rows: List[List[str]], aligns: List[str]):
        if not rows:
            return
        n_cols = max(len(r) for r in rows)
        rows = [r + [""] * (n_cols - len(r)) for r in rows]
        if self._pending_break:
            spacer = self._new_para()
            spacer.paragraph_format.space_before = Pt(0)
            spacer.paragraph_format.space_after = Pt(0)
            spacer.paragraph_format.line_spacing = 1.0
        table = self.doc.add_table(rows=len(rows), cols=n_cols)
        table.alignment = WD_TABLE_ALIGNMENT.CENTER
        table.autofit = False
        set_table_borders(table)
        set_table_cell_margins(table)
        widths = compute_table_widths(
            rows, n_cols, total_cm=self._text_width_cm,
            min_cm=1.3 if self._landscape else 1.8,
        )
        set_table_fixed_widths(table, widths)
        font_size = 7.0 if n_cols >= 11 else (8.5 if n_cols >= 8 else (9 if n_cols >= 5 else 10))
        if self._landscape and n_cols >= 11:
            font_size = 8.5

        for r_idx, row in enumerate(rows):
            set_cant_split(table.rows[r_idx])
            for c_idx, cell_text in enumerate(row):
                cell = table.cell(r_idx, c_idx)
                cell.vertical_alignment = 1  # center
                p = cell.paragraphs[0]
                p.style = self.doc.styles["Normal"]
                p.paragraph_format.first_line_indent = Cm(0)
                p.paragraph_format.space_before = Pt(0)
                p.paragraph_format.space_after = Pt(0)
                p.paragraph_format.line_spacing = 1.0
                p.alignment = {
                    "left": WD_ALIGN_PARAGRAPH.LEFT,
                    "center": WD_ALIGN_PARAGRAPH.CENTER,
                    "right": WD_ALIGN_PARAGRAPH.RIGHT,
                }.get(aligns[c_idx] if c_idx < len(aligns) else "left", WD_ALIGN_PARAGRAPH.LEFT)
                if r_idx == 0:
                    add_inline(p, cell_text, bold=True, size=font_size, code_break=True)
                else:
                    add_inline(p, cell_text, size=font_size, code_break=True)
                if r_idx == 0:
                    set_cell_shading(cell, "D9E2F3")
                elif r_idx % 2 == 0:
                    set_cell_shading(cell, "F3F6FC")
        set_repeat_table_header(table.rows[0])
        # small spacer after table
        spacer = self.doc.add_paragraph()
        spacer.paragraph_format.space_before = Pt(0)
        spacer.paragraph_format.space_after = Pt(0)
        spacer.paragraph_format.line_spacing = 1.0
        for run in spacer.runs:
            run.font.size = Pt(2)

    def _quote(self, line: str):
        maths = re.findall(r"\$([^$]+)\$", line)
        max_len = max((len(m) for m in maths), default=0)
        math_size = None
        if max_len > 160:
            math_size = 9.0
        elif max_len > 120:
            math_size = 9.8
        elif max_len > 90:
            math_size = 10.6
        elif max_len > 65:
            math_size = 11.5
        p = self._new_para("Quote Box")
        p.paragraph_format.left_indent = Cm(0.6)
        p.paragraph_format.right_indent = Cm(0.2)
        shade_paragraph(p, "F3F6FC")
        border_paragraph(p, "left", "1A73E8", 18, 8)
        add_inline(p, line, math_size=math_size)

    def _list_item(self, text: str, level: int, number: Optional[int] = None):
        p = self._new_para("Normal")
        pf = p.paragraph_format
        pf.first_line_indent = Cm(-0.4)
        pf.left_indent = Cm(0.75 + 0.6 * level)
        pf.space_before = Pt(0)
        pf.space_after = Pt(2)
        pf.line_spacing = 1.35
        pf.alignment = WD_ALIGN_PARAGRAPH.LEFT
        prefix = f"{number}. " if number is not None else "• "
        run = p.add_run(prefix)
        set_run_font(run, FONT_BODY, 13, False, False, COLOR_TEXT)
        add_inline(p, text)

    def _rule(self):
        p = self._new_para()
        p.paragraph_format.space_before = Pt(6)
        p.paragraph_format.space_after = Pt(6)
        p.paragraph_format.first_line_indent = Cm(0)
        border_paragraph(p, "bottom", "BFBFBF", 4, 1)

    def _toc(self):
        p = self._new_para()
        p.paragraph_format.first_line_indent = Cm(0)
        p.paragraph_format.space_after = Pt(6)
        add_toc(p)

    # ---- parse ---------------------------------------------------------

    def build(self, body: str, out_path: Path):
        lines = body.splitlines()
        i = 0
        buffer: List[str] = []
        n = len(lines)

        while i < n:
            raw = lines[i]
            stripped = raw.strip()

            if stripped == "":
                self._flush(buffer)
                i += 1
                continue

            if stripped.startswith("<!--") and stripped.endswith("-->"):
                if stripped == "<!-- PAGEBREAK -->":
                    self._flush(buffer)
                    self._pending_break = True
                elif stripped == "<!-- LANDSCAPE:START -->":
                    self._flush(buffer)
                    self._start_landscape()
                elif stripped == "<!-- LANDSCAPE:END -->":
                    self._flush(buffer)
                    self._end_landscape()
                elif stripped == "<!-- TOC:START -->":
                    self._flush(buffer)
                    self._toc()
                    # skip static TOC until end marker
                    i += 1
                    while i < n and lines[i].strip() != "<!-- TOC:END -->":
                        i += 1
                i += 1
                continue

            if stripped.startswith("```"):
                self._flush(buffer)
                i += 1
                code_lines = []
                while i < n and not lines[i].strip().startswith("```"):
                    code_lines.append(lines[i].rstrip("\n"))
                    i += 1
                self._code_block(code_lines)
                i += 1
                continue

            image_match = IMAGE_RE.match(stripped)
            if image_match:
                self._flush(buffer)
                self._image(image_match.group(1), image_match.group(2))
                i += 1
                continue

            heading_match = HEADING_RE.match(stripped)
            if heading_match:
                self._flush(buffer)
                self._heading(len(heading_match.group(1)), heading_match.group(2).strip())
                i += 1
                continue

            if stripped.startswith("|"):
                self._flush(buffer)
                table_lines = []
                while i < n and lines[i].strip().startswith("|"):
                    table_lines.append(lines[i].strip())
                    i += 1
                self._parse_table(table_lines)
                continue

            if stripped.startswith(">"):
                self._flush(buffer)
                quote_lines = []
                while i < n and lines[i].strip().startswith(">"):
                    quote_lines.append(lines[i].strip()[1:].strip())
                    i += 1
                for q in quote_lines:
                    if q:
                        self._quote(q)
                continue

            bullet_match = BULLET_RE.match(raw)
            if bullet_match and not stripped.startswith("**"):
                self._flush(buffer)
                indent = len(bullet_match.group(1).replace("\t", "  "))
                self._list_item(bullet_match.group(2).strip(), min(indent // 2, 3))
                i += 1
                continue

            number_match = NUMBER_RE.match(raw)
            if number_match:
                self._flush(buffer)
                indent = len(number_match.group(1).replace("\t", "  "))
                self._list_item(
                    number_match.group(3).strip(),
                    min(indent // 2, 3),
                    int(number_match.group(2)),
                )
                i += 1
                continue

            if RULE_RE.match(stripped):
                self._flush(buffer)
                self._rule()
                i += 1
                continue

            buffer.append(stripped)
            i += 1

        self._flush(buffer)
        set_update_fields(self.doc)
        set_core_properties(self.doc, self.cover_title)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        self.doc.save(str(out_path))
        return out_path

    def _parse_table(self, table_lines: List[str]):
        if not table_lines:
            return
        parsed = []
        aligns = []
        for line in table_lines:
            cells = [c.strip().replace("\\|", "|") for c in re.split(r"(?<!\\)\|", line.strip().strip("|"))]
            if all(re.match(r"^:?-{3,}:?$", c) for c in cells if c):
                aligns = []
                for c in cells:
                    if c.startswith(":") and c.endswith(":"):
                        aligns.append("center")
                    elif c.endswith(":"):
                        aligns.append("right")
                    else:
                        aligns.append("left")
                continue
            parsed.append(cells)
        if not parsed:
            return
        self._table(parsed, aligns or ["left"] * max(len(r) for r in parsed))


# ---------------------------------------------------------------------------
# Entry points
# ---------------------------------------------------------------------------

def read_body(md_path: Path) -> str:
    text = md_path.read_text(encoding="utf-8")
    if "<!-- BODY:START -->" in text:
        text = text.split("<!-- BODY:START -->", 1)[1]
    text = re.sub(r"<!-- COVER:START -->.*?<!-- COVER:END -->", "", text, flags=re.S)
    return text.strip()


def first_h1(body: str) -> str:
    for line in body.splitlines():
        m = re.match(r"^#\s+(.*)$", line.strip())
        if m:
            return m.group(1).strip()
    return "BÁO CÁO ĐỒ ÁN TỐT NGHIỆP"


def build_one(md_path: Path, out_path: Path, cover_title: str, is_excerpt=False,
              chapter_label="", header_text="", prepend_toc=False):
    body = read_body(md_path)
    if prepend_toc:
        body = ("## MỤC LỤC\n\n<!-- TOC:START -->\n<!-- TOC:END -->\n\n"
                "<!-- PAGEBREAK -->\n\n" + body)
    builder = ThesisDocx(
        md_path=md_path,
        cover_title=cover_title,
        is_excerpt=is_excerpt,
        chapter_label=chapter_label,
        header_text=header_text,
    )
    builder.build(body, out_path)
    print(f"wrote {out_path} ({out_path.stat().st_size:,} bytes)")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["combined", "chapters", "print", "all"], default="all")
    args = parser.parse_args()

    base = Path(__file__).resolve().parent.parent
    combined_md = base / "bao_cao_3_chuong.md"

    if args.mode in ("combined", "all"):
        build_one(
            combined_md,
            base / "bao_cao_3_chuong.docx",
            cover_title="XÂY DỰNG NỀN TẢNG QUẢN LÝ TRI THỨC DOANH NGHIỆP ỨNG DỤNG HỌC SÂU VÀ TRUY XUẤT TĂNG CƯỜNG",
            header_text="BÁO CÁO ĐỒ ÁN TỐT NGHIỆP — EAKWP",
        )

    if args.mode in ("print", "all"):
        build_one(
            base / "in_chuong_3_4.md",
            base / "in_chuong_3_4.docx",
            cover_title="XÂY DỰNG NỀN TẢNG QUẢN LÝ TRI THỨC DOANH NGHIỆP ỨNG DỤNG HỌC SÂU VÀ TRUY XUẤT TĂNG CƯỜNG",
            header_text="BẢN IN CHƯƠNG 3-4 - EAKWP",
            prepend_toc=True,
        )

    if args.mode in ("chapters", "all"):
        chapters = [
            ("chuong_2_hoc_sau.md", "chuong_2_hoc_sau.docx", "CHƯƠNG 2"),
            ("chuong_3_co_so_du_lieu.md", "chuong_3_co_so_du_lieu.docx", "CHƯƠNG 3"),
            ("chuong_4_co_so_tri_thuc.md", "chuong_4_co_so_tri_thuc.docx", "CHƯƠNG 4"),
        ]
        for md_name, docx_name, label in chapters:
            md_path = base / md_name
            body = read_body(md_path)
            title = first_h1(body)
            build_one(
                md_path,
                base / docx_name,
                cover_title=title,
                is_excerpt=True,
                chapter_label=label,
                header_text=f"BẢN TRÍCH {label} — EAKWP",
                prepend_toc=True,
            )


if __name__ == "__main__":
    sys.exit(main())
