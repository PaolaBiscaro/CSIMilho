"""One repair, same facts and budgets, no repeated tools or real API requests."""

from copy import deepcopy
import json
from unittest.mock import Mock

from google.genai import types
import httpx
import pytest
from pydantic import ValidationError

from app.harness import gemini_client, orchestrator, registry
from app.harness.orchestrator import run_investigation_draft
from app.harness.prompts import REPAIR_INSTRUCTION
from app.harness.schemas import InvestigationReport, InvestigationTrace, ReportRepairTrace
from tests.test_analytics import analytical_dataset
from tests.test_call_validators import comparison_args, context
from tests.test_gemini_client import make_client, settings
from tests.test_orchestrator import FakeClient, call, done, response
from tests.test_synthesis import base_report_payload, planning, report_payload, planned_responses, report_response


def run(context, client, **overrides):
    request, store = context
    return run_investigation_draft(request, client=client, store=store, settings=settings(**overrides))


def invalid_report(payload, reason):
    payload = deepcopy(payload)
    if reason == "json":
        return response(types.Part(text="PRIVATE_BAD_OUTPUT"))
    if reason == "schema":
        payload["overview"].pop("summary")
        payload["PRIVATE_EXTRA_KEY"] = "PRIVATE_EXTRA_VALUE"
    elif reason == "evidence":
        payload["findings"][0]["evidence_ids"] = ["EV-PRIVATE-999"]
    elif reason == "number":
        payload["findings"][0]["explanation"] = "NDVI médio do alvo: 9876."
    elif reason == "language":
        payload["findings"][0]["explanation"] = "PRIVATE_CAUSAL_TEXT causou a diferença."
    return report_response(payload)


@pytest.mark.parametrize("reason,trigger", [("json", "invalid_report"), ("schema", "invalid_report"),
                                           ("evidence", "invalid_report_evidence"), ("number", "invalid_report_evidence"),
                                           ("language", "invalid_report_language")])
def test_invalid_then_valid_repairs_with_same_facts_and_no_tool_reexecution(context, report_payload, monkeypatch, reason, trigger):
    execute = Mock(wraps=registry.execute_tool)
    monkeypatch.setattr(registry, "execute_tool", execute)
    client = FakeClient(*planned_responses(context[0]), invalid_report(report_payload, reason), report_response(report_payload))
    draft = run(context, client)
    assert draft.report == InvestigationReport.model_validate(report_payload)
    assert draft.error is None and not draft.validation_issues
    assert execute.call_count == len(draft.planning.trace.calls) == len(draft.planning.evidence) == 2
    assert len(client.calls) == 5 and not client.closed
    repair = draft.planning.trace.repair
    assert repair.attempt == 1 and repair.status == "success" and repair.trigger.code == trigger
    assert repair.trigger_issues and repair.error is None and not repair.validation_issues
    assert repair.started_at.utcoffset().total_seconds() == 0 and repair.duration_ms >= 0
    assert InvestigationTrace.model_validate_json(draft.planning.trace.model_dump_json()) == draft.planning.trace

    contents, config, remaining = client.calls[-1]
    assert len(contents) == 1 and contents[0].role == "user"
    body = json.loads(contents[0].parts[0].text)
    assert set(body) == {"errors", "schema", "facts"}
    assert body["schema"] == config.response_json_schema == InvestigationReport.model_json_schema()
    assert body["facts"] == json.loads(client.calls[-2][0][0].parts[0].text)
    assert body["errors"][0]["code"] == trigger
    assert set(body["errors"][0]) == {"code", "location", "message"}
    assert config.tools is None and config.tool_config is None and config.automatic_function_calling.disable
    assert config.response_mime_type == "application/json" and REPAIR_INSTRUCTION in config.system_instruction
    assert 0 < remaining <= client.calls[-2][2]
    assert "PRIVATE" not in contents[0].parts[0].text + draft.model_dump_json()
    assert context[0].question not in contents[0].parts[0].text
    assert str(draft.planning.investigation_id) not in contents[0].parts[0].text
    if reason == "schema":
        assert any(item["location"] == "report.overview.summary" for item in body["errors"])


