import shutil
import sys
from pathlib import Path

import win32com.client
from docx import Document
from docx.oxml.ns import qn

src = Path(sys.argv[1]).resolve()
dst = src.with_suffix(".pdf")
tmp = src.with_name(src.stem + "_export.docx")

# Word's automatic field update on open can hang on large TOCs. Remove the
# flag, update only the TOC field in a temp copy, then copy the clean result back.
shutil.copy2(src, tmp)
docx = Document(str(tmp))
settings = docx.settings.element
for el in settings.findall(qn("w:updateFields")):
    settings.remove(el)
docx.save(str(tmp))

word = None
doc = None
try:
    word = win32com.client.DispatchEx("Word.Application")
    word.Visible = False
    word.DisplayAlerts = 0
    word.Options.UpdateLinksAtOpen = False
    word.Options.ConfirmConversions = False
    doc = word.Documents.Open(str(tmp), ReadOnly=False, AddToRecentFiles=False)

    def update_toc():
        for field in doc.Fields:
            if field.Type == 13:  # wdFieldTOC
                field.Update()

    # First update creates the TOC1/TOC2 styles. Compact them, then update
    # again so Word recomputes page numbers against the final one-page TOC.
    update_toc()
    for i in range(1, doc.Styles.Count + 1):
        style = doc.Styles.Item(i)
        try:
            name = style.NameLocal.lower()
        except Exception:
            continue
        if name in ("toc 1", "toc 2") or name.startswith("mục lục "):
            style.ParagraphFormat.SpaceBefore = 0
            style.ParagraphFormat.SpaceAfter = 2
            style.ParagraphFormat.LineSpacingRule = 0  # wdLineSpaceSingle
    doc.Repaginate()
    update_toc()
    doc.Repaginate()
    doc.Save()
    doc.ExportAsFixedFormat(str(dst), 17)  # wdExportFormatPDF
    doc.Close(SaveChanges=0)
    doc = None
finally:
    if doc is not None:
        try:
            doc.Close(SaveChanges=0)
        except Exception:
            pass
    if word is not None:
        try:
            word.Quit()
        except Exception:
            pass

shutil.copy2(tmp, src)
tmp.unlink()
print(f"exported {dst} ({dst.stat().st_size:,} bytes)")
