"""Structured synthesis from tool facts, without consuming the Gemini API."""

import json
from unittest.mock import Mock

from google.genai import types
import httpx
import pytest

from app.data.contracts import ValidationIssue
from app.harness import gemini_client, orchestrator
from app.harness.orchestrator import (
    SynthesisError, run_investigation_draft, run_investigation_tools, synthesize_report,
)
from app.harness.prompts import SYNTHESIS_INSTRUCTION
from app.harness.schemas import InvestigationReport, ToolCallError
from tests.test_analytics import analytical_dataset
from tests.test_call_validators import comparison_args, context
from tests.test_gemini_client import make_client, settings
from tests.test_harness_schemas import report_payload as base_report_payload
from app.harness.report_validation import required_limitations
from app.harness.fallback import build_fallback_report
from tests.test_orchestrator import FakeClient, call, done, response


def report_response(payload):
    return response(types.Part(text=json.dumps(payload, ensure_ascii=False)))


def planned_responses(request):
    args = comparison_args(request)
    return [response(call("validate_comparison", args)), response(call("compare_ndvi", args)), done()]


@pytest.fixture
def planning(context):
    request, store = context
    return run_investigation_tools(request, client=FakeClient(*planned_responses(request)),
                                   store=store, settings=settings())


@pytest.fixture
def report_payload(base_report_payload, planning):
    base_report_payload["limitations"] = [item.model_dump(mode="json") for item in required_limitations(planning.evidence, planning.warnings)]
    return base_report_payload


def test_valid_fake_response_becomes_report_with_facts_only_and_no_tools(planning, report_payload):
    planning.warnings.append(ValidationIssue(code="coverage", message="Cobertura parcial."))
    report_payload["limitations"] = [item.model_dump(mode="json") for item in required_limitations(planning.evidence, planning.warnings)]
    before = planning.model_dump_json()
    client = FakeClient(report_response(report_payload))
    report = synthesize_report(planning, client=client, settings=settings())
    assert isinstance(report, InvestigationReport)
    assert report.model_dump(mode="json") == report_payload
    assert planning.model_dump_json() == before and not client.closed
    contents, config, timeout = client.calls[0]
    assert len(contents) == 1 and contents[0].role == "user"
    payload = json.loads(contents[0].parts[0].text)
    assert payload == {
        "evidence": [item.model_dump(mode="json") for item in planning.evidence],
        "reference_findings": [item.model_dump(mode="json") for item in
                               build_fallback_report(planning.evidence, planning.warnings).report.findings],
        "warnings": [item.model_dump(mode="json") for item in planning.warnings],
        "required_limitations": [item.model_dump(mode="json") for item in required_limitations(planning.evidence, planning.warnings)],
    }
    assert str(planning.investigation_id) not in contents[0].parts[0].text
    assert str(planning.trace.trace_id) not in contents[0].parts[0].text
    assert config.response_mime_type == "application/json"
    assert config.response_json_schema == InvestigationReport.model_json_schema()
    assert config.response_json_schema["additionalProperties"] is False
    assert config.response_schema is None and config.tools is None and config.tool_config is None
    assert config.automatic_function_calling.disable and config.candidate_count == 1
    assert SYNTHESIS_INSTRUCTION in config.system_instruction
    assert "Cobertura parcial." not in config.system_instruction
    assert 0 < timeout <= 7


def test_completed_loop_and_tool_limit_both_produce_draft(context, report_payload):
    request, store = context
    for max_calls in (2, 8):
        planned = planned_responses(request)
        if max_calls == 2:
            planned.pop()  # The limit ends planning without a free-form response.
        client = FakeClient(*planned, report_response(report_payload))
        draft = run_investigation_draft(request, client=client, store=store,
                                        settings=settings(GEMINI_MAX_TOOL_CALLS=max_calls))
        assert isinstance(draft.report, InvestigationReport) and draft.error is None
        assert len(draft.planning.trace.calls) == 2 and len(draft.planning.evidence) == 2
        assert len(client.calls) == len(planned) + 1
        assert len(client.calls[-1][0]) == 1  # No planning dialogue/free-form answer.
        assert request.question not in client.calls[-1][0][0].parts[0].text
        assert "Análise finalizada" not in client.calls[-1][0][0].parts[0].text
        assert not client.closed