@pytest.mark.parametrize("second", ["json", "schema", "number", "language"])
def test_second_invalid_report_is_final_and_trace_keeps_both_failures(context, report_payload, second):
    client = FakeClient(*planned_responses(context[0]), invalid_report(report_payload, "schema"),
                        invalid_report(report_payload, second), report_response(report_payload))
    draft = run(context, client)
    repair = draft.planning.trace.repair
    assert draft.report is None and repair.status == "error"
    assert repair.trigger.code == "invalid_report" and repair.trigger_issues
    assert repair.error == draft.error and repair.validation_issues == draft.validation_issues
    assert len(client.calls) == 5 and len(client.responses) == 1
    assert len(draft.planning.evidence) == len(draft.planning.trace.calls) == 2


@pytest.mark.parametrize("failure", ["unavailable", "timeout", "authentication_error", "runtime", "blocked", "truncated", "tool"])
def test_repair_failure_does_not_start_another_attempt(context, report_payload, failure):
    if failure == "runtime":
        output = RuntimeError("PRIVATE_EXCEPTION")
    elif failure == "blocked":
        output = report_response(report_payload)
        output.prompt_feedback = types.GenerateContentResponsePromptFeedback(block_reason="SAFETY")
    elif failure == "truncated":
        output = report_response(report_payload)
        output.candidates[0].finish_reason = "MAX_TOKENS"
    elif failure == "tool":
        output = response(call("compare_ndvi", comparison_args(context[0])))
    else:
        output = gemini_client.GeminiError(failure)
    client = FakeClient(*planned_responses(context[0]), invalid_report(report_payload, "number"), output, done())
    draft = run(context, client)
    assert draft.report is None and draft.planning.trace.repair.status == "error"
    assert len(client.calls) == 5 and len(client.responses) == 1
    assert len(draft.planning.trace.calls) == 2
    assert "PRIVATE_EXCEPTION" not in draft.model_dump_json()


@pytest.mark.parametrize("failure", ["unavailable", "blocked", "truncated", "tool"])
def test_provider_or_protocol_failure_before_report_never_triggers_repair(context, report_payload, failure):
    if failure == "unavailable":
        output = gemini_client.GeminiError(failure)
    elif failure == "tool":
        output = response(call("compare_ndvi", comparison_args(context[0])))
    else:
        output = report_response(report_payload)
        if failure == "blocked":
            output.prompt_feedback = types.GenerateContentResponsePromptFeedback(block_reason="SAFETY")
        else:
            output.candidates[0].finish_reason = "MAX_TOKENS"
    client = FakeClient(*planned_responses(context[0]), output, done())
    draft = run(context, client)
    assert draft.report is None and draft.planning.trace.repair is None
    assert len(client.calls) == 4 and len(client.responses) == 1


def test_valid_first_report_needs_no_repair(context, report_payload):
    client = FakeClient(*planned_responses(context[0]), report_response(report_payload), done())
    draft = run(context, client)
    assert draft.report is not None and draft.planning.trace.repair is None
    assert len(client.calls) == 4 and len(client.responses) == 1


def test_one_rate_limit_retry_is_shared_with_repair(context, report_payload, monkeypatch):
    pause = Mock()
    monkeypatch.setattr(orchestrator, "sleep", pause)
    client = FakeClient(gemini_client.GeminiError("rate_limit"), *planned_responses(context[0]),
                        invalid_report(report_payload, "number"), gemini_client.GeminiError("rate_limit"),
                        report_response(report_payload))
    draft = run(context, client)
    assert draft.error.code == "rate_limit" and draft.planning.trace.repair.error.code == "rate_limit"
    assert pause.call_count == 1 and len(client.calls) == 6 and len(client.responses) == 1


