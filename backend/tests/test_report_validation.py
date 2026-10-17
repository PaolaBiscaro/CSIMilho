"""Adversarial report checks use real deterministic outputs as the fact source."""

from copy import deepcopy

import pytest

from app.analytics.evidence import EvidenceIdGenerator
from app.data.contracts import ValidationIssue
from app.harness.registry import TOOLS, execute_tool
from app.harness.report_validation import (
    ReportValidationError, required_limitations, validate_report_evidence,
)
from app.harness.schemas import InvestigationReport, ReportRecommendation, ReportLimitation
from tests.test_analytics import analytical_dataset
from tests.test_call_validators import comparison_args, context


@pytest.fixture
def facts(context):
    request, store = context
    ids = EvidenceIdGenerator()
    return {name: execute_tool(name, {"dataset_id": str(request.dataset_id)} if "soil" in name else comparison_args(request),
                               store=store, ids=ids) for name in TOOLS}


def report_for(evidence, text=None, ids=None, warnings=()):
    return InvestigationReport.model_validate({
        "overview": {"headline": "Comparação observacional", "summary": "Os dados têm limitações.", "evidence_strength": "weak"},
        "findings": [] if text is None else [{"title": "Resultado", "explanation": text,
                                               "evidence_ids": ids or [evidence[0].evidence_id]}],
        "limitations": [item.model_dump() for item in required_limitations(evidence, warnings)],
        "recommendations": [],
    })


def codes(report, evidence, warnings=()):
    with pytest.raises(ReportValidationError) as caught:
        validate_report_evidence(report, evidence, warnings)
    return {item.code for item in caught.value.issues}


@pytest.mark.parametrize("text", [
    "NDVI médio do alvo: 0,4; NDVI médio da referência: 0,5; gap: −0,1.",
    "NDVI médio do alvo: 0.4; gap alvo menos referência: -0,1000.",
    "NDVI médio do alvo: 4e-1; gap: -1e-1.",
    "Foram 5 datas pareadas.",
    "Em 01/12/2024, o NDVI do alvo foi 0,2.",
    "Em 2024-12-02, o NDVI da referência foi 0,4.",
    "O talhão 103144 foi analisado.",
])
def test_supported_formats_counts_dates_roles_and_labels(facts, text):
    evidence = [facts["compare_ndvi"]]
    report = report_for(evidence, text)
    assert validate_report_evidence(report, evidence) == report


@pytest.mark.parametrize("text,expected", [
    ("NDVI médio do alvo: 9,876.", "unsupported_number"),
    ("Gap: 0,1.", "sign_mismatch"),
    ("NDVI médio do alvo: 0,5.", "unsupported_number"),
    ("NDVI médio da referência: 0,4.", "unsupported_number"),
    ("NDVI médio do alvo: 0,4%.", "unit_mismatch"),
    ("NDVI médio do alvo: 40%.", "unsupported_number"),
    ("NDVI médio do alvo: 0.", "unsupported_number"),
    ("NDVI médio do alvo: 1,0.", "unsupported_number"),
    ("NDVI médio do alvo: 0,2.", "unsupported_number"),
    ("Foram 6 datas pareadas.", "unsupported_number"),
    ("Foram cinco datas pareadas.", "unsupported_number_format"),
    ("Em 2024-12-01, o NDVI do alvo foi 0,3.", "unsupported_number"),
    ("Em 2024-12-20, o NDVI do alvo foi 0,4.", "unsupported_date"),
    ("Em 31/02/2024, o NDVI do alvo foi 0,4.", "unsupported_date"),
    ("NDVI médio do alvo: 1e99999999.", "unsupported_number_format"),
])
def test_invented_numbers_wrong_sign_units_roles_and_dates(facts, text, expected):
    evidence = [facts["compare_ndvi"]]
    assert expected in codes(report_for(evidence, text), evidence)


