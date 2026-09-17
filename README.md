# Enterprise AI Platform

Ðây là d? án h? th?ng AI da n?n t?ng, du?c t? ch?c du?i d?ng monorepo v?i các thành ph?n chính sau:

## C?u trúc thu m?c

- \ackend/\: Ch?a mã ngu?n d? án Spring Boot (Core APIs).
- \i-service/\: Ch?a các d?ch v? Python FastAPI x? lý RAG và tích h?p LLM.
- \rontend/\: Giao di?n ngu?i dùng vi?t b?ng React (S? phát tri?n sau).
- \infrastructure/\: Các script và t?p c?u hình tri?n khai, database, CI/CD.
- \docs/\: Tài li?u ki?n trúc, API, so d? co s? d? li?u.

## Ch?y các d?ch v? n?i b? (Infrastructure)

Ð? kh?i d?ng Database (PostgreSQL), Redis và Qdrant, s? d?ng Docker Compose:

\\\ash
docker-compose up -d
\\\

