"""Exercise the official SDK through an in-memory HTTP transport, without API calls."""

import importlib
import json
import traceback
from unittest.mock import Mock

from google import genai
from google.genai import types
import httpx
import pytest

from app.config import Settings, get_settings
from app.harness import gemini_client


def settings(**overrides):
    return Settings(_env_file=None, **{
        "GEMINI_API_KEY": "artificial-test-key",
        "GEMINI_MODEL": "configured-test-model",
        "GEMINI_TIMEOUT_SECONDS": 7,
        **overrides,
    })


def successful_response(request):
    return httpx.Response(200, json={
        "candidates": [{"content": {"role": "model", "parts": [{"text": "OK"}]}}],
    })


class TrackedTransport(httpx.MockTransport):
    is_closed = False

    def close(self):
        self.is_closed = True
        super().close()


@pytest.fixture
def make_client(monkeypatch):
    sdk_constructor = genai.Client
    clients = []

    def make(handler=successful_response, **overrides):
        requests = []
        constructions = []

        def respond(request):
            requests.append(request)
            return handler(request)

        transport = TrackedTransport(respond)

        def factory(**kwargs):
            constructions.append(kwargs.copy())
            kwargs["http_options"] = kwargs["http_options"].model_copy(update={"client_args": {"transport": transport}})
            return sdk_constructor(**kwargs)

        monkeypatch.setattr(genai, "Client", factory)
        client = gemini_client.GeminiClient(settings(**overrides))
        clients.append((client, transport))
        return client, constructions, requests, transport

    yield make
    for client, transport in clients:
        client.close()
        transport.close()


def test_module_import_and_construction_without_key_never_create_sdk_client(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.setenv("GOOGLE_API_KEY", "unrelated-test-key")
    factory = Mock(side_effect=AssertionError("SDK must remain lazy"))
    monkeypatch.setattr(genai, "Client", factory)
    get_settings.cache_clear()
    try:
        module = importlib.reload(gemini_client)
        with module.GeminiClient() as client:
            assert client.model
        factory.assert_not_called()
    finally:
        get_settings.cache_clear()


@pytest.mark.parametrize("key", [None, "", "   "])
def test_missing_or_blank_key_fails_before_sdk_creation(monkeypatch, key):
    monkeypatch.setenv("GOOGLE_API_KEY", "unrelated-test-key")
    factory = Mock()
    monkeypatch.setattr(genai, "Client", factory)
    with gemini_client.GeminiClient(settings(GEMINI_API_KEY=key)) as client:
        with pytest.raises(gemini_client.GeminiError) as caught:
            client.generate_content("Teste")
    assert caught.value.code == "missing_api_key"
    assert "GEMINI_API_KEY" in str(caught.value)
    factory.assert_not_called()


@pytest.mark.parametrize("timeout,expected", [(1.25, 1.25), (30, 7.0), (0.0001, 0.001)])
def test_per_call_timeout_can_only_reduce_the_configured_limit(make_client, timeout, expected):
    client, _, requests, _ = make_client()
    client.generate_content("Teste", timeout_seconds=timeout)
    assert set(requests[0].extensions["timeout"].values()) == {expected}


@pytest.mark.parametrize("timeout", [0, -1, True, "1", float("nan"), float("inf")])
def test_invalid_per_call_timeout_fails_before_sdk_creation(monkeypatch, timeout):
    factory = Mock()
    monkeypatch.setattr(genai, "Client", factory)
    with gemini_client.GeminiClient(settings()) as client:
        with pytest.raises(ValueError, match="positivo e finito"):
            client.generate_content("Teste", timeout_seconds=timeout)
    factory.assert_not_called()


def test_sdk_uses_configured_model_key_timeout_and_reuses_client(make_client, monkeypatch):
    monkeypatch.setenv("GOOGLE_API_KEY", "wrong-test-key")
    monkeypatch.setenv("GOOGLE_GENAI_USE_ENTERPRISE", "true")
    monkeypatch.setenv("GOOGLE_GENAI_USE_VERTEXAI", "true")
    client, constructions, requests, transport = make_client(GEMINI_API_KEY=" artificial-test-key ")
    with client:
        assert constructions == []
        response = client.generate_content("Teste")
        assert isinstance(response, types.GenerateContentResponse)
        assert response.text == "OK"
        client.generate_content("Outro teste")
        assert len(constructions) == 1
        assert constructions[0]["enterprise"] is False
        assert constructions[0]["http_options"].timeout == 7000
        assert constructions[0]["http_options"].retry_options.attempts == 1
        assert len(requests) == 2
        for request in requests:
            assert request.url.host == "generativelanguage.googleapis.com"
            assert request.url.path.endswith("/models/configured-test-model:generateContent")
            assert request.headers["x-goog-api-key"] == "artificial-test-key"
            assert set(request.extensions["timeout"].values()) == {7.0}
    assert transport.is_closed
    client.close()  # Closing twice is harmless and never creates a new SDK client.
    with pytest.raises(RuntimeError, match="fechado"):
        client.generate_content("Teste")
    assert len(constructions) == 1


def test_generation_config_is_preserved_without_allowing_automatic_tool_execution(make_client):
    tool = Mock(return_value="must not execute")
    tool.__name__ = "tool_that_must_not_run"

    def tool_that_must_not_run() -> str:
        """Artificial test tool."""
        return tool()

    def response_with_function_call(request):
        return httpx.Response(200, json={"candidates": [{"content": {
            "role": "model", "parts": [{"functionCall": {"name": "tool_that_must_not_run", "args": {}}}],
        }}]})

    client, _, requests, _ = make_client(response_with_function_call)
    config = types.GenerateContentConfig(
        max_output_tokens=12,
        tools=[tool_that_must_not_run],
        automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=False),
        http_options=types.HttpOptions(timeout=99000, retry_options=types.HttpRetryOptions(attempts=5)),
    )
    response = client.generate_content("Teste", config=config)
    assert response.function_calls[0].name == "tool_that_must_not_run"
    tool.assert_not_called()
    assert len(requests) == 1
    assert json.loads(requests[0].content)["generationConfig"]["maxOutputTokens"] == 12
    assert set(requests[0].extensions["timeout"].values()) == {7.0}
    assert config.automatic_function_calling.disable is False
    assert config.http_options.timeout == 99000
    assert config.http_options.retry_options.attempts == 5


