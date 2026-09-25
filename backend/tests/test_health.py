from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import app


def test_health_returns_safe_configuration_without_key(monkeypatch) -> None:
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    get_settings.cache_clear()
    response = TestClient(app).get("/api/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "gemini_configured": False,
        "model": "gemini-2.5-flash",
        "version": "1.0.0",
    }


def test_health_reports_configured_without_exposing_key(monkeypatch) -> None:
    secret = "private-test-value"
    monkeypatch.setenv("GEMINI_API_KEY", secret)
    get_settings.cache_clear()

    response = TestClient(app).get("/api/health")

    assert response.status_code == 200
    assert response.json()["gemini_configured"] is True
    assert secret not in response.text
    get_settings.cache_clear()
