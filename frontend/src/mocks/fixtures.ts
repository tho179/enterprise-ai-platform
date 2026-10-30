import dayjs from 'dayjs'
import type {
  AppNotification,
  Classification,
  DocumentChunk,
  DocumentDetail,
  DocumentSummary,
  DocumentVersion,
  HealthSnapshot,
  LeaveRequest,
  Ticket,
  User,
} from '@/api/types'

const now = dayjs()

function iso(daysAgo: number, hour = 9): string {
  return now.subtract(daysAgo, 'day').hour(hour).minute(0).second(0).toISOString()
}

function date(daysFromNow: number): string {
  return now.add(daysFromNow, 'day').format('YYYY-MM-DD')
}

export const demoUsers: User[] = [
  {
    id: 'u-admin',
    fullName: 'Nguyễn Minh Quân',
    email: 'admin@congty.vn',
    role: 'ADMIN',
    active: true,
    createdAt: iso(180),
  },
  {
    id: 'u-manager',
    fullName: 'Trần Thu Hà',
    email: 'manager@congty.vn',
    role: 'MANAGER',
    active: true,
    createdAt: iso(160),
  },
  {
    id: 'u-emp-1',
    fullName: 'Nguyễn Văn A',
    email: 'nva@congty.vn',
    role: 'EMPLOYEE',
    active: true,
    createdAt: iso(120),
  },
  {
    id: 'u-emp-2',
    fullName: 'Lê Hoàng B',
    email: 'lhb@congty.vn',
    role: 'EMPLOYEE',
    active: true,
    createdAt: iso(95),
  },
  {
    id: 'u-it',
    fullName: 'Phạm Đức Long',
    email: 'it@congty.vn',
    role: 'IT_SUPPORT',
    active: true,
    createdAt: iso(90),
  },
  {
    id: 'u-emp-3',
    fullName: 'Vũ Thị C',
    email: 'vtc@congty.vn',
    role: 'EMPLOYEE',
    active: false,
    createdAt: iso(60),
  },
]

export const demoAccounts = [
  { email: 'admin@congty.vn', password: 'Demo@123', userId: 'u-admin' },
  { email: 'manager@congty.vn', password: 'Demo@123', userId: 'u-manager' },
  { email: 'nva@congty.vn', password: 'Demo@123', userId: 'u-emp-1' },
  { email: 'it@congty.vn', password: 'Demo@123', userId: 'u-it' },
] as const

const nqldVersions: DocumentVersion[] = [
  {
    id: 'ver-nqld-2',
    documentId: 'doc-nqld',
    versionNumber: 2,
    status: 'INGESTED',
    chunkCount: 154,
    pageCount: 15,
    isCurrent: true,
    fileHash: '9f2a6c1b7d4e8a03',
    createdAt: iso(12, 10),
    createdBy: 'Nguyễn Minh Quân',
  },
  {
    id: 'ver-nqld-1',
    documentId: 'doc-nqld',
    versionNumber: 1,
    status: 'INGESTED',
    chunkCount: 152,
    pageCount: 15,
    isCurrent: false,
    fileHash: '4a8e2f0c9b7d1e65',
    createdAt: iso(45, 14),
    createdBy: 'Nguyễn Minh Quân',
  },
]

const dlctVersions: DocumentVersion[] = [
  {
    id: 'ver-dlct-1',
    documentId: 'doc-dlct',
    versionNumber: 1,
    status: 'INGESTED',
    chunkCount: 140,
    pageCount: 38,
    isCurrent: true,
    fileHash: 'c31b9e7a2f6d8401',
    createdAt: iso(38, 11),
    createdBy: 'Nguyễn Minh Quân',
  },
]

const csitVersions: DocumentVersion[] = [
  {
    id: 'ver-csit-1',
    documentId: 'doc-csit',
    versionNumber: 1,
    status: 'FAILED',
    chunkCount: 0,
    pageCount: 12,
    isCurrent: true,
    fileHash: 'e7d1a4c8b0f3926a',
    createdAt: iso(2, 16),
    createdBy: 'Nguyễn Minh Quân',
    errorMessage: 'Qdrant không phản hồi sau 30 giây. Pipeline đã dừng ở bước embedding.',
  },
]