@pytest.mark.parametrize("section", ["overview", "finding", "recommendation", "limitation"])
def test_unknown_ids_are_rejected_everywhere_even_without_numbers(facts, section):
    evidence = [facts["compare_ndvi"]]
    report = report_for(evidence)
    unknown = "EV-NDVI-999"
    if section == "overview":
        report.overview.summary += " " + unknown
    elif section == "finding":
        report = report_for(evidence, "Resultado qualitativo.", [unknown])
    elif section == "recommendation":
        report.recommendations = [ReportRecommendation(action="Conferir", reason="Conferir registros.", evidence_ids=[unknown])]
    else:
        report.limitations.append(ReportLimitation(title="Limite", explanation="Consultar " + unknown, rule_id="extra"))
    assert "unknown_evidence_id" in codes(report, evidence)


def test_numbers_must_come_from_cited_evidence_not_any_other_result(facts):
    evidence = [facts["compare_ndvi"], facts["compare_population"]]
    report = report_for(evidence, "População do alvo: 25 plantas/ha.")
    assert "unsupported_number" in codes(report, evidence)
    report.findings[0].evidence_ids = [facts["compare_population"].evidence_id]
    assert validate_report_evidence(report, evidence)


def test_overview_numbers_require_sentence_local_citations(facts):
    evidence = [facts["compare_ndvi"]]
    report = report_for(evidence)
    report.overview.summary = "NDVI médio do alvo: 0,4."
    assert "uncited_number" in codes(report, evidence)
    report.overview.summary = f"NDVI médio do alvo: 0,4 [{evidence[0].evidence_id}]."
    assert validate_report_evidence(report, evidence)
    report.overview.summary += " Gap: -0,1."
    assert "uncited_number" in codes(report, evidence)


@pytest.mark.parametrize("text", ["População do alvo: 25 plantas/ha.", "População da referência: 20 plants/ha.",
                                  "Diferença de população: 5 plantas/ha.", "Diferença de população: 25%."])
def test_population_units_are_attached_to_the_correct_fact(facts, text):
    evidence = [facts["compare_population"]]
    assert validate_report_evidence(report_for(evidence, text), evidence)


@pytest.mark.parametrize("text", ["População do alvo: 25 kg/ha.", "População do alvo: 25%.",
                                  "População do alvo: 25.", "Diferença de população: 5%.",
                                  "Diferença de população: -25%."])
def test_population_unit_and_sign_mismatches(facts, text):
    evidence = [facts["compare_population"]]
    assert codes(report_for(evidence, text), evidence) & {"unit_mismatch", "sign_mismatch"}


@pytest.mark.parametrize("text", [
    "Conformidade do alvo: 42,86%; conformidade da referência: 100%.",
    "Diferença de conformidade: -57,14 pontos percentuais.",
    "Dose aplicada do alvo: 75 kg/ha; dose configurada do alvo: 175 kg/ha.",
])
def test_application_rounding_and_percentage_points(facts, text):
    evidence = [facts["application_compliance"]]
    assert validate_report_evidence(report_for(evidence, text), evidence)


@pytest.mark.parametrize("text", [
    "Diferença de conformidade: -57,14%.",
    "Conformidade do alvo: 42,86 pontos percentuais.",
    "Dose aplicada do alvo: 175 kg/ha.",
    "Conformidade do alvo: 0,4286%.",
])
def test_percent_pp_dose_and_fraction_cannot_be_interchanged(facts, text):
    evidence = [facts["application_compliance"]]
    assert codes(report_for(evidence, text), evidence) & {"unit_mismatch", "unsupported_number"}


def test_thousands_and_rounding_are_not_a_global_tolerance(facts):
    evidence = [facts["compare_population"].model_copy(update={"target_population_per_ha": 61306.2749})]
    assert validate_report_evidence(report_for(evidence, "População do alvo: 61.306,27 plantas/ha."), evidence)
    assert validate_report_evidence(report_for(evidence, "População do alvo: 61,306.27 plantas/ha."), evidence)
    assert "unsupported_number" in codes(report_for(evidence, "População do alvo: 61.306,28 plantas/ha."), evidence)


