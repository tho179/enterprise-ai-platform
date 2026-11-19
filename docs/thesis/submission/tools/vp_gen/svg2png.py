"""Render Visual Paradigm SVG exports to high-resolution PNG with a real browser
(VP's own PDF export drops Vietnamese glyphs; its PNG export is 1:1 only)."""
import re, sys
from pathlib import Path
from playwright.sync_api import sync_playwright

src, dst = Path(sys.argv[1]), Path(sys.argv[2])
dst.mkdir(exist_ok=True)
TARGET = int(__import__("os").environ.get("SVG_TARGET_PX", "3400"))
with sync_playwright() as p:
    b = p.chromium.launch(channel="msedge", headless=True)
    for svg in sorted(src.glob("*.svg")):
        text = svg.read_text(encoding="utf-8")
        m = re.search(r'<svg[^>]*\bwidth="([\d.]+)[^"]*"[^>]*\bheight="([\d.]+)', text) or \
            re.search(r'<svg[^>]*\bheight="([\d.]+)[^"]*"[^>]*\bwidth="([\d.]+)', text)
        w, h = float(m.group(1)), float(m.group(2))
        if 'height="' in m.group(0)[:m.group(0).find('width="')]:
            w, h = h, w
        scale = max(2.5, TARGET / w)
        page = b.new_page(viewport={"width": int(w) + 20, "height": int(h) + 20}, device_scale_factor=scale)
        body = re.sub(r"<\?xml[^>]*>|<!DOCTYPE[^>]*>", "", text)
        page.set_content("<html><head><style>html,body{margin:0;background:#fff}"
                         "svg text{font-family:Arial,'Segoe UI',sans-serif !important}</style></head>"
                         f"<body>{body}</body></html>")
        page.locator("svg").first.screenshot(path=str(dst / (svg.stem + ".png")))
        page.close()
        print(svg.stem, int(w), int(h), f"x{scale:.1f}")
    b.close()
