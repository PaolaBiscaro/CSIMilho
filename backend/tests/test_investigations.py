"""Public legacy investigation endpoint now blocks instead of publishing fallback."""

from unittest.mock import Mock
from uuid import uuid4

from fastapi import HTTPException
from google.genai import types
import pytest

from app.api import investigations
from app.harness import gemini_client, registry
from app.harness.orchestrator import InvestigationError, run_investigation
from app.harness.report_validation import validate_report_evidence
from app.harness.language_validation import validate_report_language
from app.harness.schemas import InvestigationResponse
from tests.test_analytics import analytical_dataset
from tests.test_call_validators import context
from tests.test_gemini_client import settings
from tests.test_orchestrator import FakeClient, response
from tests.test_synthesis import (
    base_report_payload, planning, report_payload, report_response, planned_responses,
)


def run(context, client=None, **overrides):
    request, store = context
    return run_investigation(request, client=client, store=store, settings=settings(**overrides))


def assert_valid(result):
    assert InvestigationResponse.model_validate_json(result.model_dump_json()) == result
    assert validate_report_evidence(result.report, result.evidence, result.warnings) == result.report
    assert validate_report_language(result.report) == result.report


def test_no_key_blocks_report_without_constructing_provider_and_preserves_dataset(context, monkeypatch):
    provider = Mock(side_effect=AssertionError("No SDK"))
    monkeypatch.setattr(gemini_client, "GeminiClient", provider)
    request, store = context
    with pytest.raises(InvestigationError) as caught:
        run(context, GEMINI_API_KEY=None, GEMINI_API_KEY_2=None, GEMINI_API_KEY_3=None)
    assert caught.value.error.code == "missing_api_key"
    assert caught.value.status_code == 503
    assert "preservado" in str(caught.value)
    assert store.get(request.dataset_id)
    provider.assert_not_called()


def test_fake_gemini_success_is_the_only_completed_origin(context, report_payload, monkeypatch):
    execute = Mock(wraps=registry.execute_tool)
    monkeypatch.setattr(registry, "execute_tool", execute)
    client = FakeClient(*planned_responses(context[0])[1:], report_response(report_payload))
    result = run(context, client)
    assert result.generated_by == "gemini"
    assert result.status == "completed"
    assert result.report.model_dump(mode="json") == report_payload
    assert execute.call_count == len(result.trace.calls) == 2
    assert_valid(result)


def test_one_invalid_report_can_be_repaired(context, report_payload):
    invalid = response(types.Part(text="PRIVATE_INVALID_REPORT"))
    client = FakeClient(*planned_responses(context[0])[1:], invalid, report_response(report_payload))
    result = run(context, client)
    assert result.generated_by == "gemini"
    assert result.trace.repair.status == "success"
    assert "PRIVATE" not in result.model_dump_json()


def test_second_invalid_report_blocks_delivery(context):
    invalid = response(types.Part(text="PRIVATE_INVALID_REPORT"))
    client = FakeClient(*planned_responses(context[0])[1:], invalid, invalid)
    with pytest.raises(InvestigationError) as caught:
        run(context, client)
    assert caught.value.error.code == "invalid_report"
    assert caught.value.status_code == 502
    assert "PRIVATE" not in str(caught.value)


@pytest.mark.parametrize(("code", "status"), [
    ("authentication_error", 401),
    ("permission_denied", 403),
    ("rate_limit", 429),
    ("timeout", 504),
    ("unavailable", 503),
    ("network_error", 503),
])
def test_provider_failure_blocks_and_keeps_safe_error(context, code, status):
    errors = [gemini_client.GeminiError(code)] * (2 if code == "rate_limit" else 1)
    with pytest.raises(InvestigationError) as caught:
        run(context, FakeClient(*errors))
    assert caught.value.error.code == code
    assert caught.value.status_code == status
    assert "preservado" in str(caught.value)


def test_unexpected_provider_exception_is_sanitized(context):
    with pytest.raises(InvestigationError) as caught:
        run(context, FakeClient(RuntimeError("PRIVATE_PROVIDER_KEY")))
    assert caught.value.error.code == "client_error"
    assert "PRIVATE" not in str(caught.value)


def test_incompatible_pair_is_rejected_before_provider(context):
    request, store = context
    request = request.model_copy(update={"reference_field_id": "103147"})
    with pytest.raises(InvestigationError) as caught:
        run((request, store), FakeClient())
    assert caught.value.status_code == 422
    assert caught.value.error.code == "invalid_comparison"


def test_endpoint_maps_blocked_report_and_does_not_save_it(context, monkeypatch):
    request, store = context
    monkeypatch.setattr(investigations, "dataset_store", store)
    monkeypatch.setattr(
        investigations, "get_settings",
        lambda: settings(GEMINI_API_KEY=None, GEMINI_API_KEY_2=None, GEMINI_API_KEY_3=None),
    )
    save = Mock()
    monkeypatch.setattr(investigations.report_store, "save", save)
    with pytest.raises(HTTPException) as caught:
        investigations.investigate(request)
    assert caught.value.status_code == 503
    assert caught.value.detail["code"] == "missing_api_key"
    save.assert_not_called()


def test_missing_dataset_remains_404(context, monkeypatch):
    request, store = context
    monkeypatch.setattr(investigations, "dataset_store", store)
    missing = request.model_copy(update={"dataset_id": uuid4()})
    with pytest.raises(HTTPException) as caught:
        investigations.investigate(missing)
    assert caught.value.status_code == 404
    assert caught.value.detail["code"] == "dataset_not_found"