const hdsdVersions: DocumentVersion[] = [
  {
    id: 'ver-hdsd-1',
    documentId: 'doc-hdsd',
    versionNumber: 1,
    status: 'PROCESSING',
    chunkCount: 0,
    pageCount: 8,
    isCurrent: true,
    fileHash: '0b6f2d9c5e8a1743',
    createdAt: iso(0, 8),
    createdBy: 'Nguyễn Minh Quân',
  },
]

export const demoDocuments: DocumentDetail[] = [
  {
    id: 'doc-nqld',
    documentCode: 'DOC-NQLD',
    title: 'Nội quy Lao động 2026',
    category: 'Nội quy',
    createdAt: iso(45, 14),
    updatedAt: iso(12, 10),
    createdBy: 'Nguyễn Minh Quân',
    currentVersion: nqldVersions[0],
    versions: nqldVersions,
  },
  {
    id: 'doc-dlct',
    documentCode: 'DOC-DLCT',
    title: 'Điều lệ Công ty 2021',
    category: 'Quy chế',
    createdAt: iso(80, 9),
    updatedAt: iso(38, 11),
    createdBy: 'Nguyễn Minh Quân',
    currentVersion: dlctVersions[0],
    versions: dlctVersions,
  },
  {
    id: 'doc-csit',
    documentCode: 'DOC-CSIT',
    title: 'Chính sách An toàn thông tin',
    category: 'Chính sách IT',
    createdAt: iso(10, 15),
    updatedAt: iso(2, 16),
    createdBy: 'Nguyễn Minh Quân',
    currentVersion: csitVersions[0],
    versions: csitVersions,
  },
  {
    id: 'doc-hdsd',
    documentCode: 'DOC-HDSD',
    title: 'Hướng dẫn kết nối VPN nội bộ',
    category: 'Hướng dẫn',
    createdAt: iso(0, 8),
    updatedAt: iso(0, 8),
    createdBy: 'Nguyễn Minh Quân',
    currentVersion: hdsdVersions[0],
    versions: hdsdVersions,
  },
]

type ChunkSeed = {
  id: string
  documentId: string
  sectionPath: string[]
  pageStart: number
  pageEnd: number
  headingLevel: number
  content: string
}

