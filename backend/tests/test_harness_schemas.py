"""Structural contracts only; no Gemini calls or semantic report validation."""

from copy import deepcopy
import json
import subprocess
import sys
from uuid import UUID

import pytest
from pydantic import ValidationError

from app.analytics.contracts import SoilSummaryArgs
from app.analytics.evidence import EvidenceIdGenerator
from app.data.session_store import SessionStore
from app.harness.evidence_schema import Evidence as BaseEvidence
from app.harness.registry import TOOLS, execute_tool
from app.harness.schemas import (
    Evidence, EvidenceStrength, InvestigationChartData, InvestigationReport,
    InvestigationRequest, InvestigationResponse, InvestigationTrace,
    ReportFinding, ReportLimitation, ReportOrigin, ReportOverview,
    ReportRecommendation, ToolCallError, ToolCallTrace, ToolName,
)
from tests.test_analytics import analytical_dataset


DATASET_ID = "00000000-0000-4000-8000-000000000001"
TRACE_ID = "00000000-0000-4000-8000-000000000002"
INVESTIGATION_ID = "00000000-0000-4000-8000-000000000003"
TIMESTAMP = "2026-10-15T12:00:00Z"


@pytest.fixture
def request_payload():
    return dict(dataset_id=DATASET_ID, target_field_id="103144", reference_field_id="103145",
                period="full_season", question="Como os talhões se comparam?")


@pytest.fixture
def report_payload():
    return dict(
        overview=dict(headline="Comparação observacional", summary="O NDVI difere entre os talhões.",
                      evidence_strength="weak"),
        findings=[dict(title="Diferença de NDVI", explanation="O alvo apresenta NDVI médio menor.",
                       evidence_ids=["EV-NDVI-001"])],
        limitations=[dict(title="Sem causalidade", explanation="A comparação é observacional.",
                          rule_id="observational_comparison")],
        recommendations=[dict(action="Conferir registros de campo", reason="Investigar a diferença observada.",
                              evidence_ids=["EV-NDVI-001"])],
    )


@pytest.fixture
def call_payload(request_payload):
    arguments = {key: value for key, value in request_payload.items() if key != "question"}
    return dict(trace_id=TRACE_ID, sequence=1, tool="compare_ndvi", arguments=arguments,
                result_evidence_ids=["EV-NDVI-001"], source_files=["ndvi_metadata.csv"],
                tool_version="1.0.0", started_at=TIMESTAMP, duration_ms=0.25, status="success")


@pytest.fixture
def response_payload(report_payload):
    # A structurally complete empty outcome, without invented findings or charts.
    report_payload = deepcopy(report_payload)
    report_payload["overview"]["summary"] = "Não há evidências disponíveis."
    report_payload["findings"] = []
    report_payload["recommendations"] = []
    return dict(investigation_id=INVESTIGATION_ID, status="completed", generated_by="deterministic_fallback",
                report=report_payload, evidence=[], chart_data={}, warnings=[],
                trace=dict(trace_id=TRACE_ID, dataset_id=DATASET_ID, model="configured-model",
                           created_at=TIMESTAMP, calls=[]))


@pytest.mark.parametrize("question", ["a" * 10, "a" * 500, "  Como os talhões se comparam?  "])
def test_request_accepts_question_boundaries_and_normalizes_text(request_payload, question):
    request_payload["question"] = question
    request = InvestigationRequest.model_validate_json(json.dumps(request_payload))
    assert request.dataset_id == UUID(DATASET_ID)
    assert request.question == question.strip()
    assert request.period == "full_season"


def test_request_reuses_ordered_custom_period(request_payload):
    request_payload["period"] = {"start": "2025-01-01", "end": "2025-02-01"}
    request = InvestigationRequest.model_validate(request_payload)
    assert request.model_dump(mode="json")["period"] == request_payload["period"]
    request_payload["period"]["end"] = "2024-12-31"
    with pytest.raises(ValidationError):
        InvestigationRequest.model_validate(request_payload)