def test_unused_rate_limit_retry_can_be_used_in_repair(context, report_payload, monkeypatch):
    pause = Mock()
    monkeypatch.setattr(orchestrator, "sleep", pause)
    client = FakeClient(*planned_responses(context[0]), invalid_report(report_payload, "number"),
                        gemini_client.GeminiError("rate_limit"), report_response(report_payload))
    draft = run(context, client)
    assert draft.report is not None and draft.planning.trace.repair.status == "success"
    assert pause.call_count == 1 and len(client.calls) == 6
    assert client.calls[-1][0] == client.calls[-2][0]


@pytest.mark.parametrize("repair_seconds", [0.5, 2.0])
def test_repair_uses_remaining_deadline_and_records_monotonic_duration(context, report_payload, monkeypatch, repair_seconds):
    clock = [0.0]
    monkeypatch.setattr(orchestrator, "perf_counter", lambda: clock[0])
    client = FakeClient(*planned_responses(context[0]), invalid_report(report_payload, "number"), report_response(report_payload))
    generate = client.generate_content

    def timed(*args, **kwargs):
        clock[0] += repair_seconds if len(client.calls) == 4 else 1
        return generate(*args, **kwargs)

    client.generate_content = timed
    draft = run(context, client, GEMINI_TIMEOUT_SECONDS=5)
    assert [item[2] for item in client.calls] == [5, 4, 3, 2, 1]
    assert draft.planning.trace.repair.duration_ms == repair_seconds * 1000
    if repair_seconds < 1:
        assert draft.report is not None
    else:
        assert draft.report is None and draft.error.code == "timeout"


def test_tool_limit_does_not_prevent_one_report_repair(context, report_payload):
    planned = planned_responses(context[0])[:-1]
    client = FakeClient(*planned, invalid_report(report_payload, "number"), report_response(report_payload))
    draft = run(context, client, GEMINI_MAX_TOOL_CALLS=2)
    assert draft.report is not None and draft.planning.stop_reason == "tool_limit"
    assert len(client.calls) == 4 and len(draft.planning.trace.calls) == 2


@pytest.mark.parametrize("valid", [True, False])
def test_owned_client_closes_after_repair(context, report_payload, monkeypatch, valid):
    client = FakeClient(*planned_responses(context[0]), invalid_report(report_payload, "schema"),
                        report_response(report_payload) if valid else invalid_report(report_payload, "schema"))
    monkeypatch.setattr(gemini_client, "GeminiClient", lambda _: client)
    request, store = context
    draft = run_investigation_draft(request, store=store, settings=settings())
    assert client.closed and (draft.report is not None) == valid


@pytest.mark.parametrize("change", [{"attempt": 2}, {"duration_ms": -1}, {"duration_ms": float("nan")},
                                  {"status": "error", "error": None}, {"status": "success", "error": {"code": "bad", "message": "Falha"}}])
def test_repair_trace_rejects_inconsistent_states(context, report_payload, change):
    client = FakeClient(*planned_responses(context[0]), invalid_report(report_payload, "schema"), report_response(report_payload))
    trace = run(context, client).planning.trace.repair.model_dump()
    with pytest.raises(ValidationError):
        ReportRepairTrace.model_validate({**trace, **change})


def test_real_sdk_repair_uses_fresh_fact_only_request(context, report_payload, make_client):
    outputs = iter([*planned_responses(context[0]), invalid_report(report_payload, "schema"), report_response(report_payload)])

    def handler(request):
        return httpx.Response(200, json=next(outputs).model_dump(mode="json", by_alias=True, exclude_none=True))

    client, constructions, requests, _ = make_client(handler)
    draft = run(context, client)
    assert draft.report is not None and draft.planning.trace.repair.status == "success"
    assert len(constructions) == 1 and len(requests) == 5
    body = json.loads(requests[-1].content)
    assert "tools" not in body and "toolConfig" not in body and len(body["contents"]) == 1
    assert set(json.loads(body["contents"][0]["parts"][0]["text"])) == {"errors", "schema", "facts"}
    assert "PRIVATE" not in requests[-1].content.decode()
