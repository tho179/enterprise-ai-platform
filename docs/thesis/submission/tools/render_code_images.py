"""Render fenced code blocks as screenshots of the tool they belong to.

python / json -> VS Code (Dark+ theme), commands -> VS Code PowerShell terminal,
cypher -> the editor of the Neo4j Browser running on localhost:7474.
No notebook is used anywhere in the project, so no Jupyter-style cell is produced.
"""
from __future__ import annotations

import html
import re
from pathlib import Path

from playwright.sync_api import sync_playwright
from pygments import lex
from pygments.lexers import JsonLexer, PythonLexer
from pygments.token import Comment, Name, Number, Operator, Punctuation, String

PX_TO_CM = 0.0226  # 14px editor font prints at about 9pt
CHAR_W = 7.7
FENCE = re.compile(r"^```(\w*)\n(.*?)^```[ \t]*$", re.S | re.M)

FILES = [  # (first-line marker, tab name, breadcrumb path)
    ("model = SentenceTransformer", "benchmark_embeddings.py", "ai-service › scripts"),
    ("def embed_query", "embedding_service.py", "ai-service › app"),
    ("def rerank(", "reranker_service.py", "ai-service › app"),
    ("def document_id", "ids.py", "ai-service › app › knowledge_graph"),
    ("def build_pdf_record", "extract.py", "ai-service › app › knowledge_graph"),
    ("def load_pdf", "pipeline.py", "ai-service › app › knowledge_graph"),
    ("def fetch_html", "extract.py", "ai-service › app › knowledge_graph"),
    ("def load_links", "pipeline.py", "ai-service › app › knowledge_graph"),
    ("def merge(", "pipeline.py", "ai-service › app › knowledge_graph"),
    ("def plan_update", "pipeline.py", "ai-service › app › knowledge_graph"),
    ("vector_hits", "rag_service.py", "ai-service › app"),
    ("if vector_hits", "rag_service.py", "ai-service › app"),
]
JSON_NAMES = ["request.json", "response.json", "refusal.json"]

FLOW = {"if", "elif", "else", "for", "while", "return", "import", "from", "try", "except", "finally",
        "with", "as", "raise", "yield", "pass", "break", "continue", "assert", "del", "await"}
DECL = {"def", "class", "lambda", "global", "nonlocal", "async", "and", "or", "not", "in", "is",
        "True", "False", "None", "self"}
TYPES = {"str", "int", "float", "bool", "list", "dict", "set", "tuple", "bytes", "object", "Exception"}


def py_color(ttype, val, nxt):
    if ttype in Comment:
        return "#6a9955"
    if ttype in String:
        return "#ce9178"
    if ttype in Number:
        return "#b5cea8"
    if val in FLOW:
        return "#c586c0"
    if val in DECL:
        return "#569cd6"
    if ttype in Name.Function:
        return "#dcdcaa"
    if ttype in Name.Class:
        return "#4ec9b0"
    if ttype in Name.Builtin:
        return "#4ec9b0" if val in TYPES else "#dcdcaa"
    if ttype in Name:
        if nxt == "(":
            return "#4ec9b0" if val[:1].isupper() else "#dcdcaa"
        if val.isupper() and len(val) > 1:
            return "#4fc1ff"
        if val[:1].isupper():
            return "#4ec9b0"
        return "#9cdcfe"
    return "#d4d4d4"


def json_color(ttype, val, nxt):
    if ttype in String:
        return "#9cdcfe" if nxt == ":" else "#ce9178"
    if ttype in Number:
        return "#b5cea8"
    if val in ("true", "false", "null"):
        return "#569cd6"
    return "#d4d4d4"


def colorize(code: str, lexer, color_fn) -> list[str]:
    toks = [(t, v) for t, v in lex(code, lexer)]
    lines, cur = [], ""
    for i, (t, v) in enumerate(toks):
        nxt = next((x[1].strip() for x in toks[i + 1:] if x[1].strip()), "")
        color = color_fn(t, v, nxt[:1] if v.strip().isidentifier() or t in String else nxt)
        parts = v.split("\n")
        for j, part in enumerate(parts):
            if j:
                lines.append(cur); cur = ""
            if part:
                cur += f'<span style="color:{color}">{html.escape(part)}</span>'
    lines.append(cur)
    while lines and not re.sub("<[^>]+>", "", lines[-1]).strip():
        lines.pop()
    return lines