@pytest.mark.parametrize(("field", "value"), [
    ("question", "a" * 9), ("question", "a" * 501), ("question", " " * 10),
    ("question", 1234567890), ("question", None), ("dataset_id", "invalid"),
    ("target_field_id", 103144), ("reference_field_id", " "), ("period", "last_month"),
    ("period", {"start": "2025-01-01", "end": "2025-02-01", "depth": 20}),
])
def test_request_rejects_invalid_values(request_payload, field, value):
    request_payload[field] = value
    with pytest.raises(ValidationError):
        InvestigationRequest.model_validate(request_payload)


@pytest.mark.parametrize("field", ["dataset_id", "target_field_id", "reference_field_id", "period", "question"])
def test_request_requires_all_input_fields(request_payload, field):
    del request_payload[field]
    with pytest.raises(ValidationError) as caught:
        InvestigationRequest.model_validate(request_payload)
    assert any(error["loc"] == (field,) and error["type"] == "missing" for error in caught.value.errors())


@pytest.mark.parametrize("strength", ["weak", "moderate", "strong"])
def test_report_strength_serializes_as_spec_enum(report_payload, strength):
    report_payload["overview"]["evidence_strength"] = strength
    result = InvestigationReport.model_validate(report_payload)
    assert result.overview.evidence_strength is EvidenceStrength(strength)
    assert result.model_dump(mode="json") == report_payload


@pytest.mark.parametrize("origin", ["gemini", "deterministic_fallback"])
def test_final_response_origin_and_empty_charts(response_payload, origin):
    response_payload["generated_by"] = origin
    result = InvestigationResponse.model_validate_json(json.dumps(response_payload))
    assert result.generated_by is ReportOrigin(origin)
    assert result.chart_data.model_dump() == dict(ndvi=None, soil_summaries=[], soil_groups=[])
    assert InvestigationResponse.model_validate_json(result.model_dump_json()) == result


@pytest.mark.parametrize("path", [
    ("overview",), ("findings",), ("limitations",), ("recommendations",),
    ("overview", "headline"), ("overview", "summary"), ("overview", "evidence_strength"),
    ("findings", 0, "title"), ("findings", 0, "explanation"), ("findings", 0, "evidence_ids"),
    ("limitations", 0, "title"), ("limitations", 0, "explanation"), ("limitations", 0, "rule_id"),
    ("recommendations", 0, "action"), ("recommendations", 0, "reason"),
    ("recommendations", 0, "evidence_ids"),
])
def test_incomplete_narrative_is_rejected(report_payload, path):
    parent = report_payload
    for part in path[:-1]:
        parent = parent[part]
    del parent[path[-1]]
    with pytest.raises(ValidationError) as caught:
        InvestigationReport.model_validate(report_payload)
    assert any(error["loc"] == path and error["type"] == "missing" for error in caught.value.errors())


@pytest.mark.parametrize(("section", "field", "value"), [
    ("overview", "evidence_strength", "certain"), ("overview", "headline", " "),
    ("findings", "evidence_ids", []), ("findings", "evidence_ids", ["NDVI-001"]),
    ("recommendations", "evidence_ids", []), ("limitations", "rule_id", ""),
])
def test_report_rejects_invalid_nested_values(report_payload, section, field, value):
    item = report_payload[section] if section == "overview" else report_payload[section][0]
    item[field] = value
    with pytest.raises(ValidationError):
        InvestigationReport.model_validate(report_payload)


def test_report_requires_at_least_one_limitation(report_payload):
    report_payload["limitations"] = []
    with pytest.raises(ValidationError):
        InvestigationReport.model_validate(report_payload)


@pytest.mark.parametrize("field", [
    "investigation_id", "status", "generated_by", "report", "evidence", "chart_data", "trace", "warnings",
])
def test_final_response_cannot_silently_default_required_sections(response_payload, field):
    del response_payload[field]
    with pytest.raises(ValidationError) as caught:
        InvestigationResponse.model_validate(response_payload)
    assert any(error["loc"] == (field,) and error["type"] == "missing" for error in caught.value.errors())


@pytest.mark.parametrize(("field", "value"), [("generated_by", "mock"), ("status", "running"), ("report", {}), ("trace", {})])
def test_final_response_rejects_unknown_origin_status_and_placeholders(response_payload, field, value):
    response_payload[field] = value
    with pytest.raises(ValidationError):
        InvestigationResponse.model_validate(response_payload)


