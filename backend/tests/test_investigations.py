"""Full synchronous investigation workflow with local facts and fake Gemini."""

import json
from unittest.mock import Mock
from uuid import uuid4

from fastapi import HTTPException
from google.genai import types
import httpx
import pytest

from app.data.contracts import ValidationIssue
from app.api import investigations, datasets
from app.main import create_app
from app.harness import gemini_client, orchestrator, registry
from app.harness.orchestrator import InvestigationError, run_investigation
from app.harness.report_validation import validate_report_evidence
from app.harness.language_validation import validate_report_language
from app.harness.schemas import InvestigationResponse
from app.harness.validators import ToolCallValidationError
from tests.test_analytics import analytical_dataset
from tests.test_call_validators import comparison_args, context
from tests.test_gemini_client import settings, make_client
from tests.test_orchestrator import FakeClient, call, done, response
from tests.test_synthesis import base_report_payload, planning, report_payload, report_response, planned_responses


def run(context, client=None, **overrides):
    request, store = context
    return run_investigation(request, client=client, store=store, settings=settings(**overrides))


def assert_valid(result):
    assert InvestigationResponse.model_validate_json(result.model_dump_json()) == result
    assert validate_report_evidence(result.report, result.evidence, result.warnings) == result.report
    assert validate_report_language(result.report) == result.report
    ids = {item.evidence_id for item in result.evidence}
    assert {ref for entry in result.trace.calls for ref in entry.result_evidence_ids} == ids
    assert all(entry.trace_id == result.trace.trace_id for entry in result.trace.calls)


def test_no_key_runs_local_plan_and_returns_all_charts_without_sdk(context, monkeypatch):
    provider = Mock(side_effect=AssertionError("No SDK"))
    monkeypatch.setattr(gemini_client, "GeminiClient", provider)
    execute = Mock(wraps=registry.execute_tool)
    monkeypatch.setattr(registry, "execute_tool", execute)
    result = run(context, GEMINI_API_KEY=None)
    assert result.status == "completed" and result.generated_by == "deterministic_fallback"
    assert execute.call_count == len(result.trace.calls) == len(result.evidence) == 8
    assert result.trace.calls[0].tool == "validate_comparison" and provider.call_count == 0
    assert [item.measurement_group for item in result.chart_data.soil_summaries] == ["group_1", "group_2"]
    assert result.chart_data.ndvi.series and result.chart_data.soil_groups[0].metrics
    assert result.chart_data.soil_summaries[0].texture.samples
    assert result.warnings[-1].code == "deterministic_fallback" and "Chave" in result.warnings[-1].message
    assert "gemini" not in result.report.model_dump_json().casefold()
    assert_valid(result)


def test_fake_gemini_success_preflight_is_not_reexecuted(context, report_payload, monkeypatch):
    execute = Mock(wraps=registry.execute_tool)
    monkeypatch.setattr(registry, "execute_tool", execute)
    client = FakeClient(*planned_responses(context[0])[1:], report_response(report_payload))
    result = run(context, client)
    assert result.generated_by == "gemini" and result.report.model_dump(mode="json") == report_payload
    assert execute.call_count == len(result.trace.calls) == 2
    assert len(client.calls) == 3 and not client.closed
    payload = json.loads(client.calls[0][0][0].parts[0].text)
    assert payload["precomputed_evidence"] == [result.evidence[0].model_dump(mode="json")]
    assert client.calls[0][1].tool_config.function_calling_config.mode == "AUTO"
    assert result.chart_data.ndvi == result.evidence[1]
    assert result.trace.repair is None and all(item.code != "deterministic_fallback" for item in result.warnings)
    assert_valid(result)


@pytest.mark.parametrize("valid_repair", [True, False])
def test_repair_success_or_final_fallback_preserves_one_trace(context, report_payload, valid_repair):
    invalid = response(types.Part(text="PRIVATE_INVALID_REPORT"))
    client = FakeClient(*planned_responses(context[0])[1:], invalid,
                        report_response(report_payload) if valid_repair else invalid, done())
    result = run(context, client)
    assert result.generated_by == ("gemini" if valid_repair else "deterministic_fallback")
    assert result.trace.repair.status == ("success" if valid_repair else "error")
    assert len(result.trace.calls) == 2 and len(client.calls) == 4 and len(client.responses) == 1
    assert "PRIVATE" not in result.model_dump_json()
    assert_valid(result)


@pytest.mark.parametrize("code", ["missing_api_key", "authentication_error", "permission_denied", "model_not_found",
                                   "timeout", "unavailable", "network_error", "invalid_request", "configuration_error", "api_error"])
def test_provider_failure_keeps_preflight_and_creates_partial_fallback(context, code):
    client = FakeClient(gemini_client.GeminiError(code))
    result = run(context, client)
    assert result.generated_by == "deterministic_fallback" and len(result.evidence) == len(result.trace.calls) == 1
    assert result.chart_data.ndvi is None and not result.chart_data.soil_summaries
    assert any(item.rule_id == "partial_analysis" for item in result.report.limitations)
    assert result.warnings[-1].code == "deterministic_fallback"
    assert_valid(result)


