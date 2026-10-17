"""Audit actual local executions and safe failure paths without Gemini calls."""

from datetime import datetime, timedelta, timezone
import json
import traceback
from unittest.mock import Mock
from uuid import UUID

import pytest

from app.analytics.common import AnalysisUnavailableError
from app.data.session_store import DatasetNotFoundError
from app.harness import registry, trace
from app.harness.schemas import InvestigationTrace, ToolCallTrace
from app.harness.trace import InvestigationRecorder, ToolExecutionError
from app.harness.validators import ToolCallValidationError
from tests.test_analytics import analytical_dataset
from tests.test_call_validators import comparison_args, context


@pytest.fixture
def recorder(context):
    request, store = context
    return InvestigationRecorder(request, model="configured-test-model", store=store)


@pytest.mark.parametrize("name", list(registry.TOOLS))
def test_real_tool_execution_records_required_metadata_and_round_trips(context, recorder, name):
    request, _ = context
    args = {"dataset_id": str(request.dataset_id)} if "soil" in name else comparison_args(request)
    result = recorder.run_tool(name, args)
    snapshot = recorder.snapshot()
    assert snapshot.dataset_id == request.dataset_id
    assert snapshot.model == "configured-test-model"
    assert snapshot.trace_id == recorder.trace_id
    assert snapshot.created_at.utcoffset() == timedelta(0)
    assert len(snapshot.calls) == 1
    call = snapshot.calls[0]
    assert call.sequence == 1 and call.tool == name and call.trace_id == recorder.trace_id
    assert call.result_evidence_ids == [result.evidence_id]
    assert call.source_files == result.source_files
    assert call.tool_version == result.tool_version == registry.TOOLS[name].version
    assert call.started_at >= snapshot.created_at and call.started_at.utcoffset() == timedelta(0)
    assert call.duration_ms >= 0 and call.status == "success" and call.error is None
    assert InvestigationTrace.model_validate_json(snapshot.model_dump_json()) == snapshot
    assert ToolCallTrace.model_validate_json(call.model_dump_json()) == call


def test_ids_are_generated_once_and_distinct_per_investigation(context):
    request, store = context
    one = InvestigationRecorder(request, model="test", store=store)
    two = InvestigationRecorder(request, model="test", store=store)
    identifiers = [one.investigation_id, one.trace_id, two.investigation_id, two.trace_id]
    assert all(isinstance(item, UUID) and item.version == 4 for item in identifiers)
    assert len(set(identifiers)) == 4
    assert one.snapshot().calls == []
    assert one.trace_id == one.snapshot().trace_id == one.snapshot().trace_id
    with pytest.raises(AttributeError):
        one.investigation_id = two.investigation_id


def test_duration_uses_monotonic_clock_when_wall_clock_moves_back(context, monkeypatch):
    instant = datetime(2026, 1, 1, tzinfo=timezone.utc)

    class WallClock:
        times = iter([instant, instant - timedelta(hours=1)])

        @classmethod
        def now(cls, tz):
            return next(cls.times)

    ticks = iter([1_000_000_000, 1_012_500_000])
    monkeypatch.setattr(trace, "datetime", WallClock)
    monkeypatch.setattr(trace, "perf_counter_ns", lambda: next(ticks))
    request, store = context
    recorder = InvestigationRecorder(request, model="test", store=store)
    recorder.run_tool("compare_ndvi", comparison_args(request))
    snapshot = recorder.snapshot()
    assert snapshot.calls[0].started_at < snapshot.created_at
    assert snapshot.calls[0].duration_ms == 12.5


