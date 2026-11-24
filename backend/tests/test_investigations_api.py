"""HTTP acceptance: only a validated Gemini report receives HTTP 200."""

from unittest.mock import Mock

from fastapi.testclient import TestClient
from google.genai import types
import pytest

from app.api import investigations
from app.harness import gemini_client
from app.harness.schemas import InvestigationResponse
from app.main import create_app
from tests.test_analytics import analytical_dataset
from tests.test_call_validators import context
from tests.test_gemini_client import settings
from tests.test_orchestrator import FakeClient, response
from tests.test_synthesis import (
    base_report_payload, planning, report_payload, planned_responses, report_response,
)


@pytest.fixture
def api(context, monkeypatch):
    monkeypatch.setattr(investigations, "dataset_store", context[1])
    monkeypatch.setattr(
        investigations, "get_settings",
        lambda: settings(GEMINI_API_KEY=None, GEMINI_API_KEY_2=None, GEMINI_API_KEY_3=None),
    )
    with TestClient(create_app()) as client:
        yield client


def configure_fake(monkeypatch, client):
    monkeypatch.setattr(investigations, "get_settings", lambda: settings())
    factory = Mock(return_value=client)
    monkeypatch.setattr(gemini_client, "GeminiClient", factory)
    return factory


def post(api, context, **changes):
    return api.post("/api/investigations", json={**context[0].model_dump(mode="json"), **changes})


def test_gemini_complete_response_is_stored_and_returned(api, context, report_payload, monkeypatch):
    fake = FakeClient(*planned_responses(context[0])[1:], report_response(report_payload))
    factory = configure_fake(monkeypatch, fake)
    result = post(api, context)
    assert result.status_code == 200
    parsed = InvestigationResponse.model_validate(result.json())
    assert parsed.generated_by == "gemini" and parsed.status == "completed"
    assert fake.closed and factory.call_count == 1


def test_missing_key_blocks_instead_of_returning_fallback(api, context, monkeypatch):
    factory = Mock(side_effect=AssertionError("No provider"))
    monkeypatch.setattr(gemini_client, "GeminiClient", factory)
    result = post(api, context)
    assert result.status_code == 503
    assert result.json()["detail"]["code"] == "missing_api_key"
    assert "preservado" in result.json()["detail"]["message"]
    factory.assert_not_called()


@pytest.mark.parametrize(("code", "status"), [
    ("authentication_error", 401),
    ("permission_denied", 403),
    ("rate_limit", 429),
    ("timeout", 504),
    ("unavailable", 503),
])
def test_provider_errors_block_delivery(api, context, monkeypatch, code, status):
    calls = [gemini_client.GeminiError(code)] * (2 if code == "rate_limit" else 1)
    fake = FakeClient(*calls)
    configure_fake(monkeypatch, fake)
    result = post(api, context)
    assert result.status_code == status
    assert result.json()["detail"]["code"] == code
    assert "report" not in result.json()


@pytest.mark.parametrize(("valid_repair", "status"), [(True, 200), (False, 502)])
def test_single_repair_then_success_or_block(api, context, report_payload, monkeypatch, valid_repair, status):
    invalid = response(types.Part(text="PRIVATE_INVALID_RESPONSE"))
    fake = FakeClient(
        *planned_responses(context[0])[1:],
        invalid,
        report_response(report_payload) if valid_repair else invalid,
    )
    configure_fake(monkeypatch, fake)
    result = post(api, context)
    assert result.status_code == status
    if valid_repair:
        assert result.json()["generated_by"] == "gemini"
    else:
        assert result.json()["detail"]["code"] == "invalid_report"
    assert "PRIVATE" not in result.text


def test_stream_emits_error_not_result_when_report_is_blocked(context, monkeypatch):
    monkeypatch.setattr(investigations, "dataset_store", context[1])
    monkeypatch.setattr(
        investigations, "get_settings",
        lambda: settings(GEMINI_API_KEY=None, GEMINI_API_KEY_2=None, GEMINI_API_KEY_3=None),
    )
    body = "".join(investigations._investigation_stream(context[0]))
    assert "event: error" in body
    assert '"code": "missing_api_key"' in body
    assert "event: result" not in body


@pytest.mark.parametrize("change", [
    {"dataset_id": "bad-uuid"}, {"question": "curta"}, {"question": "a" * 501},
    {"period": "invalid"}, {"target_field_id": 42}, {"extra": "not allowed"},
])
def test_bad_request_is_422_before_report_generation(api, context, change):
    assert post(api, context, **change).status_code == 422


def test_openapi_exposes_report_and_error_contracts(api):
    operation = api.get("/openapi.json").json()["paths"]["/api/investigations"]["post"]
    assert operation["responses"]["200"]["content"]["application/json"]["schema"]["$ref"].endswith(
        "/InvestigationResponse"
    )
    assert "503" in operation["responses"]