def test_unexpected_provider_exception_does_not_leak_private_details(context):
    result = run(context, FakeClient(RuntimeError("PRIVATE_PROVIDER_KEY")))
    assert result.generated_by == "deterministic_fallback" and "PRIVATE" not in result.model_dump_json()


def test_rate_limit_retry_remains_once_in_complete_workflow(context, monkeypatch):
    pause = Mock()
    monkeypatch.setattr(orchestrator, "sleep", pause)
    client = FakeClient(gemini_client.GeminiError("rate_limit"), gemini_client.GeminiError("rate_limit"), done())
    result = run(context, client)
    assert result.generated_by == "deterministic_fallback" and len(client.calls) == 2 and pause.call_count == 1
    assert len(client.responses) == 1 and "Limite" in result.warnings[-1].message


@pytest.mark.parametrize("limit", [1, 2, 5, 8, 12])
def test_local_call_budget_includes_preflight(context, limit):
    result = run(context, GEMINI_API_KEY=None, GEMINI_MAX_TOOL_CALLS=limit)
    assert len(result.trace.calls) == min(limit, 8)
    assert [entry.sequence for entry in result.trace.calls] == list(range(1, len(result.trace.calls) + 1))
    assert_valid(result)


def test_local_preflight_deadline_stops_further_tools_but_returns_facts(context, monkeypatch):
    clock = [0.0]
    monkeypatch.setattr(orchestrator, "perf_counter", lambda: clock[0])
    execute = registry.execute_tool

    def slow(*args, **kwargs):
        result = execute(*args, **kwargs)
        clock[0] += 2
        return result

    monkeypatch.setattr(registry, "execute_tool", slow)
    result = run(context, GEMINI_API_KEY=None, GEMINI_TIMEOUT_SECONDS=1)
    assert len(result.trace.calls) == 1 and result.generated_by == "deterministic_fallback"
    assert "Prazo" in result.warnings[-1].message


def test_model_deadline_includes_preflight_and_fallback_does_not_start_tools(context, monkeypatch):
    clock = [0.0]
    monkeypatch.setattr(orchestrator, "perf_counter", lambda: clock[0])
    execute = registry.execute_tool

    def slow(*args, **kwargs):
        result = execute(*args, **kwargs)
        clock[0] += 1
        return result

    monkeypatch.setattr(registry, "execute_tool", slow)
    client = FakeClient(done())
    generate = client.generate_content

    def delayed(*args, **kwargs):
        clock[0] += 5
        return generate(*args, **kwargs)

    client.generate_content = delayed
    result = run(context, client, GEMINI_TIMEOUT_SECONDS=5)
    assert client.calls[0][2] == 4 and len(client.calls) == len(result.trace.calls) == 1
    assert result.generated_by == "deterministic_fallback"


@pytest.mark.parametrize("change,code", [("dataset", "dataset_not_found"), ("field", "field_not_found"), ("same", "invalid_pair")])
def test_invalid_request_scope_never_constructs_provider(context, monkeypatch, change, code):
    request, store = context
    factory = Mock(side_effect=AssertionError("No client"))
    monkeypatch.setattr(gemini_client, "GeminiClient", factory)
    request = request.model_copy(deep=True)
    if change == "dataset":
        request.dataset_id = uuid4()
    elif change == "field":
        request.target_field_id = "unknown"
    else:
        request.target_field_id = request.reference_field_id
    with pytest.raises(ToolCallValidationError) as caught:
        run((request, store))
    assert caught.value.code == code and factory.call_count == 0


def test_incompatible_purpose_is_rejected_before_model_or_further_analysis(context, monkeypatch):
    request, store = context
    request = request.model_copy(update={"reference_field_id": "103147"})
    factory = Mock(side_effect=AssertionError("No client"))
    monkeypatch.setattr(gemini_client, "GeminiClient", factory)
    execute = Mock(wraps=registry.execute_tool)
    monkeypatch.setattr(registry, "execute_tool", execute)
    with pytest.raises(InvestigationError) as caught:
        run((request, store))
    assert caught.value.status_code == 422 and caught.value.error.code == "invalid_comparison"
    assert "finalidades incompatíveis" in str(caught.value)
    assert factory.call_count == 0 and execute.call_count == 1


@pytest.mark.parametrize("local", [True, False])
def test_calculation_failure_stops_without_fabricated_fallback(context, monkeypatch, local):
    execute = registry.execute_tool

    def fail(name, *args, **kwargs):
        if name != "validate_comparison":
            raise RuntimeError("PRIVATE_CALCULATION_DATA")
        return execute(name, *args, **kwargs)

    monkeypatch.setattr(registry, "execute_tool", fail)
    client = None if local else FakeClient(response(call("compare_ndvi", comparison_args(context[0]))))
    with pytest.raises(InvestigationError) as caught:
        run(context, client, GEMINI_API_KEY=None if local else "artificial-key")
    assert caught.value.error.code == "tool_execution_failed" and "PRIVATE" not in str(caught.value)