def test_soil_units_cannot_be_invented_and_other_metric_cannot_supply_number(facts):
    soil = facts["summarize_soil_analysis"].model_copy(deep=True)
    metric = next(metric for metric in soil.metrics if metric.mean is not None)
    text = f"Média de {metric.name}: {metric.mean:.8f}."
    assert validate_report_evidence(report_for([soil], text), [soil])
    wrong = text[:-1] + " mg/kg."
    assert "unit_mismatch" in codes(report_for([soil], wrong), [soil])
    different = deepcopy(soil)
    different.metrics[0].mean = 12345.678
    text = f"Média de {metric.name}: 12345,678."
    # Pick a different named metric explicitly, not a bag of all soil numbers.
    if len(soil.metrics) > 1:
        text = f"Média de {soil.metrics[1].name}: 12345,678."
        assert "unsupported_number" in codes(report_for([different], text), [different])


def test_soil_group_labels_are_not_numbers_but_invented_group_is_rejected(facts):
    evidence = [facts["compare_soil_measurement_groups"]]
    assert validate_report_evidence(report_for(evidence, "Conjunto 1 e Conjunto 2; significado de _2 desconhecido."), evidence)
    assert codes(report_for(evidence, "Conjunto 9."), evidence)


def test_metadata_notes_and_bool_values_do_not_supply_numeric_facts(facts):
    evidence = [facts["compare_ndvi"].model_copy(update={"notes": ["O valor 9876 é apenas texto."], "tool_version": "9876.0"})]
    assert "unsupported_number" in codes(report_for(evidence, "NDVI médio do alvo: 9876."), evidence)


def test_duplicate_evidence_ids_are_rejected(facts):
    evidence = [facts["compare_ndvi"], facts["compare_ndvi"].model_copy(deep=True)]
    assert "duplicate_evidence_id" in codes(report_for(evidence), evidence)


@pytest.mark.parametrize("mutation", ["missing", "empty_meaning", "negated", "duplicate"])
def test_required_limitation_cannot_be_faked_with_id_only(facts, mutation):
    evidence = list(facts.values())
    report = report_for(evidence)
    if mutation == "missing":
        report.limitations.pop()
    elif mutation == "duplicate":
        report.limitations.append(report.limitations[0].model_copy())
    else:
        report.limitations[0].explanation = "Sem limitações." if mutation == "empty_meaning" else "Não há limitação observacional."
    assert codes(report, evidence) & {"missing_limitation", "invalid_limitation", "duplicate_limitation"}


def test_limitations_follow_available_evidence_and_quality(facts):
    full = {item.rule_id for item in required_limitations(list(facts.values()))}
    assert {"observational_comparison", "no_reliable_yield", "initial_gap_heuristic", "initial_condition_different",
            "soil_dataset_scope", "soil_group_meaning", "soil_units_unknown", "soil_agronomic_reference"} <= full
    assert "initial_condition_not_checked" not in full
    ndvi = facts["compare_ndvi"].model_copy(update={"paired_dates": 2})
    rules = {item.rule_id for item in required_limitations([ndvi], [ValidationIssue(code="quality", message="Aviso")])}
    assert {"few_paired_dates", "initial_condition_not_checked", "data_quality_warnings"} <= rules
    assert not any(key.startswith("soil_") for key in rules)
    initial = facts["check_initial_condition"].model_copy(update={"available": False, "different": None, "mean_gap": None})
    rules = {item.rule_id for item in required_limitations([initial])}
    assert "initial_condition_unavailable" in rules and "initial_condition_different" not in rules


def test_all_tools_valid_report_and_no_input_mutation(facts):
    evidence = list(facts.values())
    report = report_for(evidence)
    before = report.model_dump_json(), [item.model_dump_json() for item in evidence]
    result = validate_report_evidence(report, evidence)
    assert result == report and result is not report
    assert before == (report.model_dump_json(), [item.model_dump_json() for item in evidence])


def test_errors_are_located_and_do_not_echo_untrusted_content(facts):
    evidence = [facts["compare_ndvi"]]
    report = report_for(evidence, "PRIVATE_PAYLOAD 9876%", ["EV-PRIVATE-999"])
    with pytest.raises(ReportValidationError) as caught:
        validate_report_evidence(report, evidence)
    assert all(item.location == "findings[0].explanation" or item.location == "findings[0].title" for item in caught.value.issues)
    assert "PRIVATE" not in str(caught.value) + " ".join(item.model_dump_json() for item in caught.value.issues)


