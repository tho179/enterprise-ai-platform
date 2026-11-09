-- Roles allowed to read a document; '*' means every signed-in user.
ALTER TABLE documents ADD COLUMN allowed_roles varchar(255) NOT NULL DEFAULT '*';

CREATE TABLE ai_audit_logs (
    id uuid PRIMARY KEY,
    user_email varchar(255) NOT NULL,
    user_role varchar(64) NOT NULL,
    action varchar(32) NOT NULL,
    query_text varchar(2000) NOT NULL,
    document_id varchar(64),
    status varchar(32) NOT NULL,
    model_used varchar(128),
    result_count integer NOT NULL,
    latency_ms bigint NOT NULL,
    created_at timestamp(6) without time zone NOT NULL
);

CREATE INDEX idx_ai_audit_created ON ai_audit_logs (created_at DESC);
