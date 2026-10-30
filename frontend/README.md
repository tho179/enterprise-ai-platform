# EAKWP Console v1

Giao diện vận hành cho **Enterprise AI Knowledge Workspace Platform**: hỏi đáp tài liệu nội bộ có trích dẫn, quản lý kho tri thức, nghỉ phép, phê duyệt và yêu cầu IT trong một console thống nhất.

Frontend được xây dựng theo hướng sản phẩm doanh nghiệp Việt Nam: mật độ thông tin cao, phân quyền theo vai trò, trạng thái hệ thống luôn hiển thị và không dùng các hiệu ứng trình diễn quá mức.

## Thành phần

| Nhóm | Màn hình |
| --- | --- |
| Truy cập | Đăng nhập, Không có quyền, Không tìm thấy |
| Không gian làm việc | Tổng quan, Chat có trích dẫn, Tìm kiếm tri thức |
| Kho tài liệu | Danh sách tài liệu, Chi tiết tài liệu, Tải tài liệu |
| Quản trị | Người dùng (Admin) |
| Nghiệp vụ | Nghỉ phép, Phê duyệt đơn (Manager) |
| Hỗ trợ IT | Yêu cầu của tôi, Hàng đợi IT (IT Support) |

Điều hướng theo vai trò:

- **Admin** → Tổng quan, Kho tài liệu, Người dùng, Chat, Tìm kiếm
- **Manager** → Tổng quan, Chat, Tìm kiếm, Nghỉ phép, Phê duyệt
- **IT Support** → Tổng quan, Chat, Tìm kiếm, Yêu cầu IT, Hàng đợi IT
- **Employee** → Tổng quan, Chat, Tìm kiếm, Nghỉ phép, Yêu cầu IT

## Công nghệ

- Vite + React 19 + TypeScript strict
- Ant Design 6, theme token riêng, font Be Vietnam Pro
- React Router 7 với route guard theo vai trò
- TanStack Query 5 cho cache và trạng thái máy chủ
- Axios cho API thật; MSW 3 cho các module chưa có backend
- Vitest + Testing Library cho unit test
- Playwright + Chrome cho kiểm thử luồng giao diện

## Chạy nhanh

Yêu cầu Node.js 22+ (khuyến nghị 24) và npm.

```bash
cd frontend
npm ci
npm run dev
```

Mở `http://localhost:5173`.

Các API được proxy khi chạy dev (trỏ IPv4 để tránh dịch vụ cũ trong WSL):

- `/api` → `http://127.0.0.1:8080`
- `/ai-api` → `http://127.0.0.1:8001` (bỏ tiền tố `/ai-api`)

## Tài khoản demo

Mật khẩu chung: `Demo@123`

| Vai trò | Email |
| --- | --- |
| Admin | `admin@congty.vn` |
| Manager | `manager@congty.vn` |
| Employee | `nva@congty.vn` |
| IT Support | `it@congty.vn` |

Backend tạo sẵn 6 tài khoản khi database trống (4 tài khoản trên cùng `lhb@congty.vn`, `vtc@congty.vn`). Trang đăng nhập có nút chọn nhanh. Nếu backend chưa sẵn sàng, chế độ demo tự dùng phiên đăng nhập cục bộ để xem giao diện.

## Biến môi trường

Tạo `.env.local` từ `.env.example` khi cần thay đổi cấu hình.

| Biến | Mặc định | Ý nghĩa |
| --- | --- | --- |
| `VITE_API_BASE_URL` | rỗng | Base URL backend; rỗng nghĩa là dùng `/api` cùng origin |
| `VITE_AI_BASE_URL` | `/ai-api` | Base URL dịch vụ AI |
| `VITE_USE_MOCKS` | `true` ở dev/demo | Bật MSW và dữ liệu dự phòng cho các module chưa có API |

Khi backend và AI service đã hoàn chỉnh, đặt `VITE_USE_MOCKS=false` rồi build lại. Xem mục **Chế độ dữ liệu** bên dưới.

## Chế độ dữ liệu

