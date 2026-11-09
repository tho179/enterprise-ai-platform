import os

from dotenv import load_dotenv

load_dotenv()

class Settings:

    APP_NAME: str = os.getenv(
        "APP_NAME",
        "Enterprise AI Service"
    )

    APP_HOST: str = os.getenv(
        "APP_HOST",
        "0.0.0.0"
    )

    APP_PORT: int = int(
        os.getenv("APP_PORT", "8001")
    )

    QDRANT_URL: str = os.getenv(
        "QDRANT_URL",
        "http://localhost:6333"
    )

    QDRANT_COLLECTION: str = os.getenv(
        "QDRANT_COLLECTION",
        "enterprise_documents"
    )
    QDRANT_API_KEY: str = os.getenv("QDRANT_API_KEY", "")
    # Local-disk fallback is for scripts and tests; a deployment must fail loudly.
    QDRANT_ALLOW_LOCAL_FALLBACK: bool = os.getenv("QDRANT_ALLOW_LOCAL_FALLBACK", "true").lower() in ("1", "true", "yes")

    EMBEDDING_MODEL: str = os.getenv(
        "EMBEDDING_MODEL",
        "intfloat/multilingual-e5-small"
    )
    # E5 cần prefix khác nhau cho câu hỏi và đoạn văn; để trống nếu dùng
    # model khác không yêu cầu prefix.
    EMBEDDING_QUERY_PREFIX: str = os.getenv("EMBEDDING_QUERY_PREFIX", "query: ")
    EMBEDDING_PASSAGE_PREFIX: str = os.getenv("EMBEDDING_PASSAGE_PREFIX", "passage: ")
    EMBEDDING_FOLD_TEXT: bool = os.getenv("EMBEDDING_FOLD_TEXT", "false").lower() in ("1", "true", "yes")

    QDRANT_STORAGE_PATH: str = os.getenv(
        "QDRANT_STORAGE_PATH",
        "data/qdrant_storage"
    )

    # Cross-encoder chấm lại độ liên quan của các ứng viên đầu: quyết định
    # "trả lời hay từ chối" đáng tin hơn hẳn cosine của model nhúng nhỏ.
    RERANKER_MODEL: str = os.getenv(
        "RERANKER_MODEL",
        "cross-encoder/mmarco-mMiniLMv2-L12-H384-v1"
    )
    RERANK_CANDIDATES: int = int(os.getenv("RERANK_CANDIDATES", "10"))
    RERANK_PASSAGE_CHARS: int = int(os.getenv("RERANK_PASSAGE_CHARS", "800"))
    # Dưới ngưỡng này thì từ chối, áp dụng cho mọi dạng câu hỏi. Giá trị đặt từ
    # bộ câu hỏi dò ban đầu, không dò lại trên bộ đánh giá trong data/eval.
    RERANK_GATE: float = float(os.getenv("RERANK_GATE", "-1.5"))

    OPENAI_API_KEY: str = os.getenv(
        "OPENAI_API_KEY",
        ""
    )

    OPENAI_MODEL: str = os.getenv(
        "OPENAI_MODEL",
        "gpt-4o-mini"
    )

    GEMINI_API_KEY: str = os.getenv(
        "GEMINI_API_KEY",
        ""
    )

    GEMINI_MODEL: str = os.getenv(
        "GEMINI_MODEL",
        "gemini-3.5-flash"
    )

    # Gemini 3 thinks by default and the thinking counts against max_tokens.
    GEMINI_REASONING_EFFORT: str = os.getenv("GEMINI_REASONING_EFFORT", "none")
    # Minimum gap between LLM calls, for keys with a low requests-per-minute quota.
    LLM_MIN_INTERVAL_S: float = float(os.getenv("LLM_MIN_INTERVAL_S", "0"))

    # Any OpenAI-compatible endpoint (Ollama, vLLM...); wins over the keys above.
    LLM_BASE_URL: str = os.getenv("LLM_BASE_URL", "")
    LLM_API_KEY: str = os.getenv("LLM_API_KEY", "")
    LLM_MODEL: str = os.getenv("LLM_MODEL", "")
    LLM_TIMEOUT_S: float = float(os.getenv("LLM_TIMEOUT_S", "90"))
    LLM_MAX_TOKENS: int = int(os.getenv("LLM_MAX_TOKENS", "500"))
    # Second LLM pass that checks the answer against the cited context.
    LLM_VERIFY_ANSWERS: bool = os.getenv("LLM_VERIFY_ANSWERS", "true").lower() in ("1", "true", "yes")

    # Topic rules tuned on the sample corpus (see app/answer_rules.py).
    ANSWER_DOMAIN_RULES: bool = os.getenv("ANSWER_DOMAIN_RULES", "false").lower() in ("1", "true", "yes")

    # Shared secret for backend -> AI service calls; empty disables the check.
    INTERNAL_API_TOKEN: str = os.getenv("INTERNAL_API_TOKEN", "")
    CORS_ALLOWED_ORIGINS: list = [
        origin.strip()
        for origin in os.getenv("CORS_ALLOWED_ORIGINS", "http://localhost:3000").split(",")
        if origin.strip()
    ]

    # Neo4j Graph Database Configuration
    NEO4J_URI: str = os.getenv(
        "NEO4J_URI",
        "bolt://localhost:7687"
    )
    NEO4J_USER: str = os.getenv(
        "NEO4J_USER",
        "neo4j"
    )
    NEO4J_PASSWORD: str = os.getenv(
        "NEO4J_PASSWORD",
        "eakwp-neo4j"
    )
    NEO4J_DATABASE: str = os.getenv(
        "NEO4J_DATABASE",
        "neo4j"
    )

    # GraphRAG: đồng bộ chunk upload vào Neo4j và trộn ứng viên graph với vector.
    # Tắt mặc định để test/CLI chạy được khi không có Neo4j; compose bật true.
    GRAPH_ENABLED: bool = os.getenv("GRAPH_ENABLED", "false").lower() in ("1", "true", "yes")
    GRAPH_SEARCH_LIMIT: int = int(os.getenv("GRAPH_SEARCH_LIMIT", "8"))
    GRAPH_RRF_WEIGHT: float = float(os.getenv("GRAPH_RRF_WEIGHT", "0.2"))
    # Top vector chunks used as starting points for graph traversal.
    GRAPH_EXPAND_SEEDS: int = int(os.getenv("GRAPH_EXPAND_SEEDS", "5"))
    # Skip entities mentioned by more chunks than this during traversal.
    GRAPH_MAX_ENTITY_DF: int = int(os.getenv("GRAPH_MAX_ENTITY_DF", "25"))
    GRAPH_ENTITY_MIN_SCORE: float = float(os.getenv("GRAPH_ENTITY_MIN_SCORE", "0.9"))

settings = Settings()