@pytest.mark.parametrize("mutation", ["missing", "extra", "nested_extra", "enum", "type", "no_limitations", "empty_text"])
def test_invalid_report_schema_is_rejected_without_repair(planning, report_payload, mutation):
    if mutation == "missing":
        del report_payload["overview"]
    elif mutation == "extra":
        report_payload["generated_by"] = "gemini"
    elif mutation == "nested_extra":
        report_payload["overview"]["private_key"] = "PRIVATE_PAYLOAD"
    elif mutation == "enum":
        report_payload["overview"]["evidence_strength"] = "certain"
    elif mutation == "type":
        report_payload["overview"]["summary"] = 42
    elif mutation == "no_limitations":
        report_payload["limitations"] = []
    elif mutation == "empty_text":
        report_payload["overview"]["headline"] = "   "
    client = FakeClient(report_response(report_payload), done())
    with pytest.raises(SynthesisError) as caught:
        synthesize_report(planning, client=client, settings=settings())
    assert caught.value.code == "invalid_report"
    assert "PRIVATE_PAYLOAD" not in str(caught.value)
    assert caught.value.__context__ is None and caught.value.__cause__ is None
    assert len(client.calls) == 1 and len(client.responses) == 1


@pytest.mark.parametrize("text", ["texto livre", "```json\n{}\n```", "{} trailing", "[]", "null", '{"overview":'])
def test_invalid_json_or_wrong_root_is_rejected(planning, text):
    client = FakeClient(response(types.Part(text=text)))
    with pytest.raises(SynthesisError) as caught:
        synthesize_report(planning, client=client, settings=settings())
    assert caught.value.code == "invalid_report"


@pytest.mark.parametrize("kind", ["empty", "blocked", "truncated", "multiple", "tool", "thought_only", "code"])
def test_non_final_or_non_text_responses_are_not_reports(planning, report_payload, kind):
    output = report_response(report_payload)
    if kind == "empty":
        output = types.GenerateContentResponse()
    elif kind == "blocked":
        output.prompt_feedback = types.GenerateContentResponsePromptFeedback(block_reason="SAFETY")
    elif kind == "truncated":
        output.candidates[0].finish_reason = "MAX_TOKENS"
    elif kind == "multiple":
        output.candidates.append(output.candidates[0].model_copy(deep=True))
    elif kind == "tool":
        output.candidates[0].content.parts.append(call("compare_ndvi", {}))
    elif kind == "thought_only":
        output.candidates[0].content.parts[0].thought = True
    elif kind == "code":
        output.candidates[0].content.parts.append(types.Part(
            executable_code=types.ExecutableCode(language="PYTHON", code="print(1)"),
        ))
    with pytest.raises(SynthesisError) as caught:
        synthesize_report(planning, client=FakeClient(output), settings=settings())
    assert caught.value.code == "invalid_response"


def test_text_parts_are_joined_thoughts_ignored_and_sdk_parsed_not_trusted(planning, report_payload):
    text = json.dumps(report_payload)
    output = response(types.Part(text="PRIVATE_THOUGHT", thought=True),
                      types.Part(text=text[:40]), types.Part(text=text[40:]))
    output.parsed = {"ignored": "PRIVATE_PARSED"}
    result = synthesize_report(planning, client=FakeClient(output), settings=settings())
    assert result.model_dump(mode="json") == report_payload
    bad = response(types.Part(text="invalid JSON"))
    bad.parsed = InvestigationReport.model_validate(report_payload)
    with pytest.raises(SynthesisError, match="InvestigationReport"):
        synthesize_report(planning, client=FakeClient(bad), settings=settings())


@pytest.mark.parametrize("reason", ["invalid_comparison", "error", "timeout"])
def test_failed_planning_never_starts_synthesis(planning, reason):
    planning.stop_reason = reason
    client = FakeClient()
    with pytest.raises(SynthesisError) as caught:
        synthesize_report(planning, client=client, settings=settings())
    assert caught.value.code == "synthesis_not_ready" and not client.calls


