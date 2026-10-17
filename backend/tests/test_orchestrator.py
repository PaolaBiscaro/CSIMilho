"""Exercise bounded planning with real local tools and no external API calls."""

import json
from unittest.mock import Mock
from uuid import uuid4

from google.genai import types
import httpx
import pytest

from app.harness import gemini_client, orchestrator, registry
from app.harness.orchestrator import run_investigation_tools
from tests.test_analytics import analytical_dataset
from tests.test_call_validators import comparison_args, context
from tests.test_gemini_client import make_client, settings


def response(*parts, finish_reason="STOP"):
    return types.GenerateContentResponse(candidates=[types.Candidate(
        content=types.Content(role="model", parts=list(parts)), finish_reason=finish_reason,
    )])


def call(name, arguments, *, call_id=None, signature=None):
    return types.Part(function_call=types.FunctionCall(name=name, args=arguments, id=call_id),
                      thought_signature=signature)


def done():
    return response(types.Part(text="Análise finalizada."))


class FakeClient:
    model = "configured-test-model"

    def __init__(self, *responses):
        self.responses = list(responses)
        self.calls = []
        self.closed = False

    def generate_content(self, contents, *, config, timeout_seconds=None):
        self.calls.append((contents, config, timeout_seconds))
        assert self.responses, "Unexpected extra generation"
        result = self.responses.pop(0)
        if isinstance(result, Exception):
            raise result
        return result

    def close(self):
        self.closed = True


def run(context, client, **overrides):
    request, store = context
    return run_investigation_tools(request, client=client, store=store, settings=settings(**overrides))


def test_two_tools_then_finalization_preserves_context_results_signatures_and_ids(context):
    request, store = context
    dataset = store.get(request.dataset_id)
    dataset.dataset_metadata = {
        "source_files": ["fields.csv", "ndvi_metadata.csv", "private-path.csv"],
        "warnings": [{"code": "quality_notice", "message": "Cobertura parcial."}],
        "private": "SECRET_METADATA",
    }
    request = request.model_copy(update={"dataset_id": store.save(dataset)})
    args = comparison_args(request)
    client = FakeClient(
        response(call("validate_comparison", args, call_id="comp", signature=b"signature")),
        response(call("compare_ndvi", args, call_id="ndvi")), done(),
    )
    result = run((request, store), client)
    assert result.stop_reason == "model_finished" and result.error is None
    assert [item.tool for item in result.trace.calls] == ["validate_comparison", "compare_ndvi"]
    assert len(result.evidence) == 2 and len(client.calls) == 3
    assert result.warnings[0].code == "quality_notice"
    initial, config, timeout = client.calls[0]
    payload = json.loads(initial[0].parts[0].text)
    assert set(payload) == {"question", "dataset_id", "target", "reference", "period",
                            "source_files", "warnings", "max_tool_calls"}
    assert set(payload["target"]) == {"field_id", "label"}
    assert payload["question"] == request.question
    assert payload["source_files"] == ["fields.csv", "ndvi_metadata.csv"]
    assert "SECRET_METADATA" not in initial[0].parts[0].text
    assert request.question not in config.system_instruction
    assert config.automatic_function_calling.disable
    assert config.tool_config.function_calling_config.mode == "ANY"
    assert config.tool_config.function_calling_config.allowed_function_names == ["validate_comparison"]
    assert len(config.tools[0].function_declarations) == 7
    assert 0 < timeout <= 7
    second_history, second_config, second_timeout = client.calls[1]
    assert second_config.tool_config.function_calling_config.mode == "AUTO"
    assert second_timeout <= timeout
    assert second_history[1].parts[0].thought_signature == b"signature"
    for index, call_id in [(1, "comp"), (2, "ndvi")]:
        reply = client.calls[index][0][-1].parts[0].function_response
        assert reply.id == call_id
        assert reply.response == {"output": result.evidence[index - 1].model_dump(mode="json")}
    assert "Análise finalizada" not in result.model_dump_json()
    assert not client.closed  # Injected clients belong to the caller.


def test_sequential_execution_of_a_batch_unlocks_analysis_only_after_comparison(context):
    args = comparison_args(context[0])
    client = FakeClient(response(call("validate_comparison", args), call("compare_ndvi", args)), done())
    result = run(context, client)
    assert result.stop_reason == "model_finished"
    assert len(result.trace.calls) == 2
    assert len(client.calls[1][0][-1].parts) == 2


@pytest.mark.parametrize("first", ["compare_ndvi", "summarize_soil_analysis", "final_text"])
def test_comparison_is_required_before_any_analysis_or_completion(context, first):
    parts = done() if first == "final_text" else response(call(first, comparison_args(context[0])))
    client = FakeClient(parts)
    result = run(context, client)
    assert result.error.code == "comparison_required"
    assert result.trace.calls == [] and result.evidence == []


