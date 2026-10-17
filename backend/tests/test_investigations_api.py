"""HTTP acceptance tests; no real Gemini credentials or external requests."""

from unittest.mock import Mock
from uuid import uuid4

from fastapi.testclient import TestClient
from google.genai import types
import pytest

from app.api import investigations, datasets
from app.harness import gemini_client, orchestrator, registry
from app.harness.schemas import InvestigationResponse
from app.main import create_app
from tests.test_analytics import analytical_dataset
from tests.test_call_validators import context
from tests.test_gemini_client import settings
from tests.test_orchestrator import FakeClient, done, response
from tests.test_synthesis import base_report_payload, planning, report_payload, planned_responses, report_response


@pytest.fixture
def api(context, monkeypatch):
    monkeypatch.setattr(investigations, "dataset_store", context[1])
    monkeypatch.setattr(investigations, "get_settings", lambda: settings(GEMINI_API_KEY=None))
    with TestClient(create_app()) as client:
        yield client


def configure_fake(monkeypatch, client):
    monkeypatch.setattr(investigations, "get_settings", lambda: settings())
    factory = Mock(return_value=client)
    monkeypatch.setattr(gemini_client, "GeminiClient", factory)
    return factory


def post(api, context, **changes):
    return api.post("/api/investigations", json={**context[0].model_dump(mode="json"), **changes})


def test_gemini_complete_response_schema_and_chart(api, context, report_payload, monkeypatch):
    fake = FakeClient(*planned_responses(context[0])[1:], report_response(report_payload))
    factory = configure_fake(monkeypatch, fake)
    result = post(api, context)
    assert result.status_code == 200
    body = result.json()
    assert set(body) == {"investigation_id", "status", "generated_by", "report", "evidence", "chart_data", "trace", "warnings"}
    parsed = InvestigationResponse.model_validate(body)
    assert parsed.generated_by == "gemini" and parsed.status == "completed"
    assert parsed.chart_data.ndvi == parsed.evidence[1]
    assert parsed.trace.dataset_id == context[0].dataset_id and len(parsed.trace.calls) == 2
    assert fake.closed and factory.call_count == 1
    assert "artificial-test-key" not in result.text and context[0].question not in result.text


def test_missing_key_returns_local_fallback_with_soil_and_ndvi(api, context, monkeypatch):
    factory = Mock(side_effect=AssertionError("No provider"))
    monkeypatch.setattr(gemini_client, "GeminiClient", factory)
    result = post(api, context)
    assert result.status_code == 200 and result.json()["generated_by"] == "deterministic_fallback"
    parsed = InvestigationResponse.model_validate(result.json())
    assert len(parsed.trace.calls) == 8 and parsed.chart_data.ndvi is not None
    assert len(parsed.chart_data.soil_summaries) == 2 and len(parsed.chart_data.soil_groups) == 1
    assert factory.call_count == 0


@pytest.mark.parametrize("code", ["timeout", "unavailable", "authentication_error"])
def test_provider_errors_produce_completed_fallback(api, context, monkeypatch, code):
    fake = FakeClient(gemini_client.GeminiError(code))
    configure_fake(monkeypatch, fake)
    result = post(api, context)
    assert result.status_code == 200
    parsed = InvestigationResponse.model_validate(result.json())
    assert parsed.generated_by == "deterministic_fallback" and parsed.warnings[-1].code == "deterministic_fallback"
    assert len(parsed.trace.calls) == 1 and fake.closed


def test_rate_limit_only_retries_once_then_falls_back(api, context, monkeypatch):
    pause = Mock()
    monkeypatch.setattr(orchestrator, "sleep", pause)
    fake = FakeClient(gemini_client.GeminiError("rate_limit"), gemini_client.GeminiError("rate_limit"), done())
    configure_fake(monkeypatch, fake)
    result = post(api, context)
    assert result.status_code == 200 and result.json()["generated_by"] == "deterministic_fallback"
    assert len(fake.calls) == 2 and pause.call_count == 1 and fake.closed


