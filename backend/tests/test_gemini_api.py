"""API connectivity checks with artificial credentials and no external requests."""

import json
from unittest.mock import Mock

from fastapi.testclient import TestClient
from google import genai
from google.genai import types
import httpx
import pytest

from app.api import gemini
from app.config import Settings
from app.harness import gemini_client
from app.main import create_app


@pytest.fixture
def api_settings(monkeypatch):
    settings = Settings(
        _env_file=None,
        GEMINI_API_KEY="artificial-api-test-key",
        GEMINI_MODEL="configured-test-model",
        GEMINI_TIMEOUT_SECONDS=3,
    )
    monkeypatch.setattr(gemini, "get_settings", lambda: settings)
    return settings


@pytest.fixture
def fake_client(monkeypatch, api_settings):
    client = Mock()
    client.__enter__ = Mock(return_value=client)
    client.__exit__ = Mock(return_value=False)
    client.generate_content.return_value = types.GenerateContentResponse(
        candidates=[types.Candidate(
            finish_reason=types.FinishReason.STOP,
            content=types.Content(role="model", parts=[types.Part(text="OK")]),
        )],
    )
    monkeypatch.setattr(gemini_client, "GeminiClient", Mock(return_value=client))
    times = iter([10.0, 10.125])
    monkeypatch.setattr(gemini, "perf_counter", lambda: next(times))
    return client


def test_success_returns_model_latency_and_safe_message(fake_client):
    with TestClient(create_app()) as client:
        response = client.post("/api/gemini/test")

    assert response.status_code == 200
    assert response.json() == {
        "success": True,
        "model": "configured-test-model",
        "latency_ms": 125,
        "message": "Conexão com o Gemini verificada.",
        "error_code": None,
    }
    fake_client.generate_content.assert_called_once()
    args, kwargs = fake_client.generate_content.call_args
    assert args == ("Responda apenas OK.",)
    assert kwargs["config"].max_output_tokens == 32
    assert kwargs["config"].candidate_count == 1
    assert not kwargs["config"].tools
    fake_client.__exit__.assert_called_once()


@pytest.mark.parametrize("key", [None, "", "   "])
def test_missing_key_returns_clear_error_without_creating_sdk(monkeypatch, api_settings, key):
    settings = Settings(_env_file=None, GEMINI_API_KEY=key, GEMINI_MODEL="configured-test-model")
    monkeypatch.setattr(gemini, "get_settings", lambda: settings)
    factory = Mock(side_effect=AssertionError("No SDK client should be created"))
    monkeypatch.setattr(genai, "Client", factory)

    with TestClient(create_app()) as client:
        response = client.post("/api/gemini/test")

    assert response.status_code == 503
    payload = response.json()
    assert payload["success"] is False
    assert payload["error_code"] == "missing_api_key"
    assert "GEMINI_API_KEY" in payload["message"]
    assert payload["model"] == "configured-test-model"
    assert isinstance(payload["latency_ms"], int) and payload["latency_ms"] >= 0
    factory.assert_not_called()


@pytest.mark.parametrize(("code", "status"), [
    ("authentication_error", 401),
    ("permission_denied", 403),
    ("rate_limit", 429),
    ("timeout", 504),
    ("unavailable", 503),
    ("network_error", 503),
    ("model_not_found", 502),
    ("invalid_request", 502),
    ("configuration_error", 503),
    ("api_error", 502),
])
def test_controlled_failures_keep_response_contract(fake_client, code, status):
    fake_client.generate_content.side_effect = gemini_client.GeminiError(code)

    with TestClient(create_app()) as client:
        response = client.post("/api/gemini/test")

    assert response.status_code == status
    payload = response.json()
    assert payload == {
        "success": False,
        "model": "configured-test-model",
        "latency_ms": 125,
        "message": str(gemini_client.GeminiError(code)),
        "error_code": code,
    }
    fake_client.generate_content.assert_called_once()
    fake_client.__exit__.assert_called_once()