@pytest.mark.parametrize("tool", list(TOOLS))
def test_trace_arguments_match_registry_contract_and_round_trip(call_payload, tool):
    call_payload["tool"] = tool
    if "soil" in tool:
        call_payload["arguments"] = dict(dataset_id=DATASET_ID)
    call = ToolCallTrace.model_validate(call_payload)
    assert type(call.arguments) is TOOLS[tool].parameters
    assert ToolCallTrace.model_validate_json(call.model_dump_json()) == call


def test_trace_argument_model_instances_are_checked_against_selected_tool(call_payload):
    call_payload["arguments"] = SoilSummaryArgs(dataset_id=UUID(DATASET_ID))
    with pytest.raises(ValidationError):
        ToolCallTrace.model_validate(call_payload)
    call_payload["tool"] = "summarize_soil_analysis"
    assert isinstance(ToolCallTrace.model_validate(call_payload).arguments, SoilSummaryArgs)


@pytest.mark.parametrize(("field", "value"), [
    ("tool", "execute_python"), ("arguments", {"dataset_id": DATASET_ID}),
    ("sequence", 0), ("sequence", True), ("sequence", "1"),
    ("duration_ms", -1), ("duration_ms", float("nan")), ("duration_ms", float("inf")),
    ("duration_ms", True), ("duration_ms", "1.5"), ("started_at", "2026-10-15T12:00:00"),
    ("status", "pending"), ("result_evidence_ids", []), ("source_files", []),
    ("error", {"code": "failure", "message": "Falha controlada."}),
])
def test_trace_rejects_invalid_metadata_and_success_outcomes(call_payload, field, value):
    call_payload[field] = value
    with pytest.raises(ValidationError):
        ToolCallTrace.model_validate(call_payload)


def test_trace_accepts_controlled_failure_without_evidence(call_payload):
    call_payload.update(status="error", result_evidence_ids=[], source_files=[],
                        error=dict(code="analysis_unavailable", message="Não há datas pareadas."))
    call = ToolCallTrace.model_validate(call_payload)
    assert call.error.code == "analysis_unavailable"
    assert not call.result_evidence_ids
    call_payload["result_evidence_ids"] = ["EV-NDVI-001"]
    with pytest.raises(ValidationError):
        ToolCallTrace.model_validate(call_payload)
    call_payload.update(result_evidence_ids=[], error=None)
    with pytest.raises(ValidationError):
        ToolCallTrace.model_validate(call_payload)


@pytest.mark.parametrize("field", [
    "trace_id", "sequence", "tool", "arguments", "result_evidence_ids", "source_files",
    "tool_version", "started_at", "duration_ms", "status",
])
def test_trace_requires_audit_fields(call_payload, field):
    del call_payload[field]
    with pytest.raises(ValidationError):
        ToolCallTrace.model_validate(call_payload)


@pytest.mark.parametrize("field", ["trace_id", "dataset_id", "model", "created_at", "calls"])
def test_trace_envelope_requires_provenance(response_payload, field):
    del response_payload["trace"][field]
    with pytest.raises(ValidationError):
        InvestigationResponse.model_validate(response_payload)


def test_extra_fields_rejected_at_every_new_contract_level(request_payload, report_payload, call_payload, response_payload):
    cases = [
        (InvestigationRequest, request_payload), (InvestigationReport, report_payload),
        (ReportOverview, report_payload["overview"]), (ReportFinding, report_payload["findings"][0]),
        (ReportLimitation, report_payload["limitations"][0]),
        (ReportRecommendation, report_payload["recommendations"][0]),
        (ToolCallTrace, call_payload), (ToolCallError, dict(code="error", message="Falha.")),
        (InvestigationResponse, response_payload), (InvestigationTrace, response_payload["trace"]),
        (InvestigationChartData, {}),
    ]
    for model, payload in cases:
        with pytest.raises(ValidationError) as caught:
            model.model_validate({**payload, "raw_csv": "untrusted data"})
        assert any(error["loc"] == ("raw_csv",) and error["type"] == "extra_forbidden"
                   for error in caught.value.errors()), model.__name__


