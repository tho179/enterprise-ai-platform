"""Additional Chapter 2 analysis/design diagrams, generated for Visual Paradigm.

Activity diagrams with swimlanes, state machines, deployment, packages and the
NoSQL storage design (orange). Every label follows the code (see comments).

    python ch2_extra.py <out.xml>
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from vpgen import BLUE, ORANGE, WHITE, Element, Project, Shape, new_id, q  # noqa: E402

p = Project()


def _sarr(name, ids):
    return (f'<StringArrayProperty displayName="{name}" name="{name}">'
            + "".join(f"<Value value={q(i)}/>" for i in ids) + "</StringArrayProperty>")


def _refs(name, els):
    return (f'\n\t\t\t\t<ModelRefsProperty displayName="{name}" name="{name}">'
            + "".join(f"<ModelRef id={q(e.id)}/>" for e in els) + "</ModelRefsProperty>")


def _sp(name, value):
    return f'\n\t\t\t\t<StringProperty displayName="{name}" name="{name}" value={q(value)}/>'


# ---------------------------------------------------------------------------
# activity diagrams with swimlanes
# ---------------------------------------------------------------------------
HEAD, ROW, TOP = 34, 84, 10


def swimlane_activity(name, lanes, nodes, flows):
    """lanes: [(title, width)]; nodes: key -> (kind, label, lane, frac, row[, width]);
    flows: (a, b, guard[, points])."""
    d = p.diagram(name, "ActivityDiagram")
    rows = max(n[4] for n in nodes.values()) + 1
    height = HEAD + rows * ROW + 30
    xs = [10]
    for _, w in lanes:
        xs.append(xs[-1] + w)
    sw = Element("ActivitySwimlane2", "", None)
    p.elements.append(sw)
    parts = [Element("ActivityPartition", t, sw) for t, _ in lanes]
    sw.extra = _refs("verticalPartitions", parts)
    heads = [Shape(pt, xs[i], TOP, w, HEAD, shape_type="ActivityPartitionHeader")
             for i, (pt, (_, w)) in enumerate(zip(parts, lanes))]
    comps = [Shape(sw, xs[i], TOP + HEAD, w, height - HEAD, shape_type="ActivitySwimlane2Compartment", fill=WHITE)
             for i, (_, w) in enumerate(lanes)]
    SW = Shape(sw, xs[0], TOP, xs[-1] - xs[0], height, fill=WHITE,
               extra=_sarr("verticalPartitionIds", [h.id for h in heads]) + _sarr("compartmentIds", [c.id for c in comps]))
    d.add(SW)
    for h in heads:
        d.add(h, SW)
    for c in comps:
        d.add(c, SW)
    S = {}

    def put(shape, lane):
        # nodes live inside their lane's compartment, as VP models them
        return d.add(shape, comps[lane])
    for key, spec in nodes.items():
        kind, label, lane, frac, row = spec[:5]
        lw = lanes[lane][1]
        cx = xs[lane] + frac * lw
        cy = TOP + HEAD + 26 + row * ROW
        if kind == "action":
            w = spec[5] if len(spec) > 5 else min(lw - 24, 210)
            S[key] = put(Shape(p.el("ActivityAction", label), cx - w / 2, cy - 24, w, 48), lane)
        elif kind == "decision":
            S[key] = put(Shape(p.el("DecisionNode", ""), cx - 20, cy - 20, 40, 40, caption=(cx + 30, cy - 5, 10, 10)), lane)
        elif kind == "initial":
            S[key] = put(Shape(p.el("InitialNode", ""), cx - 10, cy - 10, 20, 20, caption=(cx + 20, cy - 10, 10, 10)), lane)
        elif kind == "final":
            S[key] = put(Shape(p.el("ActivityFinalNode", ""), cx - 12, cy - 12, 24, 24, caption=(cx + 20, cy - 10, 10, 10)), lane)
    for f in flows:
        a, b, guard = f[:3]
        pts = f[3] if len(f) > 3 else None
        d.connect(p.rel("ControlFlow", S[a].el, S[b].el, guard), S[a], S[b], points=pts)
    return d


# H2.x Đăng nhập (LoginPage -> AuthController.login -> AuthService.login)
swimlane_activity("HD_dang_nhap", [("Người dùng", 230), ("Frontend", 290), ("Backend", 470)], {
    "s": ("initial", "", 0, .5, 0),
    "a1": ("action", "Nhập email, mật khẩu", 0, .5, 1),
    "a2": ("action", "Gửi POST /api/auth/login", 1, .5, 1),
    "a3": ("action", "Tìm người dùng theo email", 2, .7, 1, 220),
    "d1": ("decision", "", 2, .7, 2),
    "a4": ("action", "So khớp mật khẩu (BCrypt)", 2, .7, 3, 220),
    "d2": ("decision", "", 2, .7, 4),
    "d3": ("decision", "", 2, .7, 5),
    "a5": ("action", "Cấp JWT (hạn 1 giờ)", 2, .7, 6, 220),
    "e401": ("action", "Trả 401 UNAUTHORIZED", 2, .2, 3, 160),
    "e403": ("action", "Trả 403 FORBIDDEN", 2, .2, 5, 160),
    "f1": ("action", "Hiển thị thông báo lỗi", 1, .5, 4),
    "f2": ("action", "Lưu phiên, chuyển trang theo vai trò", 1, .5, 6, 250),
    "x1": ("final", "", 1, .5, 5),
    "x2": ("final", "", 1, .5, 7),
}, [("s", "a1", ""), ("a1", "a2", ""), ("a2", "a3", ""), ("a3", "d1", ""),
    ("d1", "a4", "[có email]"), ("d1", "e401", "[không có]"), ("a4", "d2", ""),
    ("d2", "e401", "[sai]"), ("d2", "d3", "[đúng]"), ("d3", "e403", "[bị khóa]"), ("d3", "a5", "[hoạt động]"),
    ("e401", "f1", ""), ("e403", "f1", ""), ("f1", "x1", ""), ("a5", "f2", ""), ("f2", "x2", "")])

# Quản lý người dùng (UserController / UserService; POST & PATCH need ADMIN)
swimlane_activity("HD_quan_ly_nguoi_dung", [("Quản trị viên", 240), ("Frontend", 290), ("Backend", 470)], {
    "s": ("initial", "", 0, .5, 0),
    "a1": ("action", "Mở trang Người dùng", 0, .5, 1),
    "a2": ("action", "GET /api/users (20 dòng, mới nhất trước)", 1, .5, 1, 260),
    "a3": ("action", "Đọc trang users", 2, .7, 1, 200),
    "a4": ("action", "Hiển thị bảng người dùng", 1, .5, 2),
    "a5": ("action", "Chọn tạo tài khoản, đổi vai trò hoặc khóa / mở khóa", 0, .5, 3, 210),
    "a6": ("action", "POST /api/users hoặc PATCH /{id}/role, /{id}/status", 1, .5, 3, 270),
    "d1": ("decision", "", 2, .7, 3),
    "e403": ("action", "Trả 403 (không phải ADMIN)", 2, .25, 2, 180),
    "d2": ("decision", "", 2, .7, 4),
    "e4xx": ("action", "Trả 409 email trùng / 400 vai trò sai", 2, .25, 4, 190),
    "a7": ("action", "Lưu users (mật khẩu BCrypt khi tạo)", 2, .7, 5, 220),
    "a8": ("action", "Báo lỗi", 1, .5, 5, 160),
    "a9": ("action", "Cập nhật bảng", 1, .5, 6, 180),
    "x1": ("final", "", 1, .1, 5),
    "x2": ("final", "", 1, .5, 7),
}, [("s", "a1", ""), ("a1", "a2", ""), ("a2", "a3", ""), ("a3", "a4", ""), ("a4", "a5", ""), ("a5", "a6", ""),
    ("a6", "d1", ""), ("d1", "e403", "[không phải ADMIN]"), ("d1", "d2", "[ADMIN]"),
    ("d2", "e4xx", "[không hợp lệ]"), ("d2", "a7", "[hợp lệ]"), ("e403", "a8", ""), ("e4xx", "a8", ""),
    ("a8", "x1", ""), ("a7", "a9", ""), ("a9", "x2", "")])

# Tải lên và nạp tài liệu (UploadPage -> DocumentService.upload -> IngestionService.process @Async)
swimlane_activity("HD_tai_len_nap", [("Quản trị viên", 220), ("Frontend", 420), ("Backend", 470), ("ai-service", 250)], {
    "s": ("initial", "", 0, .5, 0),
    "a1": ("action", "Chọn PDF, nhập mã, tiêu đề, danh mục, quyền", 0, .5, 1, 200),
    "d0": ("decision", "", 1, .3, 1),
    "a2": ("action", "POST /api/documents/upload", 1, .3, 2, 180),
    "d1": ("decision", "", 2, .7, 2),
    "a3": ("action", "Lưu tệp, tính SHA-256", 2, .7, 3, 220),
    "a4": ("action", "Tạo phiên bản PROCESSING và nhiệm vụ nạp", 2, .7, 4, 250),
    "a5": ("action", "Trả 202 ACCEPTED {taskId}", 2, .25, 5, 190),
    "a6": ("action", "Hỏi trạng thái mỗi 1,4 giây", 1, .5, 5, 230),
    "b1": ("action", "Trích xuất văn bản, OCR, chia đoạn", 3, .5, 5, 210),
    "d2": ("decision", "", 3, .5, 6),
    "b2": ("action", "Trích xuất bằng PDFBox", 2, .7, 6, 220),
    "a7": ("action", "Lưu document_chunks", 2, .7, 7, 220),
    "b3": ("action", "Tạo embedding, ghi Qdrant, đồng bộ KB", 3, .5, 8, 210),
    "d3": ("decision", "", 3, .5, 9),
    "a8": ("action", "Đặt INGESTED, hiện hành; xóa vector bản cũ", 2, .7, 9, 260),
    "a9": ("action", "Đặt FAILED, lưu thông báo lỗi", 2, .7, 10, 240),
    "e1": ("action", "Báo lỗi tệp hoặc 409 mã trùng", 1, .8, 1, 150),
    "a10": ("action", "Hiển thị kết quả nạp", 1, .5, 10, 210),
    "x1": ("final", "", 1, .8, 0),
    "x2": ("final", "", 1, .5, 11),
}, [("s", "a1", ""), ("a1", "d0", ""), ("d0", "a2", "[PDF ≤ 25 MB]"), ("d0", "e1", "[sai định dạng / quá 25 MB]"),
    ("a2", "d1", ""), ("d1", "a3", "[mã mới]"), ("d1", "e1", "[mã đã tồn tại]"), ("e1", "x1", ""),
    ("a3", "a4", ""), ("a4", "a5", ""), ("a5", "a6", ""), ("a4", "b1", ""),
    ("b1", "d2", ""), ("d2", "a7", "[trích xuất được]"), ("d2", "b2", "[lỗi]"), ("b2", "a7", ""),
    ("a7", "b3", ""), ("b3", "d3", ""), ("d3", "a8", "[thành công]"), ("d3", "a9", "[lỗi]"),
    ("a8", "a10", ""), ("a9", "a10", ""), ("a6", "a10", ""), ("a10", "x2", "")])

# Hỏi đáp có trích dẫn (AiGatewayService.forward -> ai-service chat/ask)
swimlane_activity("HD_hoi_dap", [("Người dùng", 220), ("Frontend", 260), ("Backend", 480), ("ai-service", 470)], {
    "s": ("initial", "", 0, .5, 0),
    "a1": ("action", "Nhập câu hỏi", 0, .5, 1, 180),
    "a2": ("action", "POST /api/ai/chat", 1, .5, 1, 200),
    "a3": ("action", "Tăng bộ đếm Redis ai:rate:{email}:{phút}", 2, .3, 1, 260),
    "d1": ("decision", "", 2, .3, 2),
    "a4": ("action", "Ghi nhật ký RATE_LIMITED, trả 429", 2, .3, 3, 250),
    "a5": ("action", "Gắn user_roles theo vai trò", 2, .78, 2, 190),
    "b1": ("action", "Tác tử: nhận thức câu hỏi, chọn luật", 3, .22, 3, 200),
    "b2": ("action", "Truy xuất lai, chấm lại", 3, .22, 5, 200),
    "d2": ("decision", "", 3, .22, 6),
    "b3": ("action", "Sinh câu trả lời (LLM hoặc trích nguyên văn)", 3, .22, 7, 200),
    "b4": ("action", "Từ chối, citations rỗng", 3, .76, 7, 170),
    "a6": ("action", "Ghi nhật ký OK, model_used, latency", 2, .5, 8, 260),
    "a7": ("action", "Hiển thị lỗi 429", 1, .5, 3, 180),
    "a8": ("action", "Hiển thị câu trả lời, trích dẫn, vết tác tử", 1, .5, 8, 230),
    "a9": ("action", "Mở PDF tại trích dẫn", 0, .5, 9, 190),
    "x1": ("final", "", 1, .5, 4),
    "x2": ("final", "", 0, .5, 10),
}, [("s", "a1", ""), ("a1", "a2", ""), ("a2", "a3", ""), ("a3", "d1", ""),
    ("d1", "a4", "[> 30 yêu cầu/phút]"), ("d1", "a5", "[≤ 30]", None), ("a4", "a7", ""), ("a7", "x1", ""),
    ("a5", "b1", ""), ("b1", "b2", ""), ("b2", "d2", ""), ("d2", "b3", "[qua cổng bằng chứng]"),
    ("d2", "b4", "[không đủ căn cứ]"), ("b3", "a6", ""),
    ("b4", "a6", "", [(1327, 682), (1327, 742), (860, 742)]), ("a6", "a8", ""),
    ("a8", "a9", ""), ("a9", "x2", "")])

# Tìm kiếm ngữ nghĩa (AiGatewayService.search -> ai-service /api/v1/search, reranker on)
swimlane_activity("HD_tim_kiem", [("Người dùng", 220), ("Frontend", 250), ("Backend", 480), ("ai-service", 280)], {
    "s": ("initial", "", 0, .5, 0),
    "a1": ("action", "Nhập từ khóa / câu hỏi", 0, .5, 1, 180),
    "a2": ("action", "POST /api/ai/search", 1, .5, 1, 200),
    "a3": ("action", "Kiểm tra giới hạn 30 yêu cầu/phút", 2, .3, 1, 250),
    "d1": ("decision", "", 2, .3, 2),
    "a4": ("action", "Ghi RATE_LIMITED, trả 429", 2, .3, 3, 230),
    "a5": ("action", "Gắn user_roles", 2, .78, 2, 180),
    "b1": ("action", "Tìm vector, lọc allowed_roles", 3, .5, 3, 240),
    "b2": ("action", "Chấm lại bằng cross-encoder", 3, .5, 5, 240),
    "a6": ("action", "Ghi nhật ký OK, số kết quả", 2, .6, 6, 220),
    "a7": ("action", "Hiển thị lỗi 429", 1, .5, 3, 180),
    "a8": ("action", "Hiển thị đoạn, điểm, trang", 1, .5, 6, 200),
    "a9": ("action", "Mở tài liệu gốc", 0, .5, 7, 180),
    "x1": ("final", "", 1, .5, 4),
    "x2": ("final", "", 0, .5, 8),
}, [("s", "a1", ""), ("a1", "a2", ""), ("a2", "a3", ""), ("a3", "d1", ""), ("d1", "a4", "[vượt]"),
    ("d1", "a5", "[trong giới hạn]"), ("a4", "a7", ""), ("a7", "x1", ""), ("a5", "b1", ""), ("b1", "b2", ""),
    ("b2", "a6", ""), ("a6", "a8", ""), ("a8", "a9", ""), ("a9", "x2", "")])

# Xóa tài liệu (DocumentService.delete, @Transactional)
swimlane_activity("HD_xoa_tai_lieu", [("Quản trị viên", 220), ("Frontend", 250), ("Backend", 470), ("ai-service", 230)], {
    "s": ("initial", "", 0, .5, 0),
    "a1": ("action", "Chọn tài liệu, bấm Xóa", 0, .5, 1, 190),
    "d0": ("decision", "", 1, .5, 1),
    "a2": ("action", "DELETE /api/documents [ids]", 1, .5, 2, 220),
    "d1": ("decision", "", 2, .7, 2),
    "e409": ("action", "Trả 409: đang nạp", 2, .2, 3, 160),
    "b1": ("action", "Xóa vector của tài liệu", 3, .5, 3, 200),
    "d2": ("decision", "", 2, .7, 4),
    "e502": ("action", "Trả 502: không xóa được vector", 2, .2, 4, 170),
    "a3": ("action", "Xóa tệp PDF các phiên bản", 2, .7, 5, 220),
    "a4": ("action", "Xóa tasks, chunks, versions, document", 2, .7, 6, 260),
    "a5": ("action", "Báo lỗi", 1, .5, 4, 150),
    "a6": ("action", "Làm mới danh sách", 1, .5, 7, 180),
    "x0": ("final", "", 0, .5, 2),
    "x1": ("final", "", 1, .5, 5),
    "x2": ("final", "", 1, .5, 8),
}, [("s", "a1", ""), ("a1", "d0", ""), ("d0", "x0", "[hủy]"), ("d0", "a2", "[xác nhận]"), ("a2", "d1", ""),
    ("d1", "e409", "[đang nạp]"), ("d1", "b1", "[không]"), ("b1", "d2", ""), ("d2", "e502", "[lỗi]"),
    ("d2", "a3", "[xong]"), ("e409", "a5", ""), ("e502", "a5", ""), ("a5", "x1", ""), ("a3", "a4", ""),
    ("a4", "a6", ""), ("a6", "x2", "")])


# ---------------------------------------------------------------------------
# state machines
# ---------------------------------------------------------------------------
def state_diagram(name, states, transitions, final_kind="FinalState2"):
    d = p.diagram(name, "StateDiagram")
    S = {}
    for key, (kind, label, x, y, w, h) in states.items():
        if kind == "state":
            S[key] = d.add(Shape(p.el("State2", label), x, y, w, h))
        elif kind == "initial":
            S[key] = d.add(Shape(p.el("InitialPseudoState", ""), x, y, 20, 20, caption=(x + 26, y, 10, 10)))
        else:
            S[key] = d.add(Shape(p.el(final_kind, ""), x, y, 24, 24, caption=(x + 30, y, 10, 10)))
    for a, b, label, *pts in transitions:
        d.connect(p.rel("Transition2", S[a].el, S[b].el, label), S[a], S[b], points=pts[0] if pts else None)
    return d


# DocumentVersion.status + is_current (DocumentService, IngestionService)
state_diagram("TT_phien_ban", {
    "i": ("initial", "", 40, 150, 0, 0),
    "proc": ("state", "PROCESSING", 160, 130, 170, 60),
    "fail": ("state", "FAILED", 160, 330, 170, 60),
    "cur": ("state", "INGESTED, hiện hành", 520, 130, 200, 60),
    "arc": ("state", "INGESTED, không hiện hành", 520, 330, 220, 60),
    "f": ("final", "", 880, 250, 0, 0),
}, [("i", "proc", "tải lên / tải phiên bản mới"),
    ("proc", "cur", "nạp xong 5/5"),
    ("proc", "fail", "lỗi ở bước bất kỳ"),
    ("fail", "proc", "thử lại (retry)", [(290, 330), (290, 190)]),
    ("cur", "proc", "nạp lại (reindex)", [(560, 130), (560, 90), (290, 90), (290, 130)]),
    ("cur", "arc", "bản khác thành hiện hành", [(580, 190), (580, 330)]),
    ("arc", "cur", "đặt hiện hành", [(680, 330), (680, 190)]),
    ("cur", "f", "xóa tài liệu"),
    ("arc", "f", "xóa tài liệu"),
    ("fail", "f", "xóa tài liệu", [(245, 390), (245, 430), (892, 430), (892, 274)])])

# ingestion_tasks.step (IngestionService.updateTask, Bảng 2.18)
state_diagram("TT_nhiem_vu_nap", {
    "i": ("initial", "", 20, 60, 0, 0),
    "s1": ("state", "Bước 1: đọc, OCR tệp PDF", 90, 40, 220, 60),
    "s2": ("state", "Bước 2: chia đoạn", 450, 40, 190, 60),
    "s3": ("state", "Bước 3: tạo embedding", 780, 40, 200, 60),
    "s4": ("state", "Bước 4: ghi kho vector", 1100, 40, 200, 60),
    "ok": ("state", "INGESTED (bước 5)", 1100, 220, 200, 60),
    "ko": ("state", "FAILED (giữ bước lỗi)", 600, 220, 220, 60),
    "f": ("final", "", 1400, 238, 0, 0),
}, [("i", "s1", ""), ("s1", "s2", "đã trích N trang"), ("s2", "s3", "đã tạo M đoạn"), ("s3", "s4", ""),
    ("s4", "ok", "ghi xong"), ("s1", "ko", "lỗi"), ("s2", "ko", "lỗi"), ("s3", "ko", "lỗi"), ("s4", "ko", "lỗi"),
    ("ok", "f", ""), ("ko", "f", "", [(710, 280), (710, 330), (1412, 330), (1412, 262)])])


# ---------------------------------------------------------------------------
# deployment (docker-compose.yml)
# ---------------------------------------------------------------------------
d = p.diagram("TK_trien_khai", "DeploymentDiagram")
client = d.add(Shape(p.el("Node", "Máy người dùng"), 10, 80, 230, 130))
browser = d.add(Shape(p.el("Component", "Trình duyệt (React SPA)"), 25, 120, 200, 62), client)
host = d.add(Shape(p.el("Node", "Máy chủ Docker (docker-compose)"), 300, 10, 1500, 420))
C = {}


def box(key, label, x, y, w=210, h=62):
    C[key] = d.add(Shape(p.el("Component", label), x, y, w, h), host)


# row 1: services; row 2: what each one owns, placed under its owner
box("fe", "frontend: Nginx :3000", 330, 110)
box("be", "backend: Spring Boot :8080", 610, 110)
box("ai", "ai-service: FastAPI :8001", 1110, 110)
box("ol", "ollama :11434", 1520, 110, 200)
box("vol", "volume backend_uploads", 380, 300)
box("pg", "postgres 15 :5432", 610, 300)
box("rd", "redis 7 :6379", 840, 300)
box("qd", "qdrant :6333 / :6334", 1080, 300)
box("n4", "neo4j 5.26 :7474 / :7687", 1310, 300)
box("hf", "volume huggingface_cache", 1540, 300, 200)


def link(a, b, label, sa=None, sb=None):
    A, B = sa or C[a], sb or C[b]
    d.connect(p.rel("Dependency", A.el, B.el, label), A, B)


link(None, "fe", "HTTP :3000", sa=browser)
link("fe", "be", "proxy /api/")
link("be", "ai", "REST /api/v1")
link("be", "pg", "JDBC")
link("be", "rd", "INCR / EXPIRE")
link("be", "vol", "PDF gốc")
link("ai", "qd", "HTTP / gRPC")
link("ai", "n4", "Bolt")
link("ai", "ol", "HTTP (LLM)")
link("ai", "hf", "mô hình nhúng")


# ---------------------------------------------------------------------------
# packages (backend com.tho.enterpriseai, ai-service app)
# ---------------------------------------------------------------------------
d = p.diagram("TK_goi", "ClassDiagram")
be_pkg = p.el("Package", "backend: com.tho.enterpriseai")
ai_pkg = p.el("Package", "ai-service: app")
BE = d.add(Shape(be_pkg, 10, 10, 640, 420))
AI = d.add(Shape(ai_pkg, 700, 10, 640, 420))
P = {}


def pkg(key, label, parent_el, parent_shape, x, y, w=170, h=80):
    P[key] = d.add(Shape(p.el("Package", label, parent=parent_el), x, y, w, h), parent_shape)


pkg("auth", "auth", be_pkg, BE, 40, 60)
pkg("user", "user", be_pkg, BE, 40, 300)
pkg("security", "security", be_pkg, BE, 250, 180)
pkg("document", "document", be_pkg, BE, 460, 60)
pkg("ai", "ai", be_pkg, BE, 460, 300)
pkg("config", "config", be_pkg, BE, 250, 330)
pkg("api", "api.v1", ai_pkg, AI, 730, 50, 180)
pkg("agent", "agent", ai_pkg, AI, 1130, 50, 180)
pkg("rag", "truy xuất: rag_service, retriever, reranker", ai_pkg, AI, 900, 190, 270)
pkg("kg", "knowledge_graph", ai_pkg, AI, 1130, 330, 180)
pkg("doc", "xử lý tài liệu: parser, chunker", ai_pkg, AI, 715, 330, 210)
for a, b in [("auth", "security"), ("auth", "user"), ("security", "user"), ("config", "security"), ("config", "user"),
             ("document", "security"), ("ai", "security"), ("api", "agent"), ("api", "rag"), ("api", "doc"),
             ("agent", "rag"), ("agent", "kg"), ("rag", "kg"), ("kg", "doc")]:
    d.connect(p.rel("Dependency", P[a].el, P[b].el), P[a], P[b])
# api.v1 -> knowledge_graph goes under the retrieval box instead of through it
d.connect(p.rel("Dependency", P["api"].el, P["kg"].el), P["api"], P["kg"], points=[(880, 130), (880, 300), (1130, 345)])


# ---------------------------------------------------------------------------
# NoSQL storage design (orange): Neo4j graph schema, Qdrant collection, Redis key
# ---------------------------------------------------------------------------
def nosql_table(d, name, cols, x, y, w=260):
    t = p.el("DBTable", name)
    out = {}
    for cname, ctype, length, pk in cols:
        out[cname] = p.el("DBColumn", cname, parent=t, type=ctype, length=length, primaryKey=pk, nullable=False)
    return d.add(Shape(t, x, y, w, 26 + 19 * len(cols), fill=ORANGE)), out


d = p.diagram("CSDL_neo4j", "ERDiagram")
V, I, F, B, TX = "varchar", "integer", "float", "bit", "clob"
kb, kbc = nosql_table(d, "KnowledgeBase", [("kb_id", V, 16, True), ("name", V, 128, False)], 10, 10, 220)
doc, docc = nosql_table(d, "Document", [("doc_id", V, 64, True), ("title", V, 255, False), ("source_uri", V, 512, False),
                                        ("source_type", V, 16, False), ("content_hash", V, 64, False),
                                        ("version", I, 0, False), ("is_current", B, 0, False)], 300, 10)
ch, chc = nosql_table(d, "Chunk", [("chunk_id", V, 128, True), ("text", TX, 0, False), ("page_start", I, 0, False),
                                   ("page_end", I, 0, False), ("section_path", V, 512, False), ("version_id", V, 64, False)],
                      640, 10)
en, enc = nosql_table(d, "Entity", [("entity_id", V, 64, True), ("name", V, 255, False), ("type", V, 32, False),
                                    ("description", TX, 0, False), ("embedding", F, 384, False)], 640, 260)
cl, clc = nosql_table(d, "Claim", [("claim_id", V, 64, True), ("attribute", V, 128, False), ("value", V, 255, False),
                                   ("unit", V, 32, False), ("status", V, 16, False), ("confidence", F, 0, False)], 300, 260)
for a, b, rel in [(kb, doc, "HAS_DOCUMENT"), (doc, ch, "HAS_CHUNK"), (ch, en, "MENTIONS"), (ch, cl, "ASSERTS")]:
    d.connect(p.rel("DBForeignKey", a.el, b.el, rel, extra=_sp("fromMultiplicity", "1") + _sp("toMultiplicity", "0..*")), a, b)

d = p.diagram("CSDL_qdrant_redis", "ERDiagram")
nosql_table(d, "Qdrant: enterprise_documents", [
    ("point_id", V, 64, True), ("vector", F, 384, False), ("chunk_id", V, 128, False), ("content", TX, 0, False),
    ("document_id", V, 36, False), ("document_code", V, 64, False), ("title", V, 255, False),
    ("document_type", V, 64, False), ("version_id", V, 36, False), ("version_number", I, 0, False),
    ("allowed_roles", V, 255, False), ("page_start", I, 0, False), ("page_end", I, 0, False),
    ("chunk_index", I, 0, False), ("section_path", V, 512, False)], 10, 10, 300)
nosql_table(d, "Redis: ai:rate:{email}:{phút}", [("value: số yêu cầu (INCR)", I, 0, False), ("TTL: 120 giây (EXPIRE)", I, 0, False)], 380, 10, 280)

if __name__ == "__main__":
    Path(sys.argv[1]).write_text(p.xml(), encoding="utf-8")
    print("diagrams:", [x.name for x in p.diagrams])