const chunkSeeds: ChunkSeed[] = [
  {
    id: 'nqld-15-1',
    documentId: 'doc-nqld',
    sectionPath: ['CHƯƠNG III: Thời giờ làm việc và nghỉ ngơi', 'Điều 15: Nghỉ phép năm'],
    pageStart: 12,
    pageEnd: 13,
    headingLevel: 2,
    content:
      'Người lao động làm việc đủ 12 tháng cho một người sử dụng lao động thì được nghỉ hằng năm, hưởng nguyên lương theo hợp đồng lao động là 12 ngày làm việc. Trường hợp người lao động làm việc chưa đủ 12 tháng thì số ngày nghỉ hằng năm được tính theo tỷ lệ tương ứng với số tháng làm việc.',
  },
  {
    id: 'nqld-15-2',
    documentId: 'doc-nqld',
    sectionPath: ['CHƯƠNG III: Thời giờ làm việc và nghỉ ngơi', 'Điều 15: Nghỉ phép năm', 'Khoản 2'],
    pageStart: 13,
    pageEnd: 13,
    headingLevel: 3,
    content:
      'Người lao động có thể thỏa thuận với người sử dụng lao động để nghỉ hằng năm thành nhiều lần hoặc nghỉ gộp tối đa 03 năm một lần. Khi nghỉ phép năm, người lao động cần gửi đề nghị trước ít nhất 03 ngày làm việc để bộ phận nhân sự và quản lý trực tiếp sắp xếp công việc.',
  },
  {
    id: 'nqld-5-1',
    documentId: 'doc-nqld',
    sectionPath: ['CHƯƠNG II: Tuyển dụng và thử việc', 'Điều 5: Thời gian thử việc'],
    pageStart: 4,
    pageEnd: 4,
    headingLevel: 2,
    content:
      'Thời gian thử việc không quá 60 ngày đối với công việc có chức danh nghề nghiệp cần trình độ chuyên môn, kỹ thuật từ cao đẳng trở lên; không quá 30 ngày đối với công việc có chức danh nghề nghiệp cần trình độ trung cấp, công nhân kỹ thuật; không quá 06 ngày làm việc đối với công việc khác.',
  },
  {
    id: 'nqld-5-2',
    documentId: 'doc-nqld',
    sectionPath: ['CHƯƠNG II: Tuyển dụng và thử việc', 'Điều 5: Thời gian thử việc', 'Khoản 3'],
    pageStart: 5,
    pageEnd: 5,
    headingLevel: 3,
    content:
      'Trong thời gian thử việc, người lao động được hưởng lương theo thỏa thuận nhưng ít nhất bằng 85% mức lương của công việc đó. Hai bên có thể chấm dứt hợp đồng thử việc trước thời hạn mà không cần báo trước, trừ trường hợp có thỏa thuận khác.',
  },
  {
    id: 'nqld-20-1',
    documentId: 'doc-nqld',
    sectionPath: ['CHƯƠNG IV: Làm việc từ xa', 'Điều 20: Điều kiện làm việc từ xa'],
    pageStart: 18,
    pageEnd: 19,
    headingLevel: 2,
    content:
      'Nhân viên được làm việc từ xa tối đa 02 ngày mỗi tuần nếu tính chất công việc cho phép và được quản lý trực tiếp phê duyệt trước. Nhân viên phải đảm bảo kết nối VPN nội bộ, không sử dụng thiết bị công cộng và không lưu trữ dữ liệu doanh nghiệp trên thiết bị cá nhân khi chưa mã hóa.',
  },
  {
    id: 'nqld-21-1',
    documentId: 'doc-nqld',
    sectionPath: ['CHƯƠNG IV: Làm việc từ xa', 'Điều 21: Thiết bị và bảo mật'],
    pageStart: 19,
    pageEnd: 20,
    headingLevel: 2,
    content:
      'Khi làm việc từ xa, nhân viên sử dụng thiết bị do công ty cấp. Trường hợp sử dụng thiết bị cá nhân, thiết bị phải được cài đặt phần mềm diệt virus, bật mã hóa ổ đĩa và đăng ký với bộ phận IT. Mọi sự cố mất thiết bị phải được báo ngay trong vòng 02 giờ.',
  },
  {
    id: 'nqld-16-1',
    documentId: 'doc-nqld',
    sectionPath: ['CHƯƠNG III: Thời giờ làm việc và nghỉ ngơi', 'Điều 16: Nghỉ lễ, tết'],
    pageStart: 13,
    pageEnd: 14,
    headingLevel: 2,
    content:
      'Người lao động được nghỉ làm việc và hưởng nguyên lương trong các ngày lễ, tết theo quy định của Bộ luật Lao động. Nếu ngày nghỉ lễ trùng vào ngày nghỉ hằng tuần thì người lao động được nghỉ bù vào ngày làm việc kế tiếp.',
  },
  {
    id: 'nqld-17-1',
    documentId: 'doc-nqld',
    sectionPath: ['CHƯƠNG III: Thời giờ làm việc và nghỉ ngơi', 'Điều 17: Nghỉ việc riêng'],
    pageStart: 14,
    pageEnd: 14,
    headingLevel: 2,
    content:
      'Người lao động được nghỉ việc riêng mà vẫn hưởng nguyên lương trong các trường hợp kết hôn, con đẻ hoặc con nuôi kết hôn, cha đẻ, mẹ đẻ, cha nuôi, mẹ nuôi, cha mẹ vợ hoặc cha mẹ chồng, vợ hoặc chồng, con đẻ, con nuôi chết. Thời gian nghỉ cụ thể theo quy định tại Điều 115 Bộ luật Lao động.',
  },
  {
    id: 'nqld-24-1',
    documentId: 'doc-nqld',
    sectionPath: ['CHƯƠNG V: Kỷ luật lao động', 'Điều 24: Các hình thức kỷ luật'],
    pageStart: 22,
    pageEnd: 23,
    headingLevel: 2,
    content:
      'Việc xử lý kỷ luật lao động được thực hiện theo nguyên tắc công bằng, minh bạch và có sự tham gia của tổ chức đại diện người lao động. Các hình thức kỷ luật gồm khiển trách, kéo dài thời hạn nâng lương không quá 06 tháng, cách chức và sa thải.',
  },
  {
    id: 'nqld-30-1',
    documentId: 'doc-nqld',
    sectionPath: ['CHƯƠNG VI: An toàn thông tin', 'Điều 30: Trách nhiệm bảo mật'],
    pageStart: 27,
    pageEnd: 28,
    headingLevel: 2,
    content:
      'Nhân viên không được chia sẻ tài khoản đăng nhập, mật khẩu hoặc mã xác thực hai lớp cho bất kỳ ai, kể cả đồng nghiệp. Khi phát hiện dấu hiệu truy cập bất thường, nhân viên phải đổi mật khẩu và gửi yêu cầu hỗ trợ IT ngay trong ngày.',
  },
  {
    id: 'dlct-3-1',
    documentId: 'doc-dlct',
    sectionPath: ['CHƯƠNG I: Quy định chung', 'Điều 3: Cơ cấu tổ chức'],
    pageStart: 6,
    pageEnd: 7,
    headingLevel: 2,
    content:
      'Công ty tổ chức theo mô hình trực tuyến chức năng, gồm Đại hội đồng cổ đông, Hội đồng quản trị, Ban Tổng Giám đốc và các phòng ban chuyên môn. Mỗi phòng ban có trưởng phòng chịu trách nhiệm trước Tổng Giám đốc về kết quả hoạt động.',
  },
  {
    id: 'dlct-12-1',
    documentId: 'doc-dlct',
    sectionPath: ['CHƯƠNG IV: Quản trị nội bộ', 'Điều 12: Quy trình ban hành quy chế'],
    pageStart: 21,
    pageEnd: 22,
    headingLevel: 2,
    content:
      'Quy chế nội bộ được ban hành sau khi lấy ý kiến các phòng ban liên quan và được Tổng Giám đốc phê duyệt. Văn bản có hiệu lực kể từ ngày ký, trừ trường hợp văn bản quy định ngày có hiệu lực khác. Mọi sửa đổi phải được công bố trên cổng thông tin nội bộ.',
  },
  {
    id: 'csit-2-1',
    documentId: 'doc-csit',
    sectionPath: ['CHƯƠNG I: Nguyên tắc chung', 'Điều 2: Phân loại thông tin'],
    pageStart: 3,
    pageEnd: 4,
    headingLevel: 2,
    content:
      'Thông tin doanh nghiệp được phân loại thành Công khai, Nội bộ, Mật và Tối mật. Tài liệu Nội bộ chỉ được chia sẻ trong phạm vi công ty. Tài liệu Mật và Tối mật phải được lưu trữ trên hệ thống được mã hóa và chỉ người có quyền truy cập mới được xem.',
  },
  {
    id: 'csit-7-1',
    documentId: 'doc-csit',
    sectionPath: ['CHƯƠNG III: Kiểm soát truy cập', 'Điều 7: Quản lý mật khẩu'],
    pageStart: 9,
    pageEnd: 10,
    headingLevel: 2,
    content:
      'Mật khẩu phải có tối thiểu 12 ký tự, bao gồm chữ hoa, chữ thường, số và ký tự đặc biệt. Không sử dụng lại mật khẩu đã dùng trong 05 lần gần nhất. Bật xác thực đa yếu tố cho tất cả tài khoản truy cập hệ thống nội bộ từ bên ngoài.',
  },
]