def test_incompatible_pair_stops_before_next_call_in_same_batch(context):
    request, store = context
    request = request.model_copy(update={"reference_field_id": "103147"})
    args = comparison_args(request)
    client = FakeClient(response(call("validate_comparison", args), call("compare_ndvi", args)))
    result = run((request, store), client)
    assert result.stop_reason == "invalid_comparison"
    assert result.evidence[0].allowed is False
    assert len(result.trace.calls) == 1


@pytest.mark.parametrize("name,change,code", [
    ("execute_python", {}, "unknown_tool"),
    ("compare_ndvi", {"path": "private.csv"}, "invalid_arguments"),
    ("compare_ndvi", {"dataset_id": str(uuid4())}, "dataset_mismatch"),
    ("compare_ndvi", {"target_field_id": "103145", "reference_field_id": "103144"}, "pair_changed"),
    ("compare_ndvi", {"period": {"start": "2026-01-01", "end": "2026-01-02"}}, "period_changed"),
    ("validate_comparison", {}, "duplicate_call"),
])
def test_invalid_calls_stop_without_execution(context, name, change, code):
    args = comparison_args(context[0])
    client = FakeClient(response(call("validate_comparison", args)), response(call(name, {**args, **change})))
    result = run(context, client)
    assert result.stop_reason == "error" and result.error.code == code
    assert len(result.trace.calls) == len(result.evidence) == 1


def test_absent_arguments_are_rejected(context):
    result = run(context, FakeClient(response(call("validate_comparison", None))))
    assert result.error.code == "invalid_arguments" and not result.trace.calls


@pytest.mark.parametrize("kind", ["empty", "blocked", "truncated", "multiple", "code", "partial", "duplicate_ids"])
def test_malformed_responses_never_execute_tools(context, kind):
    args = comparison_args(context[0])
    part = call("validate_comparison", args)
    output = response(part)
    if kind == "empty":
        output = types.GenerateContentResponse()
    elif kind == "blocked":
        output.prompt_feedback = types.GenerateContentResponsePromptFeedback(block_reason="SAFETY")
    elif kind == "truncated":
        output.candidates[0].finish_reason = "MAX_TOKENS"
    elif kind == "multiple":
        output.candidates.append(output.candidates[0].model_copy(deep=True))
    elif kind == "code":
        output = response(types.Part(executable_code=types.ExecutableCode(language="PYTHON", code="print(1)")))
    elif kind == "partial":
        output.candidates[0].content.parts[0].function_call.will_continue = True
    elif kind == "duplicate_ids":
        output = response(call("validate_comparison", args, call_id="same"), call("compare_ndvi", args, call_id="same"))
    result = run(context, FakeClient(output))
    assert result.error.code == "invalid_response"
    assert not result.trace.calls


def test_configured_limit_stops_without_extra_generation(context):
    args = comparison_args(context[0])
    client = FakeClient(response(call("validate_comparison", args)), response(call("compare_ndvi", args)), done())
    result = run(context, client, GEMINI_MAX_TOOL_CALLS=2)
    assert result.stop_reason == "tool_limit" and len(result.evidence) == 2
    assert len(client.calls) == 2 and len(client.responses) == 1


def test_hard_limit_eight_even_with_larger_configuration_and_batched_calls(context):
    args = comparison_args(context[0])
    soil = {"dataset_id": args["dataset_id"]}
    batch = [call(name, soil if "soil" in name else args) for name in registry.TOOLS]
    batch += [call("summarize_soil_analysis", {**soil, "measurement_group": "group_2"}),
              call("application_compliance", {**args, "operation": "NEVER_EXECUTE"})]
    client = FakeClient(response(*batch))
    result = run(context, client, GEMINI_MAX_TOOL_CALLS=99)
    assert result.stop_reason == "tool_limit"
    assert len(result.trace.calls) == len(result.evidence) == 8
    assert all(item.status == "success" for item in result.trace.calls)
    assert json.loads(client.calls[0][0][0].parts[0].text)["max_tool_calls"] == 8


def test_calculation_failure_keeps_partial_evidence_and_stops(context):
    args = comparison_args(context[0])
    client = FakeClient(response(call("validate_comparison", args)),
                        response(call("application_compliance", {**args, "operation": "UNKNOWN"})), done())
    result = run(context, client)
    assert result.error.code == "analysis_unavailable"
    assert len(result.evidence) == 1 and len(result.trace.calls) == 2
    assert result.trace.calls[-1].status == "error"
    assert len(client.calls) == 2


@pytest.mark.parametrize("corruption", ["nan", "wrong_type"])
def test_invalid_concrete_tool_result_is_not_sent_back_to_model(context, monkeypatch, corruption):
    execute = registry.execute_tool

    def corrupt(name, arguments, **kwargs):
        output = execute(name, arguments, **kwargs)
        if name == "compare_ndvi":
            if corruption == "nan":
                return output.model_copy(update={"target_mean": float("nan")})
            return execute("validate_comparison", arguments, **kwargs)
        return output

    monkeypatch.setattr(registry, "execute_tool", corrupt)
    args = comparison_args(context[0])
    client = FakeClient(response(call("validate_comparison", args)), response(call("compare_ndvi", args)), done())
    result = run(context, client)
    assert result.error.code == "invalid_tool_result"
    assert len(result.evidence) == 1 and result.trace.calls[-1].status == "error"
    assert len(client.calls) == 2