Frontend dùng mô hình hybrid, ưu tiên API thật và chỉ fallback khi được phép:

- **API thật:** đăng nhập, người dùng, tài liệu (danh sách, chi tiết, phiên bản, chunk, tải lên, trạng thái nạp), health check.
- **MSW:** nghỉ phép, phê duyệt, ticket IT, thông báo — các module backend chưa triển khai.
- **AI service:** chat và tìm kiếm gọi `/ai-api` thật; nếu endpoint không khả dụng (404/không kết nối/5xx) và `VITE_USE_MOCKS=true`, dùng câu trả lời trích xuất từ fixture.
- **Đăng nhập demo:** backend tự tạo 6 tài khoản mẫu khi database trống. Nếu backend không khả dụng, nút đăng nhập nhanh vẫn tạo phiên cục bộ để xem giao diện; tài liệu và người dùng sẽ báo lỗi kết nối thay vì giả lập.
- **Người dùng:** danh sách và thao tác quản trị gọi backend thật; chỉ fallback trong bộ nhớ khi backend lỗi và đang bật mock.

Trạng thái MSW được giữ trong bộ nhớ trình duyệt và **reset khi tải lại trang**. Chat được lưu riêng theo người dùng trong `localStorage` tại khóa `eakwp.chat.<userId>`.

Khi tắt mock, mọi lỗi API sẽ hiển thị cho người dùng thay vì fallback.

## Nạp tài liệu PDF

Admin tải PDF tại **Kho tài liệu → Tải tài liệu**. Luồng thật chạy như sau:

1. `POST /api/documents/upload` trả `202` kèm `taskId`, `documentId`, `versionId`.
2. Backend lưu tệp vào volume `backend_uploads`, tính SHA-256, rồi xử lý bất đồng bộ.
3. Backend gọi AI service `POST /api/v1/extract` để trích văn bản từng trang; trang scan/ảnh được OCR tiếng Việt bằng Tesseract, trang có lớp văn bản dùng PyMuPDF. Nếu AI service không khả dụng, backend quay về Apache PDFBox cho PDF có lớp văn bản.
4. Nội dung được chia đoạn khoảng 1.400 ký tự, chồng lấn 160 ký tự, giữ số trang.
5. Chunk được lưu vào PostgreSQL (`documents`, `document_versions`, `document_chunks`).
6. Backend gửi chunk theo lô 32 sang AI service `POST /api/v1/ingest` để tạo embedding và ghi Qdrant.
7. Giao diện poll `GET /api/ai/status/{taskId}` đến khi `INGESTED` hoặc `FAILED`.

Ràng buộc hiện tại:

- Nhận PDF tối đa 25 MB, bao gồm PDF scan thuần ảnh (OCR qua AI service).
- Mã tài liệu là duy nhất, chỉ gồm chữ, số và dấu gạch ngang.
- Phiên bản lỗi có thể nạp lại bằng `POST /api/documents/versions/{versionId}/retry`.
- Phiên bản mới dùng `POST /api/documents/{id}/versions`; chỉ phiên bản `INGESTED` mới được đặt làm hiện hành.

API tài liệu: `GET /api/documents`, `GET /api/documents/{id}`, `GET /api/documents/{id}/versions`, `GET /api/documents/{id}/chunks`, `POST /api/documents/upload`, `POST /api/documents/{id}/versions`, `POST /api/documents/versions/{versionId}/retry`, `PATCH /api/documents/versions/{versionId}/current`.

## Cấu trúc thư mục

```text
frontend/
├─ e2e/                  # Playwright flows
├─ public/               # mockServiceWorker.js, favicon
├─ src/
│  ├─ api/               # axios clients, API modules, kiểu dữ liệu
│  ├─ app/               # router, providers
│  ├─ auth/              # AuthContext, route guards
│  ├─ components/        # layout, citations, UI dùng chung
│  ├─ lib/               # constants, format, dates, permissions, storage
│  ├─ mocks/             # fixture, fallback chat/search, MSW handlers
│  ├─ pages/             # 12 màn hình + lỗi
│  ├─ styles/            # global.css, theme token
│  └─ test/              # Vitest setup
├─ Dockerfile
├─ nginx.conf
├─ playwright.config.ts
└─ vitest.config.ts
```