export const demoChunks: DocumentChunk[] = chunkSeeds.map((seed, index) => ({
  id: `chunk-${seed.id}`,
  chunkId: seed.id,
  documentId: seed.documentId,
  vectorId: `vec-${String(index + 1).padStart(4, '0')}`,
  pageStart: seed.pageStart,
  pageEnd: seed.pageEnd,
  headingLevel: seed.headingLevel,
  sectionPath: seed.sectionPath,
  content: seed.content,
}))

export const demoLeaveRequests: LeaveRequest[] = [
  {
    id: 'lv-001',
    userId: 'u-emp-1',
    employeeName: 'Nguyễn Văn A',
    startDate: date(4),
    endDate: date(6),
    totalDays: 3,
    reason: 'Giải quyết việc gia đình.',
    status: 'PENDING',
    createdAt: iso(1, 8),
  },
  {
    id: 'lv-002',
    userId: 'u-emp-2',
    employeeName: 'Lê Hoàng B',
    startDate: date(7),
    endDate: date(8),
    totalDays: 2,
    reason: 'Khám sức khỏe định kỳ tại bệnh viện.',
    status: 'PENDING',
    createdAt: iso(0, 10),
  },
  {
    id: 'lv-003',
    userId: 'u-emp-1',
    employeeName: 'Nguyễn Văn A',
    startDate: date(-30),
    endDate: date(-29),
    totalDays: 2,
    reason: 'Về quê dự đám cưới người thân.',
    status: 'APPROVED',
    createdAt: iso(35, 9),
    approverName: 'Trần Thu Hà',
    comment: 'Đã sắp xếp bàn giao công việc.',
    decidedAt: iso(33, 16),
  },
  {
    id: 'lv-004',
    userId: 'u-emp-2',
    employeeName: 'Lê Hoàng B',
    startDate: date(-12),
    endDate: date(-10),
    totalDays: 3,
    reason: 'Đi du lịch cùng gia đình.',
    status: 'REJECTED',
    createdAt: iso(18, 11),
    approverName: 'Trần Thu Hà',
    comment: 'Trùng lịch bàn giao dự án quan trọng, đề nghị chọn thời gian khác.',
    decidedAt: iso(16, 9),
  },
]