def test_real_unavailable_analysis_is_recorded_and_not_retried(context, recorder):
    request, store = context
    dataset = store.get(request.dataset_id)
    dataset.ndvi_observations = dataset.ndvi_observations.iloc[:0]
    store.save(dataset, dataset_id=request.dataset_id)
    with pytest.raises(ToolExecutionError) as caught:
        recorder.run_tool("compare_ndvi", comparison_args(request))
    assert caught.value.code == "analysis_unavailable"
    call = recorder.snapshot().calls[0]
    assert call.status == "error" and call.sequence == 1
    assert call.result_evidence_ids == [] and call.source_files == []
    assert call.error.code == caught.value.code
    assert call.error.message == str(caught.value)
    assert ToolCallTrace.model_validate_json(call.model_dump_json()) == call
    with pytest.raises(ToolCallValidationError, match="mesmos argumentos"):
        recorder.run_tool("compare_ndvi", comparison_args(request))
    assert len(recorder.snapshot().calls) == 1


@pytest.mark.parametrize(("error", "code"), [
    (AnalysisUnavailableError("private-error-sentinel"), "analysis_unavailable"),
    (DatasetNotFoundError("private-error-sentinel"), "dataset_not_found"),
    (RuntimeError("private-error-sentinel"), "tool_execution_failed"),
])
def test_errors_have_safe_messages_no_raw_context_and_keep_sequence(context, recorder, monkeypatch, caplog, error, code):
    request, _ = context
    recorder.run_tool("validate_comparison", comparison_args(request))
    monkeypatch.setattr(registry, "execute_tool", Mock(side_effect=error))
    with pytest.raises(ToolExecutionError) as caught:
        recorder.run_tool("compare_ndvi", comparison_args(request))
    assert caught.value.code == code
    assert caught.value.__context__ is None and caught.value.__cause__ is None
    calls = recorder.snapshot().calls
    assert [call.sequence for call in calls] == [1, 2]
    assert [call.status for call in calls] == ["success", "error"]
    assert calls[1].error.code == code and calls[1].duration_ms >= 0
    public = recorder.snapshot().model_dump_json() + str(caught.value) + repr(caught.value)
    public += "".join(traceback.format_exception(caught.value)) + caplog.text
    assert "private-error-sentinel" not in public


def test_normalized_arguments_match_execution_and_are_defensively_copied(context, recorder, monkeypatch):
    request, _ = context
    execute = registry.execute_tool
    received = []

    def execute_and_mutate(name, args, **kwargs):
        received.append(args.copy())
        result = execute(name, args, **kwargs)
        args["operation"] = "mutated-after-execution"
        return result

    monkeypatch.setattr(registry, "execute_tool", execute_and_mutate)
    args = {**comparison_args(request), "operation": " calágem ", "target_field_id": " 103144 "}
    args.pop("period")
    result = recorder.run_tool("application_compliance", args)
    args["target_field_id"] = "changed-by-caller"
    call = recorder.snapshot().calls[0]
    assert call.arguments.model_dump(mode="json") == received[0]
    assert call.arguments.operation == result.operation == "CALAGEM"
    assert call.arguments.period == "full_season"
    assert call.arguments.target_field_id == request.target_field_id
    result.source_files.clear()
    copy = recorder.snapshot()
    copy.calls[0].source_files.clear()
    copy.calls[0].arguments.operation = "changed-snapshot"
    copy.calls.clear()
    assert recorder.snapshot().calls[0].source_files
    assert recorder.snapshot().calls[0].arguments.operation == "CALAGEM"


def test_evidence_ids_share_one_generator_per_investigation(context, recorder):
    request, store = context
    args = {"dataset_id": str(request.dataset_id)}
    one = recorder.run_tool("summarize_soil_analysis", args)
    two = recorder.run_tool("summarize_soil_analysis", {**args, "measurement_group": "group_2"})
    assert one.evidence_id != two.evidence_id
    assert one.evidence_id.endswith("-001") and two.evidence_id.endswith("-002")
    assert [call.sequence for call in recorder.snapshot().calls] == [1, 2]
    new = InvestigationRecorder(request, model="test", store=store)
    assert new.run_tool("summarize_soil_analysis", args).evidence_id == one.evidence_id
    assert new.investigation_id != recorder.investigation_id


