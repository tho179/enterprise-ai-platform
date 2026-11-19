"""Sequence diagrams of the thesis (Chapter 2 and Chapter 4), taken from the code.

    python seq_specs.py <out_dir>   -> <out_dir>/<diagram>.xml, one VP project per diagram
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from seqgen import Seq  # noqa: E402


def login():
    # frontend LoginPage -> AuthController.login -> AuthService.login (auth/AuthService.java)
    s = Seq("H2_9_tuan_tu_dang_nhap", [
        ("Người dùng", "actor"), ("LoginPage", "boundary"), ("AuthController", "control"),
        ("AuthService", "control"), ("UserRepository", "entity"), ("JwtService", "control")])
    s.call(0, 1, "nhập email, mật khẩu")
    s.call(1, 2, "POST /api/auth/login")
    s.call(2, 3, "login(request)")
    s.call(3, 4, "findByEmail(email)")
    s.ret(4, 3, "Optional<User>")
    s.self_call(3, "passwordEncoder.matches()")
    with s.fragment("alt") as f:
        f.operand("không có email hoặc sai mật khẩu")
        s.ret(3, 2, "401 UNAUTHORIZED")
        f.operand("tài khoản bị khóa")
        s.ret(3, 2, "403 FORBIDDEN")
        f.operand("hợp lệ")
        s.call(3, 5, "generateToken(email, role)")
        s.ret(5, 3, "token")
        s.ret(3, 2, "AuthResponse")
    s.ret(2, 1, "HTTP 200 / 401 / 403")
    s.ret(1, 0, "vào trang theo vai trò hoặc báo lỗi")
    return s


def upload():
    # DocumentController.upload (202) -> DocumentService.upload -> IngestionService.process (@Async)
    s = Seq("H2_10_tuan_tu_tai_len_nap", [
        ("Quản trị viên", "actor"), ("UploadPage", "boundary"), ("DocumentController", "control"),
        ("DocumentService", "control"), ("IngestionService", "control"),
        ("DocumentVersionRepository", "entity"), ("DocumentChunkRepository", "entity"), ("ai-service", "plain")])
    s.call(0, 1, "chọn PDF, nhập mã, tiêu đề, quyền")
    s.call(1, 2, "POST /api/documents/upload")
    s.call(2, 3, "upload(code, title, category, roles, file)")
    with s.fragment("alt") as f:
        f.operand("mã tài liệu đã tồn tại")
        s.ret(3, 2, "409 CONFLICT")
        f.operand("mã mới")
        s.self_call(3, "store(file): lưu tệp, SHA-256")
        s.call(3, 5, "save(version PROCESSING)")
        s.async_call(3, 4, "process(taskId)")
        s.ret(3, 2, "UploadTicketDto")
    s.ret(2, 1, "202 ACCEPTED {taskId}")
    s.call(4, 7, "POST /api/v1/extract")
    s.ret(7, 4, "trang, chunk, tọa độ")
    s.call(4, 6, "saveAll(chunks)")
    with s.fragment("loop") as f:
        f.operand("từng lô chunk")
        s.call(4, 7, "POST /api/v1/ingest")
    s.call(4, 5, "save(version INGESTED, hiện hành)")
    s.ret(1, 0, "tiến trình nạp 5/5")
    return s


def chat():
    # AiGatewayController.chat -> AiGatewayService.forward (rate limit, roles, audit)
    s = Seq("H2_11_tuan_tu_hoi_dap", [
        ("Người dùng", "actor"), ("ChatPage", "boundary"), ("AiGatewayController", "control"),
        ("AiGatewayService", "control"), ("AiRateLimiter", "control"), ("Redis", "plain"),
        ("ai-service", "plain"), ("AiAuditLogRepository", "entity")])
    s.call(0, 1, "nhập câu hỏi")
    s.call(1, 2, "POST /api/ai/chat (JWT)")
    s.call(2, 3, "chat(request)")
    s.call(3, 4, "allow(email)")
    s.call(4, 5, "INCR ai:rate:{email}:{phút}")
    s.ret(5, 4, "count")
    s.ret(4, 3, "count ≤ 30")
    with s.fragment("alt") as f:
        f.operand("vượt 30 yêu cầu/phút")
        s.call(3, 7, "save(RATE_LIMITED)")
        s.ret(3, 2, "429 TOO_MANY_REQUESTS")
        f.operand("trong giới hạn")
        s.self_call(3, "gắn user_roles theo vai trò")
        s.call(3, 6, "POST /api/v1/chat/ask")
        s.ret(6, 3, "answer, citations, agent_trace")
        s.call(3, 7, "save(OK, model_used, latency)")
        s.ret(3, 2, "response")
    s.ret(2, 1, "HTTP 200 / 429")
    s.ret(1, 0, "câu trả lời và trích dẫn")
    return s


def rag_kb():
    # ai-service RAGService.ask: retrieve_hits (Qdrant + graph_search + rerank) -> select_evidence -> LLM
    s = Seq("H4_7_bce", [
        ("Người dùng", "actor"), ("ChatPage", "boundary"), ("AiGatewayService", "control"),
        ("RAGService", "control"), ("Qdrant", "plain"), ("Neo4j (KB)", "plain"),
        ("Cross-encoder", "control"), ("LLM", "plain")])
    s.call(0, 1, "câu hỏi")
    s.call(1, 2, "POST /api/ai/chat (JWT)")
    s.call(2, 3, "POST /api/v1/chat/ask + user_roles")
    s.self_call(3, "embed_query(query): E5-Small")
    s.call(3, 4, "search(60 ứng viên, lọc allowed_roles)")
    s.ret(4, 3, "ứng viên, payload")
    s.call(3, 5, "graph_search(query, 5 chunk mồi)")
    s.ret(5, 3, "chunk liên quan")
    s.self_call(3, "_fuse_hits(): RRF, trọng số đồ thị 0,2")
    s.call(3, 6, "rerank(query, 10 ứng viên)")
    s.ret(6, 3, "rerank_score")
    s.self_call(3, "select_evidence()")
    with s.fragment("alt") as f:
        f.operand("có bằng chứng qua cổng")
        s.call(3, 7, "ngữ cảnh [n], câu hỏi")
        s.ret(7, 3, "câu trả lời có [n]")
        f.operand("không đủ bằng chứng")
        s.self_call(3, "từ chối, citations rỗng")
    s.ret(3, 2, "AskResponse")
    s.ret(2, 1, "200 OK")
    s.ret(1, 0, "câu trả lời, trích dẫn")
    return s


def users():
    # UserController / UserService (POST, PATCH need ADMIN in SecurityConfig)
    s = Seq("TT_quan_ly_nguoi_dung", [
        ("Quản trị viên", "actor"), ("UsersPage", "boundary"), ("UserController", "control"),
        ("UserService", "control"), ("UserRepository", "entity")])
    s.call(0, 1, "nhập email, họ tên, vai trò")
    s.call(1, 2, "POST /api/users")
    s.call(2, 3, "createUser(request)")
    s.call(3, 4, "existsByEmail(email)")
    s.ret(4, 3, "true / false")
    with s.fragment("alt") as f:
        f.operand("email đã tồn tại")
        s.ret(3, 2, "409 CONFLICT")
        f.operand("email mới")
        s.call(3, 4, "save(user, mật khẩu BCrypt)")
        s.ret(4, 3, "User")
        s.ret(3, 2, "UserResponse")
    s.ret(2, 1, "201 CREATED / 409")
    s.call(0, 1, "khóa tài khoản")
    s.call(1, 2, "PATCH /api/users/{id}/status")
    s.call(2, 3, "setActive(id, false)")
    s.call(3, 4, "findById(id)")
    s.ret(4, 3, "User")
    s.call(3, 4, "save(user)")
    s.ret(3, 2, "UserResponse")
    s.ret(2, 1, "200 OK")
    return s


def new_version():
    # DocumentService.uploadVersion / setCurrent
    s = Seq("TT_phien_ban_moi", [
        ("Quản trị viên", "actor"), ("DocumentDetailPage", "boundary"), ("DocumentController", "control"),
        ("DocumentService", "control"), ("DocumentVersionRepository", "entity"), ("IngestionService", "control"),
        ("DocumentChunkRepository", "entity"), ("ai-service", "plain")])
    s.call(0, 1, "chọn tệp phiên bản mới")
    s.call(1, 2, "POST /api/documents/{id}/versions")
    s.call(2, 3, "uploadVersion(id, file)")
    s.call(3, 4, "findByDocumentId(id)")
    s.ret(4, 3, "các phiên bản")
    with s.fragment("alt") as f:
        f.operand("có phiên bản PROCESSING")
        s.ret(3, 2, "409 CONFLICT")
        f.operand("không")
        s.call(3, 4, "save(phiên bản N + 1, PROCESSING)")
        s.async_call(3, 5, "process(taskId, false)")
        s.ret(3, 2, "UploadTicketDto")
    s.ret(2, 1, "202 ACCEPTED / 409")
    s.call(0, 1, "đặt phiên bản làm hiện hành")
    s.call(1, 2, "PATCH /api/documents/versions/{vid}/current")
    s.call(2, 3, "setCurrent(vid)")
    s.call(3, 4, "findById(vid)")
    s.ret(4, 3, "phiên bản")
    with s.fragment("alt") as f:
        f.operand("chưa INGESTED")
        s.ret(3, 2, "409 CONFLICT")
        f.operand("INGESTED")
        s.call(3, 6, "findByVersionIdOrderByChunkIndexAsc(vid)")
        s.ret(6, 3, "chunks")
        s.call(3, 7, "POST /api/v1/ingest (chunk của vid)")
        s.call(3, 4, "save(is_current) cho mọi phiên bản")
        s.call(3, 5, "dropSupersededVectors(id, vid)")
        s.call(5, 7, "DELETE /api/v1/ingest/documents/{id}?version_id=")
        s.ret(3, 2, "DocumentVersionDto")
    s.ret(2, 1, "200 OK / 409 / 502")
    return s


def retry():
    # DocumentService.retry (FAILED) and reindex (INGESTED, current)
    s = Seq("TT_thu_lai_nap_lai", [
        ("Quản trị viên", "actor"), ("DocumentDetailPage", "boundary"), ("DocumentController", "control"),
        ("DocumentService", "control"), ("DocumentVersionRepository", "entity"), ("IngestionService", "control"),
        ("DocumentChunkRepository", "entity")])
    s.call(0, 1, "bấm Thử lại")
    s.call(1, 2, "POST /api/documents/versions/{vid}/retry")
    s.call(2, 3, "retry(vid)")
    s.call(3, 4, "findById(vid)")
    s.ret(4, 3, "phiên bản")
    with s.fragment("alt") as f:
        f.operand("không phải FAILED")
        s.ret(3, 2, "409 CONFLICT")
        f.operand("tệp gốc không còn")
        s.ret(3, 2, "400 BAD_REQUEST")
        f.operand("hợp lệ")
        s.call(3, 6, "deleteByVersionId(vid)")
        s.call(3, 4, "save(status = PROCESSING)")
        s.async_call(3, 5, "process(taskId, false)")
        s.ret(3, 2, "UploadTicketDto")
    s.ret(2, 1, "202 ACCEPTED / 409 / 400")
    return s


def search():
    # AiGatewayService.search -> ai-service /api/v1/search (VectorRetriever.search, reranker on)
    s = Seq("TT_tim_kiem", [
        ("Người dùng", "actor"), ("SearchPage", "boundary"), ("AiGatewayController", "control"),
        ("AiGatewayService", "control"), ("AiRateLimiter", "control"), ("ai-service", "plain"),
        ("AiAuditLogRepository", "entity")])
    s.call(0, 1, "nhập từ khóa")
    s.call(1, 2, "POST /api/ai/search")
    s.call(2, 3, "search(request)")
    s.call(3, 4, "allow(email)")
    s.ret(4, 3, "true / false")
    with s.fragment("alt") as f:
        f.operand("vượt 30 yêu cầu/phút")
        s.call(3, 6, "save(RATE_LIMITED)")
        s.ret(3, 2, "429 TOO_MANY_REQUESTS")
        f.operand("trong giới hạn")
        s.call(3, 5, "POST /api/v1/search + user_roles")
        s.ret(5, 3, "data: đoạn, điểm, trang")
        s.call(3, 6, "save(OK, số kết quả)")
        s.ret(3, 2, "response")
    s.ret(2, 1, "HTTP 200 / 429")
    s.ret(1, 0, "danh sách đoạn")
    return s


def delete():
    # DocumentService.delete (@Transactional)
    s = Seq("TT_xoa_tai_lieu", [
        ("Quản trị viên", "actor"), ("DocumentsPage", "boundary"), ("DocumentController", "control"),
        ("DocumentService", "control"), ("ai-service", "plain"), ("IngestionTaskRepository", "entity"),
        ("DocumentChunkRepository", "entity"), ("DocumentVersionRepository", "entity"), ("DocumentRepository", "entity")])
    s.call(0, 1, "chọn tài liệu, xác nhận Xóa")
    s.call(1, 2, "DELETE /api/documents [ids]")
    s.call(2, 3, "delete(ids)")
    with s.fragment("loop") as f:
        f.operand("mỗi tài liệu: kiểm tra đang nạp")
        s.call(3, 5, "existsByDocumentIdAndStatus(PROCESSING)")
        s.ret(5, 3, "true / false")
    with s.fragment("loop") as f:
        f.operand("mỗi tài liệu: xóa vector trước")
        s.call(3, 4, "DELETE /api/v1/ingest/documents/{id}")
        s.ret(4, 3, "kết quả")
    with s.fragment("loop") as f:
        f.operand("mỗi tài liệu: xóa tệp và bản ghi")
        s.self_call(3, "xóa tệp PDF các phiên bản")
        s.call(3, 5, "deleteByDocumentId(id)")
        s.call(3, 6, "deleteByDocumentId(id)")
        s.call(3, 7, "deleteByDocumentId(id)")
        s.call(3, 8, "delete(document)")
    s.ret(3, 2, "số tài liệu đã xóa")
    s.ret(2, 1, "200 {deleted} / 409 / 502")
    s.ret(1, 0, "làm mới danh sách")
    return s


ALL = [login, upload, chat, rag_kb, users, new_version, retry, search, delete]

if __name__ == "__main__":
    out = Path(sys.argv[1])
    out.mkdir(parents=True, exist_ok=True)
    for make in ALL:
        s = make()
        (out / f"{s.name}.xml").write_text(s.xml(), encoding="utf-8")
        print("wrote", s.name)
