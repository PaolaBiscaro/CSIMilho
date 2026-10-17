"""Deterministic fallback uses actual W2 facts, no key, client or tool reruns."""

from copy import deepcopy
from unittest.mock import Mock

from google.genai import types
import pytest
from pydantic import ValidationError

from app.config import Settings
from app.analytics.contracts import DatePeriod
from app.data.contracts import ValidationIssue
from app.harness import gemini_client, registry
from app.harness.fallback import FallbackError, FallbackResult, build_fallback_report
from app.harness.language_validation import validate_report_language
from app.harness.orchestrator import run_investigation_draft
from app.harness.report_validation import required_limitations, validate_report_evidence
from tests.test_analytics import analytical_dataset
from tests.test_call_validators import comparison_args, context
from tests.test_report_validation import facts
from tests.test_gemini_client import settings
from tests.test_orchestrator import FakeClient, call, done, response
from tests.test_synthesis import planned_responses


def test_no_key_no_provider_no_tool_reruns_and_correct_origin(facts, monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    assert not Settings(_env_file=None).gemini_configured
    provider = Mock(side_effect=AssertionError("Provider must not be constructed"))
    execute = Mock(side_effect=AssertionError("Tools must not be rerun"))
    monkeypatch.setattr(gemini_client, "GeminiClient", provider)
    monkeypatch.setattr(registry, "execute_tool", execute)
    evidence = list(facts.values())
    result = build_fallback_report(evidence, reason="missing_api_key")
    assert result.generated_by == "deterministic_fallback"
    assert "gemini" not in result.model_dump_json().casefold()
    assert result.warnings[-1].code == "deterministic_fallback"
    assert "Chave" in result.warnings[-1].message
    assert provider.call_count == execute.call_count == 0
    assert FallbackResult.model_validate_json(result.model_dump_json()) == result
    assert validate_report_language(result.report) == result.report
    assert validate_report_evidence(result.report, evidence, result.warnings) == result.report
    for rule in required_limitations(evidence):
        assert rule in result.report.limitations
    assert len(result.report.findings) == len(evidence)


def test_origin_cannot_be_overridden(facts):
    result = build_fallback_report(list(facts.values())).model_dump()
    with pytest.raises(ValidationError):
        FallbackResult.model_validate({**result, "generated_by": "gemini"})


def test_sorted_findings_and_metrics_do_not_depend_on_input_order(facts):
    evidence = list(facts.values())
    expected = build_fallback_report(evidence)
    shuffled = deepcopy(evidence[::-1])
    for item in shuffled:
        if hasattr(item, "metrics"):
            item.metrics.reverse()
    assert build_fallback_report(shuffled) == expected
    ids = [item.evidence_ids[0] for item in expected.report.findings]
    assert ids == [facts[key].evidence_id for key in (
        "validate_comparison", "check_initial_condition", "summarize_soil_analysis",
        "compare_soil_measurement_groups", "compare_ndvi", "application_compliance", "compare_population",
    )]


def test_calagem_precedes_other_operations_and_labels_are_not_narrative(facts):
    extra = facts["application_compliance"].model_copy(deep=True)
    extra.evidence_id = "EV-APP-999"
    extra.operation = "PRIVATE_OPERATION causou 9876"
    extra.notes = ["PRIVATE_NOTES 9876"]
    result = build_fallback_report([extra, *facts.values()])
    ids = [item.evidence_ids[0] for item in result.report.findings]
    assert ids.index(facts["application_compliance"].evidence_id) < ids.index(extra.evidence_id)
    assert "PRIVATE" not in result.report.model_dump_json()


@pytest.mark.parametrize("reason,phrase", [
    ("missing_api_key", "Chave"), ("rate_limit", "Limite"), ("timeout", "Prazo"),
    ("authentication_error", "Autenticação"), ("invalid_report", "formato"),
    ("invalid_report_evidence", "evidências"), ("invalid_report_language", "linguagem"),
    ("invalid_response", "resposta utilizável"), ("unavailable", "indisponível"),
    ("PRIVATE_EXCEPTION", "indisponível"),
])
def test_failure_is_visible_with_safe_local_reason(facts, reason, phrase):
    result = build_fallback_report(list(facts.values()), reason=reason)
    assert phrase in result.warnings[-1].message
    assert "PRIVATE" not in result.model_dump_json()


def test_preserves_inputs_and_returns_independent_results(facts):
    evidence = list(facts.values())
    warning = ValidationIssue(code="quality", message="Cobertura parcial.")
    before = [item.model_dump_json() for item in evidence]
    result = build_fallback_report(evidence, [warning])
    original = result.model_dump_json()
    result.report.findings.clear()
    result.warnings[0].message = "changed"
    assert warning.message == "Cobertura parcial."
    assert [item.model_dump_json() for item in evidence] == before
    assert build_fallback_report(evidence, [warning]).model_dump_json() == original


def test_comparison_only_is_honest_partial_report(facts):
    evidence = [facts["validate_comparison"].model_copy(update={"warnings": []})]
    result = build_fallback_report(evidence)
    assert len(result.report.findings) == len(result.report.recommendations) == 1
    assert "parcial" in result.report.overview.summary
    assert result.report.overview.evidence_strength == "weak"
    rules = {rule.rule_id for rule in result.report.limitations}
    assert {"partial_analysis", "initial_condition_not_checked", "no_reliable_yield"} <= rules
    assert validate_report_evidence(result.report, evidence, result.warnings)


@pytest.mark.parametrize("missing", ["compare_ndvi", "check_initial_condition", "compare_population",
                                     "application_compliance", "summarize_soil_analysis", "compare_soil_measurement_groups"])
def test_partial_evidence_never_invents_missing_findings(facts, missing):
    evidence = [item for key, item in facts.items() if key != missing]
    result = build_fallback_report(evidence)
    cited = {ref for item in result.report.findings + result.report.recommendations for ref in item.evidence_ids}
    assert cited == {item.evidence_id for item in evidence}
    assert any(rule.rule_id == "partial_analysis" for rule in result.report.limitations)
    assert facts[missing].evidence_id not in result.report.model_dump_json()


@pytest.mark.parametrize("mutation,code", [
    ("empty", "comparison_required"), ("no_comparison", "comparison_required"),
    ("blocked", "invalid_comparison"), ("duplicate", "invalid_fallback_input"),
    ("pair", "invalid_fallback_input"), ("period", "invalid_fallback_input"),
    ("nan", "invalid_fallback_input"), ("initial", "invalid_fallback_input"),
])
def test_invalid_facts_cannot_be_completed(facts, mutation, code):
    evidence = list(facts.values())
    if mutation == "empty":
        evidence = []
    elif mutation == "no_comparison":
        evidence = evidence[1:]
    elif mutation == "blocked":
        facts["validate_comparison"].allowed = False
    elif mutation == "duplicate":
        evidence.append(deepcopy(evidence[-1]))
    elif mutation == "pair":
        facts["compare_ndvi"].target_field_id = "PRIVATE_FIELD"
    elif mutation == "period":
        facts["compare_ndvi"].period = DatePeriod(start="2020-01-01", end="2020-02-01")
    elif mutation == "nan":
        facts["compare_ndvi"].target_mean = float("nan")
    elif mutation == "initial":
        facts["check_initial_condition"].mean_gap = None
    with pytest.raises(FallbackError) as caught:
        build_fallback_report(evidence)
    assert caught.value.code == code
    assert "PRIVATE" not in str(caught.value)
    assert caught.value.__context__ is None


@pytest.mark.parametrize("available,different", [(False, None), (True, False), (True, True)])
def test_initial_state_and_limitations_follow_facts(facts, available, different):
    item = facts["check_initial_condition"]
    item.available, item.different = available, different
    item.mean_gap = -0.1 if different else 0.0 if available else None
    result = build_fallback_report(list(facts.values()))
    finding = next(row for row in result.report.findings if row.evidence_ids == [item.evidence_id])
    rules = {rule.rule_id for rule in result.report.limitations}
    if not available:
        assert "indisponível" in finding.explanation and "initial_condition_unavailable" in rules
    elif different:
        assert "Há diferença inicial" in finding.explanation and "initial_condition_different" in rules
    else:
        assert "não demonstra equivalência" in finding.explanation
        assert "initial_condition_different" not in rules
    assert result.report.overview.evidence_strength == "weak"


@pytest.mark.parametrize("value", [-1e-12, 0.0, 1e-12, -0.0199999, 0.123456789, 1000.0])
def test_rounding_preserves_small_nonzero_values_sign_and_units(facts, value):
    item = facts["compare_ndvi"]
    item.mean_gap = value
    result = build_fallback_report([facts["validate_comparison"], item])
    finding = result.report.findings[-1]
    assert validate_report_evidence(result.report, [facts["validate_comparison"], item])
    if value != 0:
        assert "gap médio: 0." not in finding.explanation
    if value < 0:
        assert "gap médio: -" in finding.explanation


def test_unknown_soil_values_are_not_zero_and_missing_analyses_are_limited(facts):
    soil = facts["summarize_soil_analysis"]
    soil.metrics[0].mean = None
    soil.metrics[0].valid_n = 0
    result = build_fallback_report([facts["validate_comparison"], soil])
    text = result.report.findings[-1].explanation
    assert "resultado indisponível" in text
    rules = {rule.rule_id for rule in result.report.limitations}
    assert {"soil_units_unknown", "soil_dataset_scope", "soil_group_meaning", "soil_agronomic_reference"} <= rules


def test_soil_second_group_and_explicit_unit_are_preserved(facts):
    soil = facts["summarize_soil_analysis"]
    soil.measurement_group = "group_2"
    soil.metrics = [soil.metrics[0]]
    soil.metrics[0].unit = "%"
    result = build_fallback_report([facts["validate_comparison"], soil])
    assert result.report.findings[-1].title == "Solo — Conjunto 2"
    assert "%" in result.report.findings[-1].explanation


def test_repair_failure_can_use_same_evidence_and_trace_without_new_tools(context, monkeypatch):
    request, store = context
    invalid = response(types.Part(text="PRIVATE_INVALID_REPORT"))
    client = FakeClient(*planned_responses(request), invalid, invalid, done())
    draft = run_investigation_draft(request, client=client, settings=settings(), store=store)
    before = draft.model_dump_json()
    execute = Mock(side_effect=AssertionError("No repeated tools"))
    monkeypatch.setattr(registry, "execute_tool", execute)
    result = build_fallback_report(draft.planning.evidence, draft.planning.warnings, reason=draft.error.code)
    assert result.generated_by == "deterministic_fallback"
    assert draft.planning.trace.repair.status == "error"
    assert draft.model_dump_json() == before
    assert len(client.calls) == 5 and len(client.responses) == 1 and execute.call_count == 0
    assert "PRIVATE" not in result.model_dump_json()


def test_partial_planning_timeout_can_produce_limited_local_report(context):
    request, store = context
    client = FakeClient(response(call("validate_comparison", comparison_args(request))), gemini_client.GeminiError("timeout"))
    draft = run_investigation_draft(request, client=client, settings=settings(), store=store)
    assert draft.error.code == "timeout" and draft.planning.trace.repair is None
    result = build_fallback_report(draft.planning.evidence, draft.planning.warnings, reason=draft.error.code)
    assert result.report.overview.evidence_strength == "weak" and len(result.report.findings) == 1
    assert "Prazo" in result.warnings[-1].message


def test_real_analyses_in_reverse_direction_keep_target_reference_and_sign(context):
    request, store = context
    arguments = comparison_args(request)
    arguments["target_field_id"], arguments["reference_field_id"] = arguments["reference_field_id"], arguments["target_field_id"]
    evidence = [registry.execute_tool(name, arguments, store=store) for name in ("validate_comparison", "compare_ndvi")]
    result = build_fallback_report(evidence)
    finding = result.report.findings[-1]
    assert "NDVI médio do alvo: 0,5" in finding.explanation
    assert "NDVI médio da referência: 0,4" in finding.explanation
    assert "gap médio: 0,1." in finding.explanation


def test_provider_notice_is_not_a_quality_warning_but_quality_notices_remain(facts):
    comparison = facts["validate_comparison"].model_copy(update={"warnings": []})
    result = build_fallback_report([comparison])
    assert "data_quality_warnings" not in {item.rule_id for item in result.report.limitations}
    assert validate_report_evidence(result.report, [comparison], result.warnings)
    quality = ValidationIssue(code="quality", message="Cobertura parcial.")
    result = build_fallback_report([comparison], [quality])
    assert "data_quality_warnings" in {item.rule_id for item in result.report.limitations}
