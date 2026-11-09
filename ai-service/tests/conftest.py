import pytest

from app.config import settings


@pytest.fixture(autouse=True)
def no_internal_token(monkeypatch):
    """API tests call the app directly; the token check has its own test."""
    monkeypatch.setattr(settings, "INTERNAL_API_TOKEN", "")
