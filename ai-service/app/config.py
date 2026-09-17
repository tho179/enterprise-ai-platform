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
        "sentence-transformers/all-MiniLM-L6-v2"
    )

    OPENAI_API_KEY: str = os.getenv(
        "OPENAI_API_KEY",
        ""
    )

    OPENAI_MODEL: str = os.getenv(
        "OPENAI_MODEL",
        "gpt-4o-mini"
    )

settings = Settings()