def test_rate_limit_retry_is_once_for_entire_investigation(context, monkeypatch):
    sleep = Mock()
    monkeypatch.setattr(orchestrator, "sleep", sleep)
    args = comparison_args(context[0])
    client = FakeClient(gemini_client.GeminiError("rate_limit"), response(call("validate_comparison", args)),
                        gemini_client.GeminiError("rate_limit"), done())
    result = run(context, client)
    assert result.error.code == "rate_limit" and len(result.evidence) == 1
    assert len(client.calls) == 3 and sleep.call_count == 1
    assert 0 < sleep.call_args.args[0] <= 1
    assert client.calls[0][0] == client.calls[1][0]


@pytest.mark.parametrize("code", ["unavailable", "client_error"])
def test_provider_failure_preserves_completed_trace_and_sanitizes_errors(context, code):
    args = comparison_args(context[0])
    error = RuntimeError("PRIVATE_EXCEPTION") if code == "client_error" else gemini_client.GeminiError(code)
    client = FakeClient(response(call("validate_comparison", args)), error)
    result = run(context, client)
    assert result.stop_reason == "error" and len(result.evidence) == 1
    assert result.error.code == code
    assert "PRIVATE_EXCEPTION" not in result.model_dump_json()
    assert len(client.calls) == 2


@pytest.mark.parametrize("slow_step", ["provider", "tool", "retry"])
def test_total_deadline_stops_late_work(context, monkeypatch, slow_step):
    clock = [0.0]
    monkeypatch.setattr(orchestrator, "perf_counter", lambda: clock[0])
    args = comparison_args(context[0])
    client = FakeClient(response(call("validate_comparison", args)), done())
    if slow_step == "provider":
        generate = client.generate_content

        def slow_generate(*args, **kwargs):
            clock[0] += 8
            return generate(*args, **kwargs)

        client.generate_content = slow_generate
    elif slow_step == "tool":
        execute = registry.execute_tool

        def slow_execute(*args, **kwargs):
            clock[0] += 8
            return execute(*args, **kwargs)

        monkeypatch.setattr(registry, "execute_tool", slow_execute)
    else:
        client.responses.insert(0, gemini_client.GeminiError("rate_limit"))
        monkeypatch.setattr(orchestrator, "sleep", lambda _: clock.__setitem__(0, 8.0))
    result = run(context, client)
    assert result.stop_reason == "timeout" and result.error.code == "timeout"
    assert len(client.calls) == 1
    assert len(result.trace.calls) == (1 if slow_step == "tool" else 0)


def test_owned_client_is_closed_on_success_and_controlled_failure(context, monkeypatch):
    args = comparison_args(context[0])
    for responses in [(response(call("validate_comparison", args)), done()), (RuntimeError("failure"),)]:
        client = FakeClient(*responses)
        monkeypatch.setattr(gemini_client, "GeminiClient", lambda _: client)
        request, store = context
        run_investigation_tools(request, store=store, settings=settings())
        assert client.closed


def test_missing_key_never_constructs_sdk_client(context, monkeypatch):
    factory = Mock(side_effect=AssertionError("No SDK expected"))
    monkeypatch.setattr(gemini_client.genai, "Client", factory)
    request, store = context
    result = run_investigation_tools(request, store=store, settings=settings(GEMINI_API_KEY=None))
    assert result.error.code == "missing_api_key" and not result.trace.calls
    factory.assert_not_called()


def test_real_sdk_round_trip_with_in_memory_http_transport(context, make_client):
    args = comparison_args(context[0])
    outputs = iter([
        response(call("validate_comparison", args, call_id="comp", signature=b"signature")),
        response(call("compare_ndvi", args, call_id="ndvi")), done(),
    ])

    def handler(request):
        return httpx.Response(200, json=next(outputs).model_dump(mode="json", by_alias=True, exclude_none=True))

    client, _, requests, _ = make_client(handler)
    result = run(context, client)
    assert result.stop_reason == "model_finished" and len(result.evidence) == 2
    payloads = [json.loads(request.content) for request in requests]
    assert len(payloads) == 3
    assert payloads[1]["contents"][1]["parts"][0]["thoughtSignature"] == "c2lnbmF0dXJl"
    assert payloads[1]["contents"][2]["parts"][0]["functionResponse"]["id"] == "comp"
    assert payloads[2]["contents"][-1]["parts"][0]["functionResponse"]["id"] == "ndvi"
    assert "systemInstruction" in payloads[0]
    assert all(0 < request.extensions["timeout"]["read"] <= 7 for request in requests)