export const demoTickets: Ticket[] = [
  {
    id: 'it-007',
    ticketCode: 'IT-2026-0007',
    requesterId: 'u-emp-1',
    requesterName: 'Nguyễn Văn A',
    title: 'Không kết nối được VPN',
    description:
      'Từ sáng nay tôi không thể kết nối VPN để vào hệ thống nội bộ. Client báo lỗi "Authentication failed" dù mật khẩu vẫn đăng nhập được email.',
    attachmentName: 'vpn_error.png',
    category: 'NETWORK',
    priority: 'HIGH',
    aiConfidence: 0.87,
    status: 'OPEN',
    createdAt: iso(0, 8),
  },
  {
    id: 'it-008',
    ticketCode: 'IT-2026-0008',
    requesterId: 'u-emp-2',
    requesterName: 'Lê Hoàng B',
    title: 'Màn hình làm việc không lên nguồn',
    description:
      'Màn hình Dell tại bàn số 14 không lên nguồn sau khi chuyển chỗ ngồi. Đã thử cắm lại dây nguồn nhưng không có tín hiệu.',
    category: 'HARDWARE',
    priority: 'MEDIUM',
    aiConfidence: 0.74,
    status: 'IN_PROGRESS',
    assigneeId: 'u-it',
    assigneeName: 'Phạm Đức Long',
    createdAt: iso(1, 9),
  },
  {
    id: 'it-009',
    ticketCode: 'IT-2026-0009',
    requesterId: 'u-emp-1',
    requesterName: 'Nguyễn Văn A',
    title: 'Cần cấp lại quyền thư mục dự án',
    description:
      'Tôi được chuyển sang nhóm dự án EAKWP nhưng chưa có quyền truy cập thư mục tài liệu trên SharePoint.',
    category: 'ACCOUNT',
    priority: 'LOW',
    aiConfidence: 0.68,
    status: 'RESOLVED',
    assigneeId: 'u-it',
    assigneeName: 'Phạm Đức Long',
    resolutionNote: 'Đã thêm tài khoản vào nhóm quyền EAKWP-Readers và xác nhận với người dùng.',
    createdAt: iso(4, 10),
    resolvedAt: iso(3, 15),
  },
  {
    id: 'it-010',
    ticketCode: 'IT-2026-0010',
    requesterId: 'u-emp-2',
    requesterName: 'Lê Hoàng B',
    title: 'OneDrive không đồng bộ tài liệu',
    description:
      'Biểu tượng OneDrive hiển thị dấu X đỏ, các tệp mới không được đồng bộ lên cloud từ chiều qua.',
    category: 'SOFTWARE',
    priority: 'MEDIUM',
    aiConfidence: 0.81,
    status: 'OPEN',
    createdAt: iso(0, 13),
  },
  {
    id: 'it-011',
    ticketCode: 'IT-2026-0011',
    requesterId: 'u-emp-1',
    requesterName: 'Nguyễn Văn A',
    title: 'Máy in tầng 3 bị kẹt giấy',
    description: 'Máy in HP tại khu vực tầng 3 báo kẹt giấy ở khay 2, đã mở kiểm tra nhưng không thấy giấy.',
    category: 'HARDWARE',
    priority: 'LOW',
    aiConfidence: 0.9,
    status: 'CLOSED',
    assigneeId: 'u-it',
    assigneeName: 'Phạm Đức Long',
    resolutionNote: 'Đã lấy mảnh giấy kẹt trong bộ phận kéo giấy và chạy test in thành công.',
    createdAt: iso(10, 9),
    resolvedAt: iso(9, 11),
  },
  {
    id: 'it-012',
    ticketCode: 'IT-2026-0012',
    requesterId: 'u-emp-1',
    requesterName: 'Nguyễn Văn A',
    title: 'Không nhận được email nội bộ',
    description:
      'Từ 9h sáng tôi không nhận được email từ đồng nghiệp trong công ty, trong khi email bên ngoài vẫn hoạt động bình thường.',
    category: 'NETWORK',
    priority: 'URGENT',
    aiConfidence: 0.55,
    status: 'REOPENED',
    assigneeId: 'u-it',
    assigneeName: 'Phạm Đức Long',
    createdAt: iso(6, 9),
    resolvedAt: iso(5, 16),
  },
  {
    id: 'it-013',
    ticketCode: 'IT-2026-0013',
    requesterId: 'u-emp-2',
    requesterName: 'Lê Hoàng B',
    title: 'Đăng nhập ERP báo sai mật khẩu',
    description:
      'Hệ thống ERP liên tục báo sai mật khẩu dù tôi vừa đổi mật khẩu theo hướng dẫn. Tài khoản có thể đã bị khóa.',
    category: 'ACCOUNT',
    priority: 'HIGH',
    aiConfidence: 0.42,
    status: 'OPEN',
    createdAt: iso(0, 14),
  },
]