CSS = """
body{margin:0;background:#fff}
.win{display:inline-block;background:#1e1e1e;font-family:'Segoe UI',Arial,sans-serif;color:#ccc}
.tabs{background:#252526;height:35px;display:flex}
.tab{background:#1e1e1e;padding:0 16px;display:flex;align-items:center;gap:8px;font-size:13px;color:#fff;border-top:1px solid #0078d4}
.crumb{padding:3px 20px;font-size:12px;color:#a9a9a9;background:#1e1e1e}
pre{margin:0;padding:8px 20px 14px 0;font-family:Consolas,'Courier New',monospace;font-size:14px;line-height:19px}
.ln{display:inline-block;width:46px;text-align:right;color:#858585;margin-right:22px;user-select:none}
.panel{display:flex;gap:22px;padding:7px 20px 6px;font-size:11px;color:#e7e7e7;background:#1e1e1e;border-bottom:1px solid #333}
.panel .on{border-bottom:1px solid #e7e7e7;padding-bottom:4px}.panel .off{color:#999}
.term{padding:10px 20px 14px;font-family:Consolas,'Courier New',monospace;font-size:14px;line-height:19px;white-space:pre-wrap;word-break:break-all;color:#ccc}
"""

ICON_PY = '<svg width="15" height="15" viewBox="0 0 16 16"><path d="M8 1c-3 0-3 1.3-3 2.2V5h3.1v.6H3.8C2.4 5.6 1.5 6.6 1.5 8.3s.8 2.7 2.2 2.7H5V9.5C5 8.5 5.8 7.7 6.8 7.7h3c.9 0 1.5-.7 1.5-1.6V3.2C11.3 2 10 1 8 1z" fill="#3a7ebb"/><path d="M8 15c3 0 3-1.3 3-2.2V11H7.9v-.6h4.3c1.4 0 2.3-1 2.3-2.7S13.700 5 12.300 5H11v1.500c0 1-.8 1.800-1.800 1.800h-3c-.9 0-1.500.7-1.500 1.600v2.900C4.700 14 6 15 8 15z" fill="#fdd835"/></svg>'
ICON_JSON = '<span style="color:#cbcb41;font-size:12px;font-weight:bold">{}</span>'


def vscode_editor(code, name, crumb, lexer, color_fn):
    lines = colorize(code.rstrip("\n"), lexer, color_fn)
    chars = max(len(re.sub("<[^>]+>", "", html.unescape(x))) for x in lines)
    width = max(520, int(46 + 22 + chars * CHAR_W + 40))
    body = "\n".join(f'<span class="ln">{i}</span>{ln}' for i, ln in enumerate(lines, 1))
    icon = ICON_PY if name.endswith(".py") else ICON_JSON
    crumb_html = f'<div class="crumb">{html.escape(crumb)} › {html.escape(name)}</div>' if crumb else ""
    page = (f"<style>{CSS}</style><div class='win' style='width:{width}px'><div class='tabs'>"
            f"<div class='tab'>{icon}{html.escape(name)}</div></div>{crumb_html}<pre>{body}</pre></div>")
    return page, width


def terminal(code: str):
    out = []
    for line in code.rstrip("\n").splitlines():
        if line.startswith("python "):
            toks = line.split(" ")
            row = '<span style="color:#ccc">PS C:\\enterprise-ai-platform\\ai-service&gt; </span>'
            row += f'<span style="color:#e5e510">{html.escape(toks[0])}</span>'
            for t in toks[1:]:
                col = "#9a9a9a" if t.startswith("-") else "#ccc"
                row += f' <span style="color:{col}">{html.escape(t)}</span>'
            out.append(row)
        else:
            out.append(html.escape(line))
    chars = min(100, max(len(re.sub("<[^>]+>", "", html.unescape(x))) for x in out))
    width = max(520, int(chars * CHAR_W + 60))
    page = (f"<style>{CSS}</style><div class='win' style='width:{width}px'><div class='panel'>"
            "<span class='off'>PROBLEMS</span><span class='off'>OUTPUT</span><span class='off'>DEBUG CONSOLE</span>"
            "<span class='on'>TERMINAL</span><span class='off'>PORTS</span></div>"
            f"<div class='term'>{chr(10).join(out)}</div></div>")
    return page, width