@pytest.mark.parametrize("valid_repair", [True, False])
def test_one_repair_then_success_or_fallback(api, context, report_payload, monkeypatch, valid_repair):
    invalid = response(types.Part(text="PRIVATE_INVALID_RESPONSE"))
    fake = FakeClient(*planned_responses(context[0])[1:], invalid,
                      report_response(report_payload) if valid_repair else invalid, done())
    configure_fake(monkeypatch, fake)
    result = post(api, context)
    assert result.status_code == 200
    parsed = InvestigationResponse.model_validate(result.json())
    assert parsed.generated_by == ("gemini" if valid_repair else "deterministic_fallback")
    assert parsed.trace.repair.status == ("success" if valid_repair else "error")
    assert len(fake.calls) == 4 and len(fake.responses) == 1 and fake.closed
    assert "PRIVATE" not in result.text


@pytest.mark.parametrize("change", [
    {"dataset_id": "bad-uuid"}, {"question": "curta"}, {"question": "a" * 501},
    {"question": " " * 15}, {"period": "invalid"},
    {"period": {"start": "2026-02-01", "end": "2026-01-01"}},
    {"target_field_id": 42}, {"extra": "not allowed"},
])
def test_bad_request_is_422_before_tools_or_client(api, context, monkeypatch, change):
    execute = Mock(side_effect=AssertionError("No tools"))
    monkeypatch.setattr(registry, "execute_tool", execute)
    assert post(api, context, **change).status_code == 422
    assert execute.call_count == 0


@pytest.mark.parametrize("change,code,status", [
    ({"dataset_id": str(uuid4())}, "dataset_not_found", 404),
    ({"target_field_id": "unknown"}, "field_not_found", 422),
    ({"reference_field_id": "103144"}, "invalid_pair", 422),
    ({"reference_field_id": "103147"}, "invalid_comparison", 422),
])
def test_dataset_and_pair_failures_have_safe_codes(api, context, monkeypatch, change, code, status):
    factory = configure_fake(monkeypatch, FakeClient())
    result = post(api, context, **change)
    assert result.status_code == status and result.json()["detail"]["code"] == code
    assert factory.call_count == 0


def test_calculation_failure_returns_safe_error_not_completed(api, context, monkeypatch):
    monkeypatch.setattr(registry, "execute_tool", Mock(side_effect=RuntimeError("PRIVATE_CALCULATION")))
    result = post(api, context)
    assert result.status_code == 503 and result.json()["detail"]["code"] == "tool_execution_failed"
    assert "PRIVATE" not in result.text and "traceback" not in result.text.casefold()


def test_unexpected_internal_failure_does_not_expose_details(api, context, monkeypatch):
    monkeypatch.setattr(investigations, "run_investigation", Mock(side_effect=RuntimeError("PRIVATE_BODY")))
    result = post(api, context)
    assert result.status_code == 503 and result.json()["detail"]["code"] == "investigation_failed"
    assert "PRIVATE" not in result.text


def test_upload_then_investigate_uses_dataset_session(api, context, presentation_package, monkeypatch):
    monkeypatch.setattr(datasets, "dataset_store", context[1])
    package = [("files", (name, content, "text/csv")) for name, content in presentation_package.items()]
    uploaded = api.post("/api/datasets", files=package)
    assert uploaded.status_code == 201
    result = post(api, context, dataset_id=uploaded.json()["dataset_id"])
    assert result.status_code == 200
    parsed = InvestigationResponse.model_validate(result.json())
    assert parsed.generated_by == "deterministic_fallback"
    assert str(parsed.trace.dataset_id) == uploaded.json()["dataset_id"]


def test_openapi_exposes_request_and_complete_response(api):
    schema = api.get("/openapi.json").json()
    operation = schema["paths"]["/api/investigations"]["post"]
    assert operation["requestBody"]["content"]["application/json"]["schema"]["$ref"].endswith("/InvestigationRequest")
    assert operation["responses"]["200"]["content"]["application/json"]["schema"]["$ref"].endswith("/InvestigationResponse")