@pytest.mark.parametrize("key", ["path", "api_key", "prompt", "raw_csv", "operation"])
def test_trace_does_not_accept_extra_arguments_from_another_tool(call_payload, key):
    call_payload["arguments"][key] = "not allowed for compare_ndvi"
    with pytest.raises(ValidationError):
        ToolCallTrace.model_validate(call_payload)


def test_all_tool_outputs_survive_final_json_with_charts_and_package_warnings(
    analytical_dataset, response_payload, report_payload, call_payload,
):
    store = SessionStore()
    store.save(analytical_dataset, dataset_id=UUID(DATASET_ID))
    ids = EvidenceIdGenerator()
    outputs, calls = [], []
    for name in TOOLS:
        args = dict(dataset_id=DATASET_ID) if "soil" in name else call_payload["arguments"]
        output = execute_tool(name, args, store=store, ids=ids)
        outputs.append(output)
        calls.append(ToolCallTrace.model_validate({
            **call_payload, "sequence": len(calls) + 1, "tool": name, "arguments": args,
            "result_evidence_ids": [output.evidence_id], "source_files": output.source_files,
        }))
    # The eighth allowed call can supply the second soil measurement group.
    args = dict(dataset_id=DATASET_ID, measurement_group="group_2")
    group_2 = execute_tool("summarize_soil_analysis", args, store=store, ids=ids)
    outputs.append(group_2)
    calls.append(ToolCallTrace.model_validate({
        **call_payload, "sequence": 8, "tool": "summarize_soil_analysis", "arguments": args,
        "result_evidence_ids": [group_2.evidence_id], "source_files": group_2.source_files,
    }))
    ndvi = outputs[1]
    response_payload.update(
        report=report_payload, evidence=outputs,
        chart_data=dict(ndvi=ndvi, soil_summaries=[outputs[5], group_2], soil_groups=[outputs[6]]),
        warnings=[dict(code="soil_units_unknown", message="Unidades não documentadas.", file="soil_analysis.csv")],
    )
    response_payload["trace"]["calls"] = calls
    result = InvestigationResponse.model_validate(response_payload)
    encoded = result.model_dump_json()
    restored = InvestigationResponse.model_validate_json(encoded)
    assert [type(item) for item in restored.evidence] == [type(item) for item in outputs]
    assert [item.model_dump(mode="json") for item in restored.evidence] == [
        item.model_dump(mode="json") for item in outputs
    ]
    assert restored.chart_data.ndvi == ndvi
    assert restored.chart_data.soil_summaries == [outputs[5], group_2]
    assert restored.chart_data.soil_groups == [outputs[6]]
    assert restored.chart_data.soil_summaries[0].unit is None
    assert restored.warnings[0].file == "soil_analysis.csv"
    assert restored.trace.calls == calls
    assert set(ToolName) == set(TOOLS)
    # A new field nested inside specialized evidence must not be dropped.
    damaged = json.loads(encoded)
    damaged["evidence"][1]["series"][0]["invented"] = 1
    with pytest.raises(ValidationError):
        InvestigationResponse.model_validate(damaged)
    damaged = json.loads(encoded)
    damaged["chart_data"]["ndvi"]["series"][0]["gap"] = float("nan")
    with pytest.raises(ValidationError):
        InvestigationResponse.model_validate(damaged)


@pytest.mark.parametrize("model", [InvestigationRequest, InvestigationReport, InvestigationResponse, ToolCallTrace])
def test_json_schemas_forbid_additional_properties_recursively(model):
    schema = model.model_json_schema()
    json.dumps(schema, allow_nan=False)

    def visit(node):
        if isinstance(node, dict):
            if node.get("type") == "object":
                assert node["additionalProperties"] is False
            for value in node.values():
                visit(value)
        elif isinstance(node, list):
            for value in node:
                visit(value)

    visit(schema)


@pytest.mark.parametrize("first", ["app.analytics.contracts", "app.harness.schemas", "app.harness.registry"])
def test_shared_evidence_import_is_compatible_in_fresh_process(first):
    assert Evidence is BaseEvidence
    result = subprocess.run(
        [sys.executable, "-c", f"import {first}; from app.harness.schemas import Evidence; "
         "from app.harness.evidence_schema import Evidence as Base; assert Evidence is Base"],
        capture_output=True, text=True, check=False,
    )
    assert result.returncode == 0, result.stderr
