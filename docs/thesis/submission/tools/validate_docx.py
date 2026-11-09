from pathlib import Path
from docx import Document

for name in ["bao_cao_3_chuong.docx", "chuong_2_hoc_sau.docx", "chuong_3_co_so_du_lieu.docx", "chuong_4_co_so_tri_thuc.docx"]:
    p = Path("docs/thesis/submission") / name
    doc = Document(str(p))
    paragraphs = len(doc.paragraphs)
    tables = len(doc.tables)
    images = len(doc.inline_shapes)
    sections = len(doc.sections)
    text = "\n".join(x.text for x in doc.paragraphs)
    print(f"{name}: paras={paragraphs}, tables={tables}, images={images}, sections={sections}, chars={len(text):,}")
    print("  headings:", sum(1 for x in doc.paragraphs if x.style.name.startswith("Heading")))
    print("  toc field:", "TOC" in doc.element.xml)
    print("  first paras:", [x.text[:50] for x in doc.paragraphs[:4]])
