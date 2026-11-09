from fastapi.testclient import TestClient

from app.config import settings
from app.main import app

client = TestClient(app)
BODY = {"query": "x"}


def test_api_rejects_missing_or_wrong_token(monkeypatch):
    monkeypatch.setattr(settings, "INTERNAL_API_TOKEN", "secret")
    assert client.post("/api/v1/search", json=BODY).status_code == 401
    wrong = client.post("/api/v1/search", json=BODY, headers={"X-Internal-Token": "nope"})
    assert wrong.status_code == 401


def test_right_token_passes_the_middleware(monkeypatch):
    monkeypatch.setattr(settings, "INTERNAL_API_TOKEN", "secret")
    response = client.get("/api/v1/metrics/latency", headers={"X-Internal-Token": "secret"})
    assert response.status_code == 200


def test_health_stays_public(monkeypatch):
    monkeypatch.setattr(settings, "INTERNAL_API_TOKEN", "secret")
    assert client.get("/health").status_code == 200