export const demoNotifications: AppNotification[] = [
  {
    id: 'nt-1',
    title: 'Đơn nghỉ phép đã được duyệt',
    body: 'Đơn nghỉ 2 ngày của bạn đã được Trần Thu Hà phê duyệt.',
    createdAt: iso(0, 9),
    read: false,
    href: '/leave',
  },
  {
    id: 'nt-2',
    title: 'Ticket IT-2026-0007 đã được tiếp nhận',
    body: 'Phạm Đức Long đang xử lý yêu cầu hỗ trợ VPN của bạn.',
    createdAt: iso(0, 8),
    read: false,
    href: '/tickets',
  },
  {
    id: 'nt-3',
    title: 'Tài liệu mới đã nạp thành công',
    body: 'Nội quy Lao động 2026 phiên bản 2 đã sẵn sàng trong kho tri thức.',
    createdAt: iso(12, 10),
    read: true,
    href: '/documents/doc-nqld',
  },
  {
    id: 'nt-4',
    title: 'Có 2 đơn nghỉ phép chờ duyệt',
    body: 'Hàng đợi phê duyệt của bạn đang có 2 đơn mới.',
    createdAt: iso(1, 8),
    read: true,
    href: '/approvals',
  },
]

export const demoHealth: HealthSnapshot = {
  ai: 'healthy',
  qdrantVectors: 152,
  model: 'paraphrase-multilingual-MiniLM-L12-v2',
  latencyMs: 42,
}

export const demoClassification: Classification = {
  category: 'NETWORK',
  priority: 'HIGH',
  confidence: 0.87,
}

export const demoDocumentSummaries: DocumentSummary[] = demoDocuments.map(
  ({ versions: _versions, ...summary }) => summary,
)