@pytest.mark.parametrize("mutation", ["empty", "forbidden_pair", "error", "invalid_fact"])
def test_invalid_handoff_is_rejected_before_provider_call(planning, mutation):
    if mutation == "empty":
        planning.evidence = []
    elif mutation == "forbidden_pair":
        planning.evidence[0] = planning.evidence[0].model_copy(update={"allowed": False})
    elif mutation == "error":
        planning.error = ToolCallError(code="error", message="Falha.")
    else:
        planning.evidence[-1] = planning.evidence[-1].model_copy(update={"target_mean": float("nan")})
    client = FakeClient()
    with pytest.raises(SynthesisError) as caught:
        synthesize_report(planning, client=client, settings=settings())
    expected = "invalid_synthesis_input" if mutation == "invalid_fact" else "synthesis_not_ready"
    assert caught.value.code == expected and not client.calls


def test_draft_retains_tool_evidence_and_trace_when_synthesis_fails(context):
    request, store = context
    client = FakeClient(*planned_responses(request), response(types.Part(text="PRIVATE_INVALID_JSON")),
                        response(types.Part(text="PRIVATE_INVALID_JSON")))
    draft = run_investigation_draft(request, client=client, store=store, settings=settings())
    assert draft.report is None and draft.error.code == "invalid_report"
    assert len(draft.planning.evidence) == len(draft.planning.trace.calls) == 2
    assert all(item.status == "success" for item in draft.planning.trace.calls)
    assert "PRIVATE_INVALID_JSON" not in draft.model_dump_json()


def test_invalid_pair_never_reaches_synthesis_in_integrated_flow(context):
    request, store = context
    request = request.model_copy(update={"reference_field_id": "103147"})
    client = FakeClient(response(call("validate_comparison", comparison_args(request))))
    draft = run_investigation_draft(request, client=client, store=store, settings=settings())
    assert draft.report is None and draft.error.code == "invalid_comparison"
    assert len(client.calls) == 1


@pytest.mark.parametrize("code", ["missing_api_key", "unavailable", "timeout", "client_error"])
def test_provider_failures_have_safe_local_errors(planning, code):
    error = RuntimeError("PRIVATE_EXCEPTION") if code == "client_error" else gemini_client.GeminiError(code)
    client = FakeClient(error)
    with pytest.raises(SynthesisError) as caught:
        synthesize_report(planning, client=client, settings=settings())
    assert caught.value.code == code
    assert "PRIVATE_EXCEPTION" not in str(caught.value)
    assert caught.value.__context__ is None


def test_retry_is_shared_between_planning_and_synthesis(context, report_payload, monkeypatch):
    pause = Mock()
    monkeypatch.setattr(orchestrator, "sleep", pause)
    request, store = context
    client = FakeClient(gemini_client.GeminiError("rate_limit"), *planned_responses(request),
                        gemini_client.GeminiError("rate_limit"), report_response(report_payload))
    draft = run_investigation_draft(request, client=client, store=store, settings=settings())
    assert draft.error.code == "rate_limit" and draft.report is None
    assert pause.call_count == 1 and len(client.calls) == 5 and len(client.responses) == 1


def test_synthesis_can_use_the_one_remaining_retry(context, report_payload, monkeypatch):
    pause = Mock()
    monkeypatch.setattr(orchestrator, "sleep", pause)
    request, store = context
    client = FakeClient(*planned_responses(request), gemini_client.GeminiError("rate_limit"),
                        report_response(report_payload))
    draft = run_investigation_draft(request, client=client, store=store, settings=settings())
    assert draft.report is not None and draft.error is None
    assert pause.call_count == 1
    assert client.calls[-1][0] == client.calls[-2][0]


@pytest.mark.parametrize("synthesis_duration", [1, 2])
def test_synthesis_uses_remaining_investigation_deadline(context, report_payload, monkeypatch, synthesis_duration):
    clock = [0.0]
    monkeypatch.setattr(orchestrator, "perf_counter", lambda: clock[0])
    request, store = context
    client = FakeClient(*planned_responses(request), report_response(report_payload))
    generate = client.generate_content

    def timed_generate(*args, **kwargs):
        clock[0] += synthesis_duration if len(client.calls) == 3 else 2
        return generate(*args, **kwargs)

    client.generate_content = timed_generate
    draft = run_investigation_draft(request, client=client, store=store,
                                    settings=settings(GEMINI_TIMEOUT_SECONDS=8))
    assert [item[2] for item in client.calls] == [8, 6, 4, 2]
    assert len(draft.planning.evidence) == 2
    if synthesis_duration == 1:
        assert draft.report is not None and draft.error is None
    else:
        assert draft.report is None and draft.error.code == "timeout"


