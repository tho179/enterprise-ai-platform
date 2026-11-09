import hmac
import logging

import httpx
from fastapi import FastAPI, Request, HTTPException, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.api.v1.search import router as search_router
from app.api.v1.ingest import router as ingest_router
from app.api.v1.chat import router as chat_router
from app.api.v1.extract import router as extract_router
from app.api.v1.knowledge_graph import router as knowledge_graph_router
from app.api.v1.evaluation import router as evaluation_router
from app.knowledge_graph.service import get_store
from app.llm_client import resolve_llm
from app.observability import latency_snapshot

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title=settings.APP_NAME,
    version="0.1.0",
    description="Enterprise Knowledge Base & AI Semantic Retrieval Service"
)

# Enable CORS for frontend cross-origin requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ALLOWED_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["Content-Type"],
)

PUBLIC_PATHS = {"/", "/health", "/health/dependencies", "/docs", "/openapi.json"}


@app.middleware("http")
async def require_internal_token(request: Request, call_next):
    """Only the backend gateway, which holds the shared token, may call the API."""
    expected = settings.INTERNAL_API_TOKEN
    if expected and request.url.path not in PUBLIC_PATHS and request.method != "OPTIONS":
        supplied = request.headers.get("X-Internal-Token", "")
        if not hmac.compare_digest(supplied.encode(), expected.encode()):
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={
                    "success": False,
                    "error": {
                        "code": "HTTP_401",
                        "message": "Missing or invalid internal token",
                        "details": None,
                    },
                },
            )
    return await call_next(request)

# Centralized Exception Handlers (Standard JSON format)
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": {
                "code": f"HTTP_{exc.status_code}",
                "message": str(exc.detail),
                "details": None
            }
        }
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "success": False,
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Invalid request payload format",
                "details": exc.errors()
            }
        }
    )

@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception during {request.method} {request.url.path}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "An unexpected error occurred while processing the request",
                "details": str(exc)
            }
        }
    )

# Include API Routers
app.include_router(search_router, prefix="/api/v1")
app.include_router(ingest_router, prefix="/api/v1")
app.include_router(chat_router, prefix="/api/v1")
app.include_router(extract_router, prefix="/api/v1")
app.include_router(knowledge_graph_router, prefix="/api/v1")
app.include_router(evaluation_router, prefix="/api/v1")

@app.get("/", tags=["Health"])
def root():
    return {
        "success": True,
        "message": f"{settings.APP_NAME} is running",
        "version": "0.1.0"
    }

@app.get("/health", tags=["Health"])
def health_check():
    return {
        "success": True,
        "status": "healthy"
    }


@app.get("/health/dependencies", tags=["Health"])
def dependency_health():
    """Readiness of the stores and LLM; Qdrant is required, the rest degrade."""
    checks = {"qdrant": "down", "neo4j": "disabled", "llm": "extractive-fallback"}
    try:
        headers = {"api-key": settings.QDRANT_API_KEY} if settings.QDRANT_API_KEY else {}
        response = httpx.get(f"{settings.QDRANT_URL}/collections", headers=headers, timeout=3.0)
        checks["qdrant"] = "up" if response.status_code == 200 else f"http_{response.status_code}"
    except httpx.HTTPError as exc:
        logger.warning("Qdrant health check failed: %s", exc)

    if settings.GRAPH_ENABLED:
        try:
            get_store().verify()
            checks["neo4j"] = "up"
        except Exception as exc:
            logger.warning("Neo4j health check failed: %s", exc)
            checks["neo4j"] = "down"

    llm = resolve_llm()
    if llm:
        checks["llm"] = f"{llm.provider}:{llm.model}"

    ready = checks["qdrant"] == "up"
    degraded = checks["neo4j"] == "down" or llm is None
    return JSONResponse(
        status_code=status.HTTP_200_OK if ready else status.HTTP_503_SERVICE_UNAVAILABLE,
        content={
            "success": ready,
            "status": "unhealthy" if not ready else ("degraded" if degraded else "healthy"),
            "dependencies": checks,
        },
    )


@app.get("/api/v1/metrics/latency", tags=["Health"])
def latency_metrics():
    """p50/p95 per pipeline step over the most recent requests."""
    return {"success": True, "steps": latency_snapshot()}
