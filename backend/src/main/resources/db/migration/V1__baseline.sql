-- Schema as it existed when Flyway was introduced.

CREATE TABLE document_chunks (
    id uuid NOT NULL,
    chunk_id character varying(128) NOT NULL,
    chunk_index integer NOT NULL,
    content text NOT NULL,
    document_id uuid NOT NULL,
    heading_level integer NOT NULL,
    page_end integer NOT NULL,
    page_start integer NOT NULL,
    section_path character varying(512) NOT NULL,
    vector_id character varying(128) NOT NULL,
    version_id uuid NOT NULL,
    highlight_json text
);

CREATE TABLE document_versions (
    id uuid NOT NULL,
    chunk_count integer NOT NULL,
    created_at timestamp(6) without time zone NOT NULL,
    created_by character varying(255) NOT NULL,
    is_current boolean NOT NULL,
    document_id uuid NOT NULL,
    error_message character varying(2000),
    file_hash character varying(64) NOT NULL,
    file_name character varying(255) NOT NULL,
    page_count integer NOT NULL,
    status character varying(32) NOT NULL,
    storage_path character varying(1024) NOT NULL,
    version_number integer NOT NULL
);

CREATE TABLE documents (
    id uuid NOT NULL,
    category character varying(64) NOT NULL,
    created_at timestamp(6) without time zone NOT NULL,
    created_by character varying(255) NOT NULL,
    document_code character varying(64) NOT NULL,
    title character varying(255) NOT NULL,
    updated_at timestamp(6) without time zone NOT NULL
);

CREATE TABLE ingestion_tasks (
    id character varying(64) NOT NULL,
    chunk_count integer NOT NULL,
    document_id uuid NOT NULL,
    message character varying(2000),
    status character varying(32) NOT NULL,
    step integer NOT NULL,
    updated_at timestamp(6) without time zone NOT NULL,
    version_id uuid NOT NULL
);

CREATE TABLE users (
    id uuid NOT NULL,
    created_at timestamp(6) without time zone NOT NULL,
    email character varying(255) NOT NULL,
    full_name character varying(255) NOT NULL,
    password character varying(255) NOT NULL,
    role character varying(255) NOT NULL,
    active boolean
);

ALTER TABLE ONLY document_chunks
    ADD CONSTRAINT document_chunks_pkey PRIMARY KEY (id);

ALTER TABLE ONLY document_versions
    ADD CONSTRAINT document_versions_pkey PRIMARY KEY (id);

ALTER TABLE ONLY documents
    ADD CONSTRAINT documents_pkey PRIMARY KEY (id);

ALTER TABLE ONLY ingestion_tasks
    ADD CONSTRAINT ingestion_tasks_pkey PRIMARY KEY (id);

ALTER TABLE ONLY users
    ADD CONSTRAINT uk6dotkott2kjsp8vw4d0m25fb7 UNIQUE (email);

ALTER TABLE ONLY documents
    ADD CONSTRAINT uk_documents_code UNIQUE (document_code);

ALTER TABLE ONLY document_chunks
    ADD CONSTRAINT ukij984dg41rekmyjy849kt6jge UNIQUE (chunk_id);

ALTER TABLE ONLY users
    ADD CONSTRAINT users_pkey PRIMARY KEY (id);

CREATE INDEX idx_chunks_document ON document_chunks USING btree (document_id);

CREATE INDEX idx_chunks_version ON document_chunks USING btree (version_id);

CREATE INDEX idx_tasks_document ON ingestion_tasks USING btree (document_id);

CREATE INDEX idx_versions_current ON document_versions USING btree (document_id, is_current);

CREATE INDEX idx_versions_document ON document_versions USING btree (document_id);
