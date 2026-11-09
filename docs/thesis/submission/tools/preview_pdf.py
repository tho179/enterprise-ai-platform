import sys
from pathlib import Path
import fitz

pdf = Path(sys.argv[1]).resolve()
out_dir = Path(sys.argv[2]).resolve()
out_dir.mkdir(parents=True, exist_ok=True)

doc = fitz.open(str(pdf))
print("pages:", doc.page_count)
for i, page in enumerate(doc):
    text = page.get_text().strip().replace("\n", " ")
    print(f"p{i+1}: {text[:150]}")

pages = [int(x) for x in sys.argv[3].split(",")] if len(sys.argv) > 3 else list(range(1, min(doc.page_count, 12) + 1))
for p in pages:
    if 1 <= p <= doc.page_count:
        page = doc[p - 1]
        pix = page.get_pixmap(dpi=110)
        path = out_dir / f"page_{p:03d}.png"
        pix.save(str(path))
        print("saved", path)