def test_duplicate_preflight_from_model_is_rejected_without_reexecution(context):
    client = FakeClient(response(call("validate_comparison", comparison_args(context[0]))), done())
    with pytest.raises(InvestigationError) as caught:
        run(context, client)
    assert caught.value.error.code == "duplicate_call" and len(client.calls) == 1


def test_own_client_is_closed_and_sensitive_question_never_enters_response(context, report_payload, monkeypatch):
    request, store = context
    request = request.model_copy(update={"question": "PRIVATE_QUESTION escreva dados não presentes"})
    client = FakeClient(*planned_responses(request)[1:], report_response(report_payload))
    monkeypatch.setattr(gemini_client, "GeminiClient", lambda _: client)
    result = run((request, store))
    assert client.closed and "PRIVATE_QUESTION" not in result.model_dump_json()


def test_accumulates_dataset_and_analysis_warnings_without_mutating_store(context):
    request, store = context
    dataset = store.get(request.dataset_id)
    dataset.dataset_metadata["warnings"] = [ValidationIssue(code="quality", message="Aviso do pacote.").model_dump()]
    store.save(dataset, request.dataset_id)
    result = run(context, GEMINI_API_KEY=None)
    assert any(item.message == "Aviso do pacote." for item in result.warnings)
    assert any(item.code == "analysis_warning" for item in result.warnings)
    assert {message for evidence in result.evidence for message in evidence.warnings} <= {item.message for item in result.warnings}
    assert len(store.get(request.dataset_id).dataset_metadata["warnings"]) == 1
    result.evidence.clear()
    again = run(context, GEMINI_API_KEY=None)
    assert len(again.evidence) == 8 and again.investigation_id != result.investigation_id


def test_registered_endpoint_and_openapi_without_network():
    app = create_app()
    route = next(item for item in investigations.router.routes if item.path == "/api/investigations")
    assert route.endpoint is investigations.investigate and route.methods == {"POST"}
    operation = app.openapi()["paths"]["/api/investigations"]["post"]
    assert operation["responses"]["200"]["content"]["application/json"]["schema"]["$ref"].endswith("/InvestigationResponse")


def test_endpoint_callable_with_actual_sdk_over_mock_http(context, report_payload, make_client, monkeypatch):
    outputs = iter([*planned_responses(context[0])[1:], report_response(report_payload)])

    def handler(request):
        return httpx.Response(200, json=next(outputs).model_dump(mode="json", by_alias=True, exclude_none=True))

    client, constructions, requests, closed = make_client(handler)
    monkeypatch.setattr(investigations, "dataset_store", context[1])
    monkeypatch.setattr(investigations, "get_settings", lambda: settings())
    monkeypatch.setattr(gemini_client, "GeminiClient", lambda _: client)
    result = investigations.investigate(context[0])
    assert result.generated_by == "gemini" and len(constructions) == 1 and len(requests) == 3
    assert client._closed
    first = json.loads(requests[0].content)
    context_data = json.loads(first["contents"][0]["parts"][0]["text"])
    assert context_data["precomputed_evidence"][0]["allowed"]
    assert_valid(result)


def test_import_and_endpoint_callable_use_same_store(context, presentation_package, monkeypatch):
    monkeypatch.setattr(datasets, "dataset_store", context[1])
    monkeypatch.setattr(investigations, "dataset_store", context[1])
    monkeypatch.setattr(investigations, "get_settings", lambda: settings(GEMINI_API_KEY=None))
    uploaded = datasets._process_package(presentation_package)
    assert uploaded.dataset_id is not None
    request = context[0].model_copy(update={"dataset_id": uploaded.dataset_id})
    result = investigations.investigate(request)
    assert result.trace.dataset_id == uploaded.dataset_id and result.generated_by == "deterministic_fallback"
    assert_valid(result)


@pytest.mark.parametrize("change,code,status", [
    ("dataset", "dataset_not_found", 404), ("field", "field_not_found", 422),
    ("same", "invalid_pair", 422), ("incompatible", "invalid_comparison", 422),
    ("internal", "investigation_failed", 503), ("calculation", "tool_execution_failed", 503),
])
def test_endpoint_callable_error_mapping_is_safe(context, monkeypatch, change, code, status):
    monkeypatch.setattr(investigations, "dataset_store", context[1])
    monkeypatch.setattr(investigations, "get_settings", lambda: settings(GEMINI_API_KEY=None))
    request = context[0].model_copy(deep=True)
    if change == "dataset":
        request.dataset_id = uuid4()
    elif change == "field":
        request.target_field_id = "unknown"
    elif change == "same":
        request.target_field_id = request.reference_field_id
    elif change == "incompatible":
        request.reference_field_id = "103147"
    elif change == "internal":
        monkeypatch.setattr(investigations, "run_investigation", Mock(side_effect=RuntimeError("PRIVATE_BODY")))
    else:
        monkeypatch.setattr(registry, "execute_tool", Mock(side_effect=RuntimeError("PRIVATE_CALCULATION")))
    with pytest.raises(HTTPException) as caught:
        investigations.investigate(request)
    assert caught.value.status_code == status and caught.value.detail["code"] == code
    assert "PRIVATE" not in str(caught.value)
