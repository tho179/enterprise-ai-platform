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

    EMBEDDING_MODEL: str = os.getenv(
        "EMBEDDING_MODEL",
        "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    )

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
    # Câu hợp lệ đo được -1.06..+9.86; câu ngoài phạm vi -1.68..-6.86.
    # -1.5 chặn được "công ty có bao nhiêu nhân viên" mà không chặn câu đúng.
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
        "gemini-1.5-flash"
    )

settings = Settings()