@pytest.mark.parametrize("result", [
    {},
    {"candidates": [{"finish_reason": "STOP"}]},
    {"candidates": [{"content": {"parts": [{"text": "  "}]}}]},
    {"candidates": [{"content": {"parts": [{"text": "internal", "thought": True}]}}]},
    {"candidates": [{"finish_reason": "SAFETY", "content": {"parts": [{"text": "private-block-reason"}]}}]},
    {"prompt_feedback": {"block_reason": "SAFETY", "block_reason_message": "private-block-reason"}},
])
def test_empty_or_blocked_response_is_not_reported_as_success(fake_client, result):
    fake_client.generate_content.return_value = types.GenerateContentResponse.model_validate(result)
    with TestClient(create_app()) as client:
        response = client.post("/api/gemini/test")
    assert response.status_code == 502
    assert response.json()["success"] is False
    assert response.json()["error_code"] == "invalid_response"
    assert "private-block-reason" not in response.text
    assert "internal" not in response.text


def test_token_limit_still_confirms_connectivity_without_exposing_generation(fake_client):
    fake_client.generate_content.return_value = types.GenerateContentResponse(
        candidates=[types.Candidate(finish_reason=types.FinishReason.MAX_TOKENS)],
    )
    with TestClient(create_app()) as client:
        response = client.post("/api/gemini/test")
    assert response.status_code == 200
    assert response.json()["success"] is True


@pytest.mark.parametrize(("provider_status", "expected_status"), [
    (200, 200), (401, 401), (403, 403), (429, 429), (503, 503), ("timeout", 504),
])
def test_api_uses_official_sdk_with_mock_http_transport(monkeypatch, api_settings, caplog, provider_status, expected_status):
    sdk_constructor = genai.Client
    requests = []

    def respond(request):
        requests.append(request)
        if provider_status == "timeout":
            raise httpx.ReadTimeout("private-provider-text", request=request)
        if provider_status == 200:
            return httpx.Response(200, json={"candidates": [{
                "finishReason": "STOP",
                "content": {"role": "model", "parts": [{"text": "private-provider-text"}]},
            }]})
        return httpx.Response(provider_status, json={"error": {
            "code": provider_status,
            "message": "artificial-api-test-key private-provider-text",
        }})

    def factory(**kwargs):
        kwargs["http_options"] = kwargs["http_options"].model_copy(
            update={"client_args": {"transport": httpx.MockTransport(respond)}},
        )
        return sdk_constructor(**kwargs)

    monkeypatch.setattr(genai, "Client", factory)
    with TestClient(create_app()) as client:
        # Unsolicited fields must never select another model or become a prompt.
        response = client.post("/api/gemini/test?model=another-model", json={
            "question": "private-user-content", "api_key": "another-key", "model": "another-model",
        })

    assert response.status_code == expected_status
    assert response.json()["success"] is (provider_status == 200)
    assert len(requests) == 1
    request = requests[0]
    assert request.url.path.endswith("/models/configured-test-model:generateContent")
    assert request.headers["x-goog-api-key"] == "artificial-api-test-key"
    assert set(request.extensions["timeout"].values()) == {3.0}
    sent = json.loads(request.content)
    assert sent["contents"] == [{"role": "user", "parts": [{"text": "Responda apenas OK."}]}]
    assert sent["generationConfig"] == {"candidateCount": 1, "maxOutputTokens": 32}
    assert not sent.get("tools")
    assert "artificial-api-test-key" not in response.text + caplog.text
    assert "private-provider-text" not in response.text + caplog.text
    assert "private-user-content" not in request.content.decode()


def test_health_and_get_probe_do_not_generate_content(fake_client):
    with TestClient(create_app()) as client:
        assert client.get("/api/health").status_code == 200
        assert client.get("/api/gemini/test").status_code == 405
    fake_client.generate_content.assert_not_called()


def test_openapi_documents_response_for_success_and_errors():
    operation = create_app().openapi()["paths"]["/api/gemini/test"]["post"]
    assert "requestBody" not in operation
    for status in (200, 401, 403, 429, 502, 503, 504):
        assert operation["responses"][str(status)]["content"]["application/json"]["schema"] == {
            "$ref": "#/components/schemas/GeminiTestResponse",
        }