@pytest.mark.parametrize(("name", "extra"), [
    ("execute_python", {}), ("compare_ndvi", {"raw_csv": "raw-data-sentinel"}),
    ("compare_ndvi", {"api_key": "credential-sentinel"}),
    ("compare_ndvi", {"prompt": "system-prompt-sentinel"}),
    ("compare_ndvi", {"target_field_id": "103146"}),
])
def test_rejected_calls_do_not_execute_or_record_untrusted_arguments(context, recorder, monkeypatch, name, extra):
    request, _ = context
    execute = Mock(side_effect=AssertionError("must not execute"))
    monkeypatch.setattr(registry, "execute_tool", execute)
    with pytest.raises(ToolCallValidationError):
        recorder.run_tool(name, {**comparison_args(request), **extra})
    execute.assert_not_called()
    assert recorder.snapshot().calls == []


def test_trace_contains_only_audit_fields_not_question_configuration_or_full_results(context, monkeypatch):
    request, store = context
    request.question = "private-question-sentinel"
    monkeypatch.setenv("GEMINI_API_KEY", "credential-sentinel")
    recorder = InvestigationRecorder(request, model="test", store=store)
    execute = registry.execute_tool

    def with_private_note(*args, **kwargs):
        result = execute(*args, **kwargs)
        result.notes.append("raw-csv-or-system-prompt-sentinel")
        return result

    monkeypatch.setattr(registry, "execute_tool", with_private_note)
    recorder.run_tool("compare_ndvi", comparison_args(request))
    exported = recorder.snapshot().model_dump_json()
    assert "sentinel" not in exported
    data = json.loads(exported)
    assert set(data) == {"trace_id", "dataset_id", "model", "created_at", "calls", "repair"}
    assert data["repair"] is None
    assert set(data["calls"][0]) == {
        "trace_id", "sequence", "tool", "arguments", "result_evidence_ids", "source_files",
        "tool_version", "started_at", "duration_ms", "status", "error",
    }


@pytest.mark.parametrize("change", [
    {"evidence_id": "private-result-sentinel"}, {"source_files": ["C:/private-result-sentinel.csv"]},
    {"source_files": []}, {"tool_version": "wrong-version"},
])
def test_invalid_audit_metadata_creates_only_safe_failure(context, recorder, monkeypatch, change):
    request, _ = context
    execute = registry.execute_tool

    def damaged(*args, **kwargs):
        return execute(*args, **kwargs).model_copy(update=change)

    monkeypatch.setattr(registry, "execute_tool", damaged)
    with pytest.raises(ToolExecutionError) as caught:
        recorder.run_tool("compare_ndvi", comparison_args(request))
    assert caught.value.code == "invalid_tool_result"
    call = recorder.snapshot().calls[0]
    assert call.status == "error" and call.result_evidence_ids == [] and call.source_files == []
    assert "private-result-sentinel" not in recorder.snapshot().model_dump_json()


def test_duplicate_result_id_and_non_evidence_result_cannot_be_success(context, recorder, monkeypatch):
    request, _ = context
    result = recorder.run_tool("compare_ndvi", comparison_args(request))
    monkeypatch.setattr(registry, "execute_tool", Mock(return_value=result))
    with pytest.raises(ToolExecutionError) as caught:
        recorder.run_tool("compare_population", comparison_args(request))
    assert caught.value.code == "invalid_tool_result"
    monkeypatch.setattr(registry, "execute_tool", Mock(return_value={"raw_csv": "private-result-sentinel"}))
    with pytest.raises(ToolExecutionError) as caught:
        recorder.run_tool("validate_comparison", comparison_args(request))
    assert caught.value.code == "invalid_tool_result"
    assert [call.sequence for call in recorder.snapshot().calls] == [1, 2, 3]
    assert "private-result-sentinel" not in recorder.snapshot().model_dump_json()
