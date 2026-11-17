"""Chapter 2 diagrams (analysis & design) as a Visual Paradigm project.

python ch2_diagrams.py -> ch2.xml, then ImportXML + ExportXML (images).
Content follows the running code: backend (Spring Boot), ai-service (FastAPI),
Flyway schema V1 + V2.
"""
import sys

sys.path.insert(0, ".")
from vpgen import BLUE, WHITE, Project, Shape  # noqa: E402

p = Project()
UW, UH = 250, 44  # use case size


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
def actor(d, el, x, y, above=False):
    w = max(80, 7 * len(el.name))
    cy = y - 20 if above else y + 72
    return d.add(Shape(el, x, y, 40, 70, caption=(x + 20 - w // 2, cy, w, 16)))


def note(d, text, x, y, w, h):
    n = p.el("NOTE", text)
    return d.add(Shape(n, x, y, w, h))


def usecase_diagram(name, title, groups, left, right, links, incl=(), ext=(), gen=(), note_text=None):
    """groups: list of columns, each a list of use case names (top to bottom)."""
    d = p.diagram(name, "UseCaseDiagram")
    col_gap, row_gap = 50, 62
    groups = [[it if isinstance(it, tuple) else (it, None) for it in col] for col in groups]
    rows = max(max((r + 1 if r is not None else i + 1) for i, (_, r) in enumerate(col)) for col in groups)
    sys_w = 40 + len(groups) * UW + (len(groups) - 1) * col_gap + 40
    sys_h = 50 + rows * row_gap
    sx, sy = 190, 10
    system = p.el("System", title)
    S = d.add(Shape(system, sx, sy, sys_w, sys_h))
    uc = {}
    for ci, col in enumerate(groups):
        offset = (rows - len(col)) * row_gap // 2
        for ri, (label, row) in enumerate(col):
            el = p.el("UseCase", label)
            ypos = sy + 40 + (int(row * row_gap) if row is not None else offset + ri * row_gap)
            uc[label] = d.add(Shape(el, sx + 40 + ci * (UW + col_gap), ypos, UW, UH), S)
    act = {}
    generals = {b for _, b in gen}
    for i, label in enumerate(left):
        el = p.el("Actor", label)
        y = sy + (i + 0.5) * sys_h / len(left) - 35
        act[label] = actor(d, el, 60, int(y))
    for i, label in enumerate(right):
        el = p.el("Actor", label)
        y = sy + (i + 0.5) * sys_h / len(right) - 35
        act[label] = actor(d, el, sx + sys_w + 90, int(y))
    for a, u in links:
        d.connect(p.rel("Association", act[a].el, uc[u].el), act[a], uc[u])
    for a, b in incl:
        d.connect(p.rel("Include", uc[a].el, uc[b].el, "«include»"), uc[a], uc[b])
    for a, b in ext:  # a extends b; VP puts the arrow head on the model's "from" end
        d.connect(p.rel("Extend", uc[b].el, uc[a].el, "«extend»"), uc[b], uc[a])
    # Generalisation between actors is stated in the note: headless VP export cannot draw its arrow head.
    if note_text:
        note(d, note_text, sx, sy + sys_h + 14, sys_w, 40)
    return d


def sequence(name, lifelines, messages, note_text=None, gap=40, width=150, step=170):
    d = p.diagram(name, "InteractionDiagram")
    height = 70 + gap * len(messages) + 20
    shapes = []
    for i, label in enumerate(lifelines):
        el = p.el("InteractionLifeLine", label)
        shapes.append(d.add(Shape(el, 10 + i * step, 10, width, height)))
    for k, (a, b, text) in enumerate(messages):
        y = 75 + k * gap
        xa, xb = shapes[a].cx(), shapes[b].cx()
        rel = p.rel("Message", shapes[a].el, shapes[b].el, text)
        if a == b:
            pts = [(xa, y - 8), (xa + 30, y - 8), (xa + 30, y + 8), (xa, y + 8)]
            d.connect(rel, shapes[a], shapes[b], points=pts, label_xy=(xa + 36, y - 6))
            continue
        lx = min(xa, xb) + 12
        d.connect(rel, shapes[a], shapes[b], points=[(xa, y), (xb, y)], label_xy=(lx, y - 17))
    if note_text:
        note(d, note_text, 10, height + 20, min(len(lifelines) * step - 20, 900), 40)
    return d


# ---------------------------------------------------------------------------
# H2.1 Microservice architecture
# ---------------------------------------------------------------------------
d = p.diagram("H2_1_kien_truc_microservice", "ComponentDiagram")
C = {}


def comp(key, label, x, y, w=210, h=64):
    C[key] = d.add(Shape(p.el("Component", label), x, y, w, h))


comp("browser", "Trình duyệt (người dùng)", 10, 200, 180)
comp("fe", "frontend: React SPA + Nginx (:3000)", 300, 200, 240)
comp("be", "backend: Spring Boot API Gateway (:8080)", 650, 195, 270, 74)
comp("ai", "ai-service: FastAPI (:8001)", 1110, 195, 240, 74)
comp("pg", "PostgreSQL 15 (6 bảng)", 520, 10, 200)
comp("redis", "Redis 7 (rate limit)", 830, 10, 190)
comp("files", "Kho tệp PDF (volume uploads)", 670, 400, 230)
comp("qdrant", "Qdrant (vector 384 chiều)", 1060, 10, 210)
comp("neo4j", "Neo4j 5 (đồ thị tri thức)", 1340, 10, 210)
comp("llm", "LLM: Ollama / Gemini", 1460, 200, 190)
comp("model", "Mô hình nhúng + reranker", 1115, 400, 230)

def dep(a, b, label):
    d.connect(p.rel("Dependency", C[a].el, C[b].el, label), C[a], C[b])


dep("browser", "fe", "HTTPS")
dep("fe", "be", "REST /api/* + JWT")
dep("be", "ai", "REST /api/v1, X-Internal-Token")
dep("be", "pg", "JDBC (Flyway)")
dep("be", "redis", "INCR/EXPIRE")
dep("be", "files", "đọc/ghi PDF")
dep("ai", "qdrant", "gRPC/HTTP")
dep("ai", "neo4j", "Bolt + Cypher")
dep("ai", "llm", "HTTP")
dep("ai", "model", "nạp trong tiến trình")
note(d, "Mỗi khối là một container trong docker-compose. Trình duyệt chỉ gọi backend; ai-service và các kho dữ liệu không mở ra ngoài.", 10, 500, 820, 40)

# ---------------------------------------------------------------------------
# H2.2 Functional decomposition
# ---------------------------------------------------------------------------
d = p.diagram("H2_2_phan_ra_chuc_nang", "ClassDiagram")
modules = [
    ("M1. Xác thực và người dùng", ["Đăng nhập", "Đăng ký tài khoản", "Xem danh sách người dùng", "Tạo tài khoản", "Đổi vai trò", "Khóa / mở khóa"]),
    ("M2. Quản lý tài liệu", ["Xem và lọc tài liệu", "Xem chi tiết, phiên bản", "Xem đoạn trích", "Xem PDF gốc", "Tải lên tài liệu", "Tải phiên bản mới", "Đặt phiên bản hiện hành", "Xóa tài liệu"]),
    ("M3. Nạp và xử lý tài liệu", ["Trích xuất, OCR", "Phân đoạn theo cấu trúc", "Tạo embedding, ghi Qdrant", "Theo dõi tiến trình", "Thử lại bản lỗi", "Nạp lại bản hiện hành"]),
    ("M4. Hỏi đáp và tìm kiếm", ["Hỏi đáp có trích dẫn", "Tìm kiếm ngữ nghĩa", "Xem trích dẫn trên PDF", "Xem vết xử lý tác tử"]),
    ("M5. Giám sát và tri thức", ["Xem nhật ký truy vấn AI", "Kiểm tra trạng thái AI", "Quản trị KB đồ thị", "Đánh giá truy xuất"]),
]
root = d.add(Shape(p.el("Class", "Hệ thống EAKWP"), 470, 10, 260, 44))
mw, gap = 210, 24
for i, (mname, funcs) in enumerate(modules):
    mx = 10 + i * (mw + gap)
    m = d.add(Shape(p.el("Class", mname), mx, 100, mw, 44))
    d.connect(p.rel("Association", root.el, m.el), root, m,
              points=[(root.cx(), 54), (root.cx(), 77), (m.cx(), 77), (m.cx(), 100)])
    spine = mx + 14
    for j, f in enumerate(funcs):
        fy = 170 + j * 50
        fs = d.add(Shape(p.el("Class", f), mx + 34, fy, mw - 34, 36))
        d.connect(p.rel("Association", m.el, fs.el), m, fs,
                  points=[(spine, 144), (spine, fy + 18), (mx + 34, fy + 18)])

# ---------------------------------------------------------------------------
# H2.3 Overall use case
# ---------------------------------------------------------------------------
d = p.diagram("H2_3_use_case_tong_quan", "UseCaseDiagram")
system = p.el("System", "Hệ thống EAKWP")
S = d.add(Shape(system, 260, 10, 380, 610))
labels = ["Đăng nhập", "Tra cứu tài liệu, xem PDF", "Hỏi đáp có trích dẫn", "Tìm kiếm ngữ nghĩa",
          "Quản lý người dùng", "Quản lý tài liệu và phiên bản", "Nạp và xử lý tài liệu",
          "Giám sát truy vấn AI", "Quản trị cơ sở tri thức đồ thị"]
U = {}
for i, label in enumerate(labels):
    U[label] = d.add(Shape(p.el("UseCase", label), 320, 40 + i * 63 + (20 if i >= 4 else 0), 260, UH), S)
A = {}
A["user"] = actor(d, p.el("Actor", "Người dùng"), 80, 130)
A["admin"] = actor(d, p.el("Actor", "Quản trị viên"), 80, 420)
A["ai"] = actor(d, p.el("Actor", "Dịch vụ AI"), 760, 250)
A["llm"] = actor(d, p.el("Actor", "Mô hình ngôn ngữ (LLM)"), 760, 60)
for a, u in [
    ("user", "Đăng nhập"), ("user", "Tra cứu tài liệu, xem PDF"), ("user", "Hỏi đáp có trích dẫn"),
    ("user", "Tìm kiếm ngữ nghĩa"),
    ("admin", "Quản lý người dùng"), ("admin", "Quản lý tài liệu và phiên bản"),
    ("admin", "Nạp và xử lý tài liệu"), ("admin", "Giám sát truy vấn AI"),
    ("admin", "Quản trị cơ sở tri thức đồ thị"),
    ("ai", "Nạp và xử lý tài liệu"), ("ai", "Hỏi đáp có trích dẫn"), ("ai", "Tìm kiếm ngữ nghĩa"),
    ("ai", "Quản trị cơ sở tri thức đồ thị"), ("llm", "Hỏi đáp có trích dẫn"),
]:
    d.connect(p.rel("Association", A[a].el, U[u].el), A[a], U[u])
note(d, "Người dùng gồm ba vai trò EMPLOYEE, MANAGER, IT_SUPPORT; Quản trị viên (ADMIN) kế thừa mọi quyền của Người dùng.", 260, 632, 380, 54)

# ---------------------------------------------------------------------------
# H2.4 - H2.8 Use cases per module
# ---------------------------------------------------------------------------
usecase_diagram(
    "H2_4_uc_xac_thuc_nguoi_dung", "M1. Xác thực và quản lý người dùng",
    [["Đăng nhập", "Đăng ký tài khoản", "Xem danh sách người dùng", "Tạo tài khoản", "Đổi vai trò", "Khóa / mở khóa tài khoản"],
     ["Kiểm tra mật khẩu BCrypt", "Cấp JWT (1 giờ)", "Kiểm tra quyền ADMIN"]],
    ["Người dùng", "Quản trị viên"], [],
    [("Người dùng", "Đăng nhập"), ("Người dùng", "Đăng ký tài khoản"),
     ("Quản trị viên", "Xem danh sách người dùng"), ("Quản trị viên", "Tạo tài khoản"),
     ("Quản trị viên", "Đổi vai trò"), ("Quản trị viên", "Khóa / mở khóa tài khoản")],
    incl=[("Đăng nhập", "Kiểm tra mật khẩu BCrypt"), ("Đăng nhập", "Cấp JWT (1 giờ)"),
          ("Đăng ký tài khoản", "Cấp JWT (1 giờ)"),
          ("Tạo tài khoản", "Kiểm tra quyền ADMIN"), ("Đổi vai trò", "Kiểm tra quyền ADMIN"),
          ("Khóa / mở khóa tài khoản", "Kiểm tra quyền ADMIN")],
    gen=[("Quản trị viên", "Người dùng")],
    note_text="Quản trị viên kế thừa Người dùng nên cũng đăng nhập được. Đăng ký công khai luôn tạo tài khoản EMPLOYEE.",
)
usecase_diagram(
    "H2_5_uc_quan_ly_tai_lieu", "M2. Quản lý tài liệu",
    [["Xem danh sách tài liệu", "Xem chi tiết và phiên bản", "Xem đoạn trích", "Xem PDF gốc",
      "Tải lên tài liệu mới", "Tải lên phiên bản mới", "Đặt phiên bản hiện hành", "Xóa tài liệu"],
     ["Lọc theo danh mục, trạng thái", "Kiểm tra tệp PDF (≤ 25 MB)", "Khởi chạy pipeline nạp", "Xóa vector ở ai-service"]],
    ["Người dùng", "Quản trị viên"], ["Dịch vụ AI"],
    [("Người dùng", "Xem danh sách tài liệu"), ("Người dùng", "Xem chi tiết và phiên bản"),
     ("Người dùng", "Xem đoạn trích"), ("Người dùng", "Xem PDF gốc"),
     ("Quản trị viên", "Tải lên tài liệu mới"), ("Quản trị viên", "Tải lên phiên bản mới"),
     ("Quản trị viên", "Đặt phiên bản hiện hành"), ("Quản trị viên", "Xóa tài liệu"),
     ("Dịch vụ AI", "Khởi chạy pipeline nạp"), ("Dịch vụ AI", "Xóa vector ở ai-service")],
    incl=[("Tải lên tài liệu mới", "Kiểm tra tệp PDF (≤ 25 MB)"), ("Tải lên phiên bản mới", "Kiểm tra tệp PDF (≤ 25 MB)"),
          ("Tải lên tài liệu mới", "Khởi chạy pipeline nạp"), ("Tải lên phiên bản mới", "Khởi chạy pipeline nạp"),
          ("Xóa tài liệu", "Xóa vector ở ai-service")],
    ext=[("Lọc theo danh mục, trạng thái", "Xem danh sách tài liệu")],
    gen=[("Quản trị viên", "Người dùng")],
    note_text="Quản trị viên kế thừa mọi use case của Người dùng. Người dùng chỉ thấy tài liệu có allowed_roles chứa vai trò của mình hoặc '*'.",
)
usecase_diagram(
    "H2_6_uc_nap_tai_lieu", "M3. Nạp và xử lý tài liệu",
    [[("Theo dõi tiến trình nạp", 0), ("Thử lại phiên bản lỗi", 1.2), ("Nạp lại phiên bản hiện hành", 2.6)],
     [("Nạp tài liệu (5 bước)", 1.9)],
     [("Trích xuất văn bản, OCR", 0), ("Phân đoạn theo Chương/Điều", 1.2), ("Tạo embedding, ghi Qdrant", 2.4), ("Ghi nút vào đồ thị Neo4j", 3.6)]],
    ["Quản trị viên"], ["Dịch vụ AI"],
    [("Quản trị viên", "Theo dõi tiến trình nạp"), ("Quản trị viên", "Thử lại phiên bản lỗi"),
     ("Quản trị viên", "Nạp lại phiên bản hiện hành"),
     ("Dịch vụ AI", "Trích xuất văn bản, OCR"), ("Dịch vụ AI", "Phân đoạn theo Chương/Điều"),
     ("Dịch vụ AI", "Tạo embedding, ghi Qdrant"), ("Dịch vụ AI", "Ghi nút vào đồ thị Neo4j")],
    incl=[("Nạp tài liệu (5 bước)", "Trích xuất văn bản, OCR"), ("Nạp tài liệu (5 bước)", "Phân đoạn theo Chương/Điều"),
          ("Nạp tài liệu (5 bước)", "Tạo embedding, ghi Qdrant"),
          ("Thử lại phiên bản lỗi", "Nạp tài liệu (5 bước)"), ("Nạp lại phiên bản hiện hành", "Nạp tài liệu (5 bước)")],
    ext=[("Ghi nút vào đồ thị Neo4j", "Tạo embedding, ghi Qdrant")],
    note_text="Nạp tài liệu chạy bất đồng bộ (@Async); khi ai-service không trích xuất được, backend tự chuyển sang PDFBox.",
)
usecase_diagram(
    "H2_7_uc_hoi_dap_tim_kiem", "M4. Hỏi đáp và tìm kiếm",
    [[("Xem trích dẫn trên PDF", 0), ("Hỏi đáp có trích dẫn", 1.5), ("Xem vết xử lý tác tử", 3), ("Tìm kiếm ngữ nghĩa", 4.6)],
     [("Sinh câu trả lời bằng LLM", 0), ("Giới hạn 30 yêu cầu/phút", 2), ("Lọc theo quyền tài liệu", 3.1), ("Ghi nhật ký truy vấn AI", 4.2)]],
    ["Người dùng"], ["Mô hình ngôn ngữ (LLM)", "Dịch vụ AI"],
    [("Người dùng", "Hỏi đáp có trích dẫn"), ("Người dùng", "Tìm kiếm ngữ nghĩa"),
     ("Người dùng", "Xem trích dẫn trên PDF"), ("Người dùng", "Xem vết xử lý tác tử"),
     ("Dịch vụ AI", "Lọc theo quyền tài liệu"), ("Mô hình ngôn ngữ (LLM)", "Sinh câu trả lời bằng LLM")],
    incl=[("Hỏi đáp có trích dẫn", "Giới hạn 30 yêu cầu/phút"), ("Tìm kiếm ngữ nghĩa", "Giới hạn 30 yêu cầu/phút"),
          ("Hỏi đáp có trích dẫn", "Lọc theo quyền tài liệu"), ("Tìm kiếm ngữ nghĩa", "Lọc theo quyền tài liệu"),
          ("Hỏi đáp có trích dẫn", "Ghi nhật ký truy vấn AI"), ("Tìm kiếm ngữ nghĩa", "Ghi nhật ký truy vấn AI")],
    ext=[("Xem trích dẫn trên PDF", "Hỏi đáp có trích dẫn"), ("Xem vết xử lý tác tử", "Hỏi đáp có trích dẫn"),
         ("Sinh câu trả lời bằng LLM", "Hỏi đáp có trích dẫn")],
)
usecase_diagram(
    "H2_8_uc_giam_sat_tri_thuc", "M5. Giám sát và quản trị tri thức",
    [["Kiểm tra trạng thái dịch vụ AI", "Xem nhật ký truy vấn AI", "Quản trị KB đồ thị", "Đánh giá cấu hình truy xuất"],
     ["Nạp PDF vào KB1", "Nạp link vào KB2", "Gộp KB1 + KB2", "Bảo trì: trùng lặp, mâu thuẫn"]],
    ["Người dùng", "Quản trị viên"], ["Dịch vụ AI"],
    [("Người dùng", "Kiểm tra trạng thái dịch vụ AI"), ("Quản trị viên", "Xem nhật ký truy vấn AI"),
     ("Quản trị viên", "Quản trị KB đồ thị"), ("Quản trị viên", "Đánh giá cấu hình truy xuất"),
     ("Dịch vụ AI", "Nạp PDF vào KB1"), ("Dịch vụ AI", "Nạp link vào KB2"),
     ("Dịch vụ AI", "Gộp KB1 + KB2"), ("Dịch vụ AI", "Bảo trì: trùng lặp, mâu thuẫn")],
    incl=[("Quản trị KB đồ thị", "Nạp PDF vào KB1"), ("Quản trị KB đồ thị", "Nạp link vào KB2"),
          ("Quản trị KB đồ thị", "Gộp KB1 + KB2"), ("Quản trị KB đồ thị", "Bảo trì: trùng lặp, mâu thuẫn")],
    gen=[("Quản trị viên", "Người dùng")],
    note_text="Chi tiết KB đồ thị (KB1, KB2, hợp nhất, cập nhật) trình bày ở Chương 4; đánh giá truy xuất ở Chương 3 và 4.",
)

# ---------------------------------------------------------------------------
# H2.9 - H2.11 Sequence diagrams
# ---------------------------------------------------------------------------
sequence(
    "H2_9_tuan_tu_dang_nhap",
    ["Người dùng", "LoginPage", "AuthController", "AuthService", "UserRepository", "JwtService"],
    [
        (0, 1, "nhập email, mật khẩu"),
        (1, 2, "POST /api/auth/login"),
        (2, 3, "login(request)"),
        (3, 4, "findByEmail(email)"),
        (4, 3, "User"),
        (3, 3, "BCrypt.matches, kiểm tra active"),
        (3, 5, "generateToken(email, role)"),
        (5, 3, "JWT (hết hạn 1 giờ)"),
        (3, 2, "AuthResponse"),
        (2, 1, "200 OK {token, role, fullName}"),
        (1, 0, "lưu phiên, chuyển tới trang theo vai trò"),
    ],
    note_text="Sai mật khẩu hoặc không có email: 401 \"Email hoặc mật khẩu không đúng.\"; tài khoản bị khóa: 403.",
)
sequence(
    "H2_10_tuan_tu_tai_len_nap",
    ["Quản trị viên", "DocumentController", "DocumentService", "IngestionService (@Async)", "ai-service", "Qdrant", "PostgreSQL"],
    [
        (0, 1, "POST /api/documents/upload (PDF)"),
        (1, 2, "upload(code, title, ...)"),
        (2, 6, "kiểm tra mã trùng, lưu tệp, SHA-256"),
        (2, 6, "INSERT documents, version PROCESSING"),
        (2, 3, "process(taskId)"),
        (2, 1, "UploadTicket {taskId}"),
        (1, 0, "202 Accepted"),
        (3, 4, "POST /api/v1/extract (bước 1-2)"),
        (4, 3, "trang, chunk, highlight"),
        (3, 6, "lưu document_chunks (bước 3)"),
        (3, 4, "POST /api/v1/ingest (bước 4)"),
        (4, 5, "upsert vector + payload"),
        (4, 3, "số vector đã ghi"),
        (3, 6, "INGESTED, đặt hiện hành (bước 5)"),
        (0, 1, "GET /api/ai/status/{taskId}"),
        (1, 0, "bước 5/5, INGESTED"),
    ],
    gap=36, step=160,
    note_text="Lỗi ở bất kỳ bước nào: phiên bản chuyển FAILED kèm thông báo; quản trị viên dùng \"Thử lại\".",
)
sequence(
    "H2_11_tuan_tu_hoi_dap",
    ["Người dùng", "ChatPage", "AiGatewayService", "Redis", "ai-service (tác tử)", "Qdrant / Neo4j", "LLM", "ai_audit_logs"],
    [
        (0, 1, "nhập câu hỏi"),
        (1, 2, "POST /api/ai/chat + JWT"),
        (2, 3, "INCR rate:{email}"),
        (3, 2, "số lần trong phút"),
        (2, 4, "POST /chat/ask + user_roles"),
        (4, 5, "tìm vector + đồ thị, lọc quyền"),
        (5, 4, "đoạn ứng viên"),
        (4, 4, "rerank, chọn bằng chứng"),
        (4, 6, "ngữ cảnh [n] + câu hỏi"),
        (6, 4, "câu trả lời có [n]"),
        (4, 2, "answer, citations, agent_trace"),
        (2, 7, "ghi nhật ký (OK, latency)"),
        (2, 1, "200 OK"),
        (1, 0, "câu trả lời + trích dẫn"),
    ],
    gap=36, step=150, width=140,
    note_text="Quá 30 yêu cầu/phút: 429 và ghi RATE_LIMITED; không đủ bằng chứng: tác tử từ chối, bỏ qua LLM.",
)

# ---------------------------------------------------------------------------
# H2.12 Activity: document version lifecycle
# ---------------------------------------------------------------------------
d = p.diagram("H2_12_hoat_dong_vong_doi_phien_ban", "ActivityDiagram")
N = {}


def node(key, kind, label, x, y, w=260, h=44, cap=None):
    N[key] = d.add(Shape(p.el(kind, label), x, y, w, h, caption=cap))


node("start", "InitialNode", "", 230, 10, 20, 20, cap=(260, 10, 10, 10))
node("up", "ActivityAction", "Tải lên PDF hoặc phiên bản mới", 110, 60)
node("save", "ActivityAction", "Lưu tệp, tạo phiên bản PROCESSING", 110, 134)
node("ext", "ActivityAction", "Bước 1-2: trích xuất, OCR, chia đoạn", 110, 208)
node("chk", "ActivityAction", "Bước 3: lưu document_chunks", 110, 282)
node("emb", "ActivityAction", "Bước 4: tạo embedding, ghi Qdrant", 110, 356)
node("dec", "DecisionNode", "", 220, 436, 40, 40, cap=(270, 448, 110, 16))
node("ok", "ActivityAction", "INGESTED, đặt hiện hành, xóa vector bản cũ", 30, 520, 300)
node("fail", "ActivityAction", "FAILED, lưu error_message", 420, 520, 230)
node("retry", "ActivityAction", "Quản trị viên chọn Thử lại", 420, 208, 230)
node("end", "ActivityFinalNode", "", 170, 610, 24, 24, cap=(200, 612, 10, 10))


def flow(a, b, label="", pts=None):
    d.connect(p.rel("ControlFlow", N[a].el, N[b].el, label), N[a], N[b], points=pts)


flow("start", "up")
flow("up", "save")
flow("save", "ext")
flow("ext", "chk")
flow("chk", "emb")
flow("emb", "dec")
flow("dec", "ok", "[thành công]")
flow("dec", "fail", "[lỗi]")
flow("ok", "end")
flow("fail", "retry", "", pts=[(535, 520), (535, 252)])
flow("retry", "ext", "", pts=[(420, 230), (370, 230)])

# ---------------------------------------------------------------------------
# H2.13 Class diagram: layers of the backend
# ---------------------------------------------------------------------------
d = p.diagram("H2_13_lop_thiet_ke_backend", "ClassDiagram")
K = {}


def cls(key, label, x, y, w=210, h=40):
    K[key] = d.add(Shape(p.el("Class", label), x, y, w, h))


cls("dc", "DocumentController", 20, 20)
cls("ic", "IngestionController", 250, 20)
cls("ac", "AiGatewayController", 750, 20)
cls("uc", "UserController", 1000, 20)
cls("auc", "AuthController", 1240, 20)
cls("ds", "DocumentService", 20, 130)
cls("is", "IngestionService", 250, 130)
cls("as", "AiGatewayService", 750, 130)
cls("us", "UserService", 1000, 130)
cls("aus", "AuthService", 1240, 130)
cls("pdf", "PdfProcessor", 20, 250)
cls("parse", "AiParseClient", 250, 250)
cls("ing", "AiIngestClient", 480, 250)
cls("rl", "AiRateLimiter", 750, 250)
cls("agc", "AiGatewayClient", 1000, 250)
cls("jwt", "JwtService", 1240, 250)
cls("dr", "DocumentRepository", 20, 420)
cls("vr", "DocumentVersionRepository", 250, 420, 230)
cls("cr", "DocumentChunkRepository", 500, 420)
cls("tr", "IngestionTaskRepository", 730, 420)
cls("arr", "AiAuditLogRepository", 960, 420)
cls("urr", "UserRepository", 1190, 420)
for a, b in [("dc", "ds"), ("ic", "ds"), ("ac", "as"), ("uc", "us"), ("auc", "aus"),
             ("ds", "is"), ("ds", "pdf"), ("is", "parse"), ("is", "ing"), ("as", "rl"), ("as", "agc"),
             ("aus", "jwt"), ("ds", "vr"), ("is", "cr"),
             ("as", "arr"), ("us", "urr")]:
    d.connect(p.rel("Dependency", K[a].el, K[b].el), K[a], K[b])
# DocumentService -> DocumentRepository routed left of PdfProcessor
d.connect(p.rel("Dependency", K["ds"].el, K["dr"].el), K["ds"], K["dr"],
          points=[(20, 150), (8, 150), (8, 440), (20, 440)])
d.connect(p.rel("Dependency", K["is"].el, K["tr"].el), K["is"], K["tr"],
          points=[(460, 145), (718, 145), (718, 440), (730, 440)])
d.connect(p.rel("Dependency", K["aus"].el, K["urr"].el), K["aus"], K["urr"],
          points=[(1450, 150), (1464, 150), (1464, 440), (1400, 440)])
note(d, "Tầng Controller (REST) → Service (nghiệp vụ, giao dịch) → Client/Repository (ai-service, Redis, PostgreSQL). Mỗi Repository là Spring Data JPA trên một bảng.", 20, 500, 900, 40)

# ---------------------------------------------------------------------------
# H2.14 ERD (Flyway V1 + V2)
# ---------------------------------------------------------------------------
d = p.diagram("H2_14_erd_postgresql", "ERDiagram")
T = {}


def table(key, name, cols, x, y, w=250):
    t = p.el("DBTable", name)
    for cname, ctype, length, pk, nullable in cols:
        p.el("DBColumn", cname, parent=t, type=ctype, length=36 if ctype == "char" else length, primaryKey=pk, nullable=nullable)
    T[key] = d.add(Shape(t, x, y, w, 26 + 19 * len(cols)))


# VP CE only knows generic JDBC types: uuid -> char(36), boolean -> bit, text -> clob.
V, I, B, TX, TS, BI = "varchar", "integer", "bit", "clob", "timestamp", "bigint"
UID = "char"
table("users", "users", [
    ("id", UID, 0, True, False), ("email", V, 255, False, False), ("full_name", V, 255, False, False),
    ("password", V, 255, False, False), ("role", V, 255, False, False), ("active", B, 0, False, True),
    ("created_at", TS, 0, False, False)], 20, 20)
table("documents", "documents", [
    ("id", UID, 0, True, False), ("document_code", V, 64, False, False), ("title", V, 255, False, False),
    ("category", V, 64, False, False), ("allowed_roles", V, 255, False, False), ("created_by", V, 255, False, False),
    ("created_at", TS, 0, False, False), ("updated_at", TS, 0, False, False)], 330, 20)
table("versions", "document_versions", [
    ("id", UID, 0, True, False), ("document_id", UID, 0, False, False), ("version_number", I, 0, False, False),
    ("status", V, 32, False, False), ("is_current", B, 0, False, False), ("page_count", I, 0, False, False),
    ("chunk_count", I, 0, False, False), ("file_hash", V, 64, False, False), ("file_name", V, 255, False, False),
    ("storage_path", V, 1024, False, False), ("error_message", V, 2000, False, True),
    ("created_by", V, 255, False, False), ("created_at", TS, 0, False, False)], 660, 20)
table("chunks", "document_chunks", [
    ("id", UID, 0, True, False), ("document_id", UID, 0, False, False), ("version_id", UID, 0, False, False),
    ("chunk_id", V, 128, False, False), ("chunk_index", I, 0, False, False), ("vector_id", V, 128, False, False),
    ("page_start", I, 0, False, False), ("page_end", I, 0, False, False), ("heading_level", I, 0, False, False),
    ("section_path", V, 512, False, False), ("content", TX, 0, False, False), ("highlight_json", TX, 0, False, True)],
    660, 330)
table("tasks", "ingestion_tasks", [
    ("id", V, 64, True, False), ("document_id", UID, 0, False, False), ("version_id", UID, 0, False, False),
    ("status", V, 32, False, False), ("step", I, 0, False, False), ("chunk_count", I, 0, False, False),
    ("message", V, 2000, False, True), ("updated_at", TS, 0, False, False)], 330, 330)
table("audit", "ai_audit_logs", [
    ("id", UID, 0, True, False), ("user_email", V, 255, False, False), ("user_role", V, 64, False, False),
    ("action", V, 32, False, False), ("query_text", V, 2000, False, False), ("document_id", V, 64, False, True),
    ("status", V, 32, False, False), ("model_used", V, 128, False, True), ("result_count", I, 0, False, False),
    ("latency_ms", BI, 0, False, False), ("created_at", TS, 0, False, False)], 20, 330)
for a, b in [("documents", "versions"), ("documents", "tasks"), ("versions", "chunks"), ("versions", "tasks")]:
    d.connect(p.rel("DBForeignKey", T[a].el, T[b].el), T[a], T[b])
note(d, "Quan hệ là khóa ngoại logic do ứng dụng bảo đảm; Flyway V1-V2 không tạo FOREIGN KEY vật lý. Kiểu hiển thị là kiểu chung của VP: char(36) = uuid, bit = boolean, clob = text của PostgreSQL.", 20, 590, 890, 40)

open("ch2.xml", "w", encoding="utf-8").write(p.xml())
print("diagrams:", [x.name for x in p.diagrams])
