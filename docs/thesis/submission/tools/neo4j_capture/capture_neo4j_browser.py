import sys
from playwright.sync_api import sync_playwright
OUT = sys.argv[1]
S = 1.25

def run(pg, q, wait=6500):
    ed = pg.locator(".cm-content").first
    ed.click(); pg.keyboard.press("Control+A"); pg.keyboard.press("Delete")
    pg.keyboard.insert_text(q); pg.keyboard.press("Control+Enter")
    pg.wait_for_timeout(wait)
    pg.keyboard.press("Escape")

def style(pg, chip, caption=None, size_off=None, color_off=None):
    pg.locator(f"text={chip}").first.click()
    pg.wait_for_timeout(800)
    h = pg.locator("text=Customize Style").bounding_box()
    hx, hy = h["x"], h["y"] + h["height"]/2
    if color_off is not None:
        pg.mouse.click(hx + (color_off - 1423)/S, hy + (520 - 455)/S)
    if size_off is not None:
        pg.mouse.click(hx + (size_off - 1423)/S, hy + (630 - 455)/S)
    if caption:
        pg.get_by_text(caption, exact=True).last.click()
    pg.wait_for_timeout(600)
    pg.keyboard.press("Escape")
    pg.mouse.click(300, 700)  # neutral area to close panel
    pg.wait_for_timeout(500)

with sync_playwright() as p:
    b = p.chromium.launch(channel="msedge", headless=True)
    pg = b.new_page(viewport={"width":1600,"height":950}, device_scale_factor=S)
    pg.goto("http://localhost:7474/browser/", wait_until="domcontentloaded", timeout=60000)
    pg.wait_for_selector("input[type=password]", timeout=60000)
    pg.fill("input[type=password]", "eakwp-neo4j"); pg.press("input[type=password]", "Enter")
    pg.wait_for_timeout(5000)
    if pg.locator("text=Dismiss").count(): pg.locator("text=Dismiss").first.click()
    def fit():
        pg.get_by_role("button", name="Zoom to fit").first.click(); pg.mouse.move(250, 800); pg.wait_for_timeout(1800)

    run(pg, ":clear", 1500)
    run(pg, "MATCH p=(kb:KnowledgeBase)-[:HAS_DOCUMENT]->(d:Document) RETURN p")
    style(pg, "KnowledgeBase (3)", caption="kb_id", size_off=1856, color_off=1516)
    style(pg, "Document (45)", color_off=1671, size_off=1595)
    fit(); pg.screenshot(path=f"{OUT}\\neo4j_kb_tong_quan.png")

    run(pg, ":clear", 1500)
    run(pg, "MATCH p=(d:Document)-[:HAS_CHUNK]->(c:Chunk)-[:MENTIONS]->(e:Entity) WHERE d.source_uri CONTAINS 'HDQT' AND c.chunk_index >= 28 AND c.chunk_index <= 33 RETURN p")
    style(pg, "Document (1)", caption="title", size_off=1856)
    style(pg, "Chunk (6)", caption="chunk_index", size_off=1796)
    style(pg, "Entity (6)", caption="name", size_off=1796)
    fit(); pg.screenshot(path=f"{OUT}\\neo4j_tai_lieu_hdqt.png")

    run(pg, ":clear", 1500)
    run(pg, "CALL db.schema.visualization()")
    for chip in ("Chunk (1)", "Document (1)", "Entity (1)", "KnowledgeBase (1)"):
        style(pg, chip, caption="name", size_off=1856)
    fit(); pg.screenshot(path=f"{OUT}\\neo4j_schema.png")

    run(pg, ":clear", 1500)
    pg.get_by_label("Database overview").first.click(); pg.wait_for_timeout(1500)
    run(pg, "MATCH (n) RETURN labels(n)[0] AS nhan, count(*) AS so_luong ORDER BY so_luong DESC")
    pg.get_by_text("Table", exact=True).first.click(); pg.wait_for_timeout(1500); pg.mouse.move(250, 900)
    pg.screenshot(path=f"{OUT}\\neo4j_thong_ke.png")
    b.close()