@pytest.mark.parametrize("failure", [False, True])
def test_owned_client_is_closed_after_synthesis(context, report_payload, monkeypatch, failure):
    request, store = context
    output = RuntimeError("failure") if failure else report_response(report_payload)
    client = FakeClient(*planned_responses(request), output)
    monkeypatch.setattr(gemini_client, "GeminiClient", lambda _: client)
    result = run_investigation_draft(request, store=store, settings=settings())
    assert client.closed
    assert (result.report is None) == failure


def test_real_sdk_sends_json_schema_and_facts_only_over_in_memory_transport(context, report_payload, make_client):
    request, store = context
    outputs = iter([*planned_responses(request), report_response(report_payload)])

    def handler(request):
        return httpx.Response(200, json=next(outputs).model_dump(mode="json", by_alias=True, exclude_none=True))

    client, constructions, requests, _ = make_client(handler)
    draft = run_investigation_draft(request, client=client, store=store, settings=settings())
    assert draft.report.model_dump(mode="json") == report_payload
    assert len(constructions) == 1 and len(requests) == 4
    payload = json.loads(requests[-1].content)
    assert "tools" not in payload and "toolConfig" not in payload
    config = payload["generationConfig"]
    assert config["responseMimeType"] == "application/json"
    assert config["responseJsonSchema"] == InvestigationReport.model_json_schema()
    assert len(payload["contents"]) == 1
    facts = json.loads(payload["contents"][0]["parts"][0]["text"])
    assert set(facts) == {"evidence", "reference_findings", "warnings", "required_limitations"} and len(facts["evidence"]) == 2


@pytest.mark.parametrize("mistake,code", [("id", "unknown_evidence_id"), ("number", "unsupported_number"),
                                         ("sign", "sign_mismatch"), ("unit", "unit_mismatch"),
                                         ("limitation", "missing_limitation")])
def test_evidence_checks_run_before_a_draft_report_is_accepted(context, report_payload, mistake, code):
    request, store = context
    if mistake == "id":
        report_payload["findings"][0]["evidence_ids"] = ["EV-NDVI-999"]
    elif mistake == "number":
        report_payload["findings"][0]["explanation"] = "NDVI médio do alvo: 9876."
    elif mistake == "sign":
        report_payload["findings"][0]["explanation"] = "Gap de NDVI: 0,1."
    elif mistake == "unit":
        report_payload["findings"][0]["explanation"] = "NDVI médio do alvo: 0,4%."
    else:
        report_payload["limitations"].pop()
    client = FakeClient(*planned_responses(request), report_response(report_payload), report_response(report_payload), done())
    draft = run_investigation_draft(request, client=client, store=store, settings=settings())
    assert draft.report is None and draft.error.code == "invalid_report_evidence"
    assert code in {item.code for item in draft.validation_issues}
    assert len(draft.planning.evidence) == len(draft.planning.trace.calls) == 2
    assert len(client.calls) == 5 and len(client.responses) == 1
    assert draft.planning.trace.repair.status == "error"


@pytest.mark.parametrize("text,accepted", [
    ("O manejo causou a diferença de NDVI.", False),
    ("Não é possível afirmar que o manejo causou a diferença de NDVI.", True),
    ("Não é possível afirmar que o manejo causou a diferença, mas a calagem garantiu o vigor.", False),
    ("Os dados indicam uma associação com o manejo.", True),
])
def test_language_validation_runs_on_both_attempts(context, report_payload, text, accepted):
    request, store = context
    report_payload["findings"][0]["explanation"] = text
    outputs = [report_response(report_payload)] if accepted else [report_response(report_payload)] * 2
    client = FakeClient(*planned_responses(request), *outputs, done())
    draft = run_investigation_draft(request, client=client, store=store, settings=settings())
    if accepted:
        assert draft.report is not None and draft.error is None and not draft.validation_issues
    else:
        assert draft.report is None and draft.error.code == "invalid_report_language"
        assert {item.code for item in draft.validation_issues} == {"causal_language"}
        assert {item.location for item in draft.validation_issues} == {"findings[0].explanation"}
    assert len(draft.planning.evidence) == len(draft.planning.trace.calls) == 2
    assert len(client.calls) == (4 if accepted else 5) and len(client.responses) == 1
