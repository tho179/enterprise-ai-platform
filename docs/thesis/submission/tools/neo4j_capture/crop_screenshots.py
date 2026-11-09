from PIL import Image
src = r"C:\Users\Admin\AppData\Local\Temp\claude\c--enterprise-ai-platform\f4690344-b7a4-4fe4-8ea0-edd230506874\scratchpad\nb"; dst = r"C:\enterprise-ai-platform\docs\thesis\submission\assets\neo4j"
for n in ("neo4j_kb_tong_quan", "neo4j_tai_lieu_hdqt", "neo4j_schema"):
    im = Image.open(f"{src}\\{n}.png").convert("RGB")
    im.crop((500, 90, im.width, 940)).save(f"{dst}\\{n}.png", optimize=True)
im = Image.open(f"{src}\\neo4j_thong_ke.png").convert("RGB"); im.crop((0, 40, im.width, 760)).save(f"{dst}\\neo4j_thong_ke.png", optimize=True)