@pytest.mark.parametrize(("status", "code"), [
    (400, "invalid_request"),
    (401, "authentication_error"),
    (403, "permission_denied"),
    (404, "model_not_found"),
    (408, "timeout"),
    (429, "rate_limit"),
    (500, "unavailable"),
    (503, "unavailable"),
    (504, "timeout"),
])
def test_api_errors_are_safe_and_not_retried_by_sdk(make_client, caplog, status, code):
    private_content = "artificial-test-key private-prompt-content"

    def fail(request):
        return httpx.Response(status, json={"error": {"code": status, "message": private_content}})

    client, _, requests, transport = make_client(fail)
    with client, pytest.raises(gemini_client.GeminiError) as caught:
        client.generate_content("private-prompt-content")
    error = caught.value
    assert error.code == code
    assert error.status_code == status
    assert len(requests) == 1
    assert transport.is_closed
    public_error = str(error) + repr(error) + str(vars(error)) + "".join(traceback.format_exception(error))
    assert "artificial-test-key" not in public_error + caplog.text
    assert private_content not in public_error + caplog.text


def test_invalid_api_key_returned_as_400_has_authentication_message(make_client):
    def fail(request):
        return httpx.Response(400, json={"error": {
            "code": 400,
            "status": "INVALID_ARGUMENT",
            "message": "provider text must not be exposed",
            "details": [{"@type": "type.googleapis.com/google.rpc.ErrorInfo", "reason": "API_KEY_INVALID"}],
        }})

    client, _, _, _ = make_client(fail)
    with pytest.raises(gemini_client.GeminiError) as caught:
        client.generate_content("Teste")
    assert caught.value.code == "authentication_error"
    assert "provider text" not in str(caught.value)


@pytest.mark.parametrize(("error_type", "code"), [
    (httpx.ConnectTimeout, "timeout"),
    (httpx.ReadTimeout, "timeout"),
    (httpx.WriteTimeout, "timeout"),
    (httpx.PoolTimeout, "timeout"),
    (httpx.ConnectError, "network_error"),
    (httpx.ReadError, "network_error"),
    (httpx.RemoteProtocolError, "network_error"),
])
def test_transport_failures_are_translated_without_request_details(make_client, error_type, code):
    def fail(request):
        raise error_type("private-network-details", request=request)

    client, _, requests, _ = make_client(fail)
    with pytest.raises(gemini_client.GeminiError) as caught:
        client.generate_content("Teste")
    assert caught.value.code == code
    assert caught.value.status_code is None
    assert "private-network-details" not in "".join(traceback.format_exception(caught.value))
    assert len(requests) == 1


def test_client_configuration_error_is_sanitized(monkeypatch):
    monkeypatch.setattr(genai, "Client", Mock(side_effect=ValueError("private-config-details")))
    with gemini_client.GeminiClient(settings()) as client:
        with pytest.raises(gemini_client.GeminiError) as caught:
            client.generate_content("Teste")
    assert caught.value.code == "configuration_error"
    assert "private-config-details" not in "".join(traceback.format_exception(caught.value))


def test_programming_errors_are_not_hidden_as_provider_failures(make_client):
    def fail(request):
        raise RuntimeError("unexpected-programming-error")

    client, _, _, transport = make_client(fail)
    with pytest.raises(RuntimeError, match="unexpected-programming-error"), client:
        client.generate_content("Teste")
    assert transport.is_closed