## Kiểm thử

```bash
npm run typecheck   # TypeScript strict
npm test            # unit tests (Vitest)
npm run build       # typecheck + production build
npm run e2e         # Playwright, dùng Chrome đã cài
```

E2E bao phủ: đăng nhập bốn vai trò, điều hướng mặc định, trang tài liệu thật, người dùng, drawer lịch sử chat, hàng đợi IT, chặn truy cập trái quyền và sidebar dạng drawer ở tablet.

Nếu máy chưa có Chrome, cài Chromium của Playwright rồi bỏ `channel: 'chrome'` trong `playwright.config.ts`:

```bash
npx playwright install chromium
```

## Docker

Từ thư mục gốc dự án, khởi động toàn bộ cụm (PostgreSQL, Qdrant, AI service, backend, frontend):

```bash
docker compose up -d --build
```

Mở `http://localhost:3000` cho console và `http://localhost:8080` cho backend API. Có thể đổi cổng bằng `FRONTEND_PORT` và `BACKEND_PORT`.

Backend tự tạo tài khoản demo khi database trống và lưu PDF gốc trong volume `backend_uploads`. Dữ liệu tài liệu/chunk nằm trong PostgreSQL; vector nằm trong Qdrant.

Image dùng build nhiều tầng: Node để build, nginx để phục vụ SPA và proxy:

- `/api/` → `backend:8080`
- `/ai-api/` → `ai-service:8001/`

Build arg `VITE_USE_MOCKS` mặc định `true` cho bản demo. Để dùng API thật:

```bash
VITE_USE_MOCKS=false docker compose build frontend
docker compose up frontend
```

Trên Windows PowerShell:

```powershell
$env:VITE_USE_MOCKS="false"; docker compose build frontend
docker compose up frontend
```

Lưu ý: `VITE_*` là biến build-time, phải build lại image khi thay đổi.

## Quy ước giao diện

- Khung desktop: rail 56px + sidebar ngữ cảnh 264px + topbar 56px + vùng nội dung + thanh trạng thái 28px.
- Inspector trích dẫn 340px ở màn hình ≥1200px; dưới ngưỡng này chuyển thành Drawer.
- Dưới 1600px, danh sách phiên chat chuyển vào Drawer **Lịch sử** để giữ vùng đọc rộng.
- Dưới 1024px, sidebar ngữ cảnh chuyển thành drawer; dưới 768px, rail chuyển thành thanh điều hướng đáy.
- Nội dung chính cuộn độc lập trong khung 100vh; topbar, rail, sidebar và status bar luôn cố định.

Màu chủ đạo: `#0B4F7A`; sidebar: `#0B1F33`; nền: `#F6F8FA`; viền: `#E2E8F0`; bán kính: 8px.

## Giới hạn đã biết

- PDF scan được OCR qua AI service (Tesseract tiếng Việt); chất lượng trích xuất phụ thuộc độ rõ của bản scan. Nếu AI service không khả dụng, chỉ PDF có lớp văn bản mới nạp được bằng PDFBox.
- Nghỉ phép, phê duyệt, ticket và thông báo vẫn dùng MSW cho đến khi backend có endpoint tương ứng; dữ liệu các module này reset khi tải lại trang.
- Nếu AI service không có `OPENAI_API_KEY`, chat trả câu trả lời trích xuất từ chunk thay vì sinh văn bản bằng LLM.
- MSW không mô phỏng phân quyền phía máy chủ; backend đã chặn upload/quản trị người dùng bằng JWT + role, nhưng các module mock chỉ được bảo vệ phía giao diện.
- Tệp tải lên giới hạn 25 MB, chỉ nhận PDF; giới hạn này được kiểm tra ở cả trang tải mới và trang thêm phiên bản.
- Bundle Ant Design lớn (~1,3 MB) và Vite có cảnh báo chunk; có thể tách động theo màn hình nếu cần tối ưu tải trang.
