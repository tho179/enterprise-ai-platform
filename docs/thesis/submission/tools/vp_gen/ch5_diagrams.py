"""Chapter 5 diagrams: agent architecture and agent loop (follows ai-service/app/agent/*)."""
import sys

sys.path.insert(0, ".")
from vpgen import Project, Shape  # noqa: E402

p = Project()


def note(d, text, x, y, w, h):
    return d.add(Shape(p.el("NOTE", text), x, y, w, h))


# H5.1 agent architecture ----------------------------------------------------
d = p.diagram("H5_1_kien_truc_tac_tu", "ComponentDiagram")
C = {}


def comp(key, label, x, y, w=230, h=64):
    C[key] = d.add(Shape(p.el("Component", label), x, y, w, h))


comp("api", "POST /api/v1/chat/ask (chat.py)", 10, 260, 230)
comp("per", "Nhận thức: perception.py", 10, 20, 230)
comp("rules", "Chính sách: rules.py (9 luật)", 320, 150, 230)
comp("loop", "Vòng lặp: agent.py (tối đa 4 bước)", 320, 260, 230)
comp("kb", "Công cụ kb_attribute", 640, 20, 220)
comp("flat", "Công cụ retrieve:flat_rag", 640, 110, 220)
comp("hyb", "Công cụ retrieve:hybrid_rag", 640, 200, 220)
comp("ref", "Công cụ refuse", 640, 290, 220)
comp("neo", "Neo4j: nút Claim, đồ thị", 950, 40, 220)
comp("qd", "Qdrant + cross-encoder", 950, 160, 220)
comp("llm", "LLM (tùy chọn)", 950, 270, 220)


def dep(a, b, label=""):
    d.connect(p.rel("Dependency", C[a].el, C[b].el, label), C[a], C[b])


dep("api", "loop", "ask(query, user_roles)")
dep("loop", "per", "")
dep("loop", "rules", "match(observation, state)")
dep("loop", "kb", "")
dep("loop", "flat", "")
dep("loop", "hyb", "")
dep("loop", "ref", "")
dep("kb", "neo", "ATTRIBUTE_VALUES")
dep("flat", "qd", "")
dep("hyb", "qd", "")
dep("hyb", "neo", "graph_search")
dep("hyb", "llm", "")
note(d, "Mỗi bước ghi một dòng vào agent_trace: luật, hành động, kết quả quan sát, thời gian. Cờ AGENT_ENABLED=false bỏ qua tác tử, gọi thẳng RAGService.", 10, 380, 860, 40)

# H5.2 agent loop ------------------------------------------------------------
d = p.diagram("H5_2_vong_lap_tac_tu", "ActivityDiagram")
N = {}


def node(key, kind, label, x, y, w=250, h=44, cap=None):
    N[key] = d.add(Shape(p.el(kind, label), x, y, w, h, caption=cap))


node("start", "InitialNode", "", 255, 10, 20, 20, cap=(285, 10, 10, 10))
node("per", "ActivityAction", "Nhận thức: dạng câu, số điều, thuộc tính, thực thể", 120, 60, 290)
node("match", "ActivityAction", "Chọn luật đầu tiên có điều kiện đúng", 140, 140)
node("dec", "DecisionNode", "", 245, 220, 40, 40, cap=(295, 226, 10, 10))
node("kb", "ActivityAction", "kb_attribute: đọc Claim đã chấp nhận", 10, 300)
node("ret", "ActivityAction", "retrieve: truy xuất, chấm lại, cổng bằng chứng", 290, 300, 280)
node("obs", "ActivityAction", "Quan sát: tìm thấy? qua cổng? ghi agent_trace", 140, 390, 260)
node("out", "ActivityAction", "Trả lời có trích dẫn hoặc từ chối", 140, 480)
node("end", "ActivityFinalNode", "", 253, 560, 24, 24, cap=(283, 562, 10, 10))


def flow(a, b, label="", pts=None):
    d.connect(p.rel("ControlFlow", N[a].el, N[b].el, label), N[a], N[b], points=pts)


flow("start", "per")
flow("per", "match")
flow("match", "dec")
flow("dec", "kb", "[R3]")
flow("dec", "ret", "[R5-R8]")
flow("kb", "obs")
flow("ret", "obs")
d.connect(p.rel("ControlFlow", N["obs"].el, N["match"].el, "[bước < 4]"), N["obs"], N["match"], points=[(400, 412), (600, 412), (600, 162), (390, 162)], label_xy=(606, 280))
d.connect(p.rel("ControlFlow", N["dec"].el, N["out"].el, "[R1, R2, R4, R9]"), N["dec"], N["out"], points=[(245, 240), (110, 240), (110, 502), (140, 502)], label_xy=(8, 440))
flow("out", "end")

open("ch5.xml", "w", encoding="utf-8").write(p.xml())
print("diagrams:", [x.name for x in p.diagrams])