def pick_python_file(code: str):
    first = code.lstrip().splitlines()[0]
    for marker, name, crumb in FILES:
        if marker in first or (marker in code[:200] and marker.startswith("vector_hits")):
            return name, crumb
    return "module.py", "ai-service › app"


def render(body: str, outdir: Path) -> str:
    outdir.mkdir(parents=True, exist_ok=True)
    jobs, counter = [], {"n": 0, "json": 0}

    def repl(m):
        lang, code = m.group(1), m.group(2)
        if lang not in ("python", "json", "cypher") and not (
                lang == "text" and all(l.startswith("python ") or not l.strip() or l.startswith(("Ran ", "OK", "-----"))
                                       for l in code.splitlines())):
            return m.group(0)
        counter["n"] += 1
        n = counter["n"]
        pieces = [code]
        if lang == "python" and "def build_pdf_record" in code and "def load_pdf" in code:
            head, tail = code.split("def load_pdf", 1)
            pieces = [head.rstrip() + "\n", "def load_pdf" + tail]
        tags = []
        for k, piece in enumerate(pieces):
            png = outdir / f"code{n:02d}{'abc'[k] if len(pieces) > 1 else ''}.png"
            jobs.append((lang, piece, png))
            tags.append(f"![code](assets/code/{png.name})")
        return "\n\n".join(tags)

    new_body = FENCE.sub(repl, body)
    widths = {}
    with sync_playwright() as p:
        b = p.chromium.launch(channel="msedge", headless=True)
        pg = b.new_page(viewport={"width": 1200, "height": 900}, device_scale_factor=2)
        neo = None
        for lang, code, png in jobs:
            if lang == "python":
                name, crumb = pick_python_file(code)
                page, w = vscode_editor(code, name, crumb, PythonLexer(), py_color)
            elif lang == "json":
                name = JSON_NAMES[counter["json"] % 3]; counter["json"] += 1
                page, w = vscode_editor(code, name, "", JsonLexer(), json_color)
            elif lang == "text":
                page, w = terminal(code)
            else:
                if neo is None:
                    neo = b.new_page(viewport={"width": 1500, "height": 950}, device_scale_factor=2)
                    neo.goto("http://localhost:7474/browser/", wait_until="domcontentloaded")
                    neo.wait_for_selector("input[type=password]")
                    neo.fill("input[type=password]", "eakwp-neo4j"); neo.press("input[type=password]", "Enter")
                    neo.wait_for_timeout(4000)
                    if neo.locator("text=Dismiss").count():
                        neo.locator("text=Dismiss").first.click()
                ed = neo.locator(".cm-content").first
                ed.click(); neo.keyboard.press("Control+A"); neo.keyboard.press("Delete")
                neo.keyboard.insert_text(code.rstrip("\n")); neo.keyboard.press("Escape")
                neo.wait_for_timeout(700)
                neo.locator(".cm-editor").first.screenshot(path=str(png))
                trim_right(png)
                widths[png.name] = image_width(png)
                continue
            pg.set_content(page)
            pg.locator(".win").screenshot(path=str(png))
            widths[png.name] = w
        b.close()
    for name, w in widths.items():
        new_body = new_body.replace(f"![code](assets/code/{name})", f"![code|{w}](assets/code/{name})")
    return new_body


def image_width(png: Path) -> int:
    from PIL import Image
    return Image.open(png).width // 2


def trim_right(png: Path, pad=36):
    from PIL import Image, ImageChops
    im = Image.open(png).convert("RGB")
    bg = Image.new("RGB", im.size, (255, 255, 255))
    box = ImageChops.difference(im, bg).getbbox()
    right = min(im.width, (box[2] + pad * 2) if box else im.width)
    im.crop((0, 0, right, im.height)).save(png, optimize=True)