@pytest.mark.parametrize("text,valid", [
    ("O gap de NDVI é negativo.", True),
    ("O alvo apresenta NDVI médio menor que a referência.", True),
    ("O alvo não apresenta NDVI médio maior que a referência.", True),
    ("O gap de NDVI é positivo.", False),
    ("O gap de NDVI é nulo.", False),
    ("O alvo apresenta NDVI médio maior que a referência.", False),
    ("O alvo não apresenta NDVI médio menor que a referência.", False),
    ("Há aumento do NDVI médio do alvo frente à referência.", False),
])
def test_explicit_direction_words(facts, text, valid):
    evidence = [facts["compare_ndvi"]]
    report = report_for(evidence, text)
    if valid:
        assert validate_report_evidence(report, evidence)
    else:
        assert "direction_mismatch" in codes(report, evidence)


@pytest.mark.parametrize("text", ["Foram 5 datas positivas.", "Foram 5 amostras.", "Foram 5 registros."])
def test_other_counts_cannot_substitute_for_the_named_count(facts, text):
    evidence = [facts["compare_ndvi"]]
    assert "unsupported_number" in codes(report_for(evidence, text), evidence)


@pytest.mark.parametrize("unit", ["ppm", "mg/dm³", "cmolc/kg", "kg", "kg/ha"])
def test_soil_unit_invention_even_when_attached_to_number(facts, unit):
    soil = facts["summarize_soil_analysis"]
    metric = next(item for item in soil.metrics if item.mean is not None)
    text = f"Média de {metric.name}: {metric.mean:.8f}{unit}."
    assert "unit_mismatch" in codes(report_for([soil], text), [soil])


def test_identical_values_in_another_statistic_do_not_validate_a_mean(facts):
    soil = facts["summarize_soil_analysis"].model_copy(deep=True)
    metric = soil.metrics[0]
    metric.mean, metric.max = 2.25, 8.75
    report = report_for([soil], f"Média de {metric.name}: 8,75.")
    assert "unsupported_number" in codes(report, [soil])


@pytest.mark.parametrize("section", ["headline", "title", "recommendation", "limitation"])
def test_numbers_are_checked_outside_finding_explanations(facts, section):
    evidence = [facts["compare_ndvi"]]
    report = report_for(evidence, "Resultado descritivo.")
    text = f"NDVI médio do alvo: 9876 [{evidence[0].evidence_id}]."
    if section == "headline":
        report.overview.headline = text
    elif section == "title":
        report.findings[0].title = text
    elif section == "recommendation":
        report.recommendations.append(ReportRecommendation(action=text, reason="Conferir dados.", evidence_ids=[evidence[0].evidence_id]))
    else:
        report.limitations.append(ReportLimitation(title="Extra", explanation=text, rule_id="extra"))
    assert "unsupported_number" in codes(report, evidence)


def test_daily_direction_uses_the_date_not_the_overall_mean(facts):
    ndvi = facts["compare_ndvi"].model_copy(deep=True)
    ndvi.series[0].gap = 0.1
    text = "Em 2024-12-01, o gap de NDVI foi positivo: 0,1."
    assert validate_report_evidence(report_for([ndvi], text), [ndvi])
    assert "direction_mismatch" in codes(report_for([ndvi], text.replace("positivo", "negativo")), [ndvi])


def test_soil_pairs_use_named_sample_and_group(facts):
    soil = facts["compare_soil_measurement_groups"]
    metric = next(item for item in soil.metrics if item.pairs)
    pair = metric.pairs[0]
    text = f"Amostra {pair.sample_id}, {metric.name}, Conjunto 1: {pair.group_1:.8f}."
    assert validate_report_evidence(report_for([soil], text), [soil])
    invented = text.replace(f"{pair.group_1:.8f}", "99999,123")
    assert "unsupported_number" in codes(report_for([soil], invented), [soil])


def test_unavailable_values_cannot_be_reported_as_zero(facts):
    initial = facts["check_initial_condition"].model_copy(update={"available": False, "mean_gap": None, "different": None})
    assert "unsupported_number" in codes(report_for([initial], "Gap inicial: 0."), [initial])
