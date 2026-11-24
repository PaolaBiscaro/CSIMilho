import pytest

from app.analytics.capabilities import (
    assess_question_capabilities, capability_gap_for_code, missing_data_gap_for_tool,
)


def codes(question: str) -> list[str]:
    return [item.code for item in assess_question_capabilities(question)]


@pytest.mark.parametrize(("question", "expected"), [
    ("Existe diferença estatisticamente significativa? Faça um teste de hipótese.",
     ["analysis_missing_tooling_hypothesis_test"]),
    ("Calcule correlação de Pearson e uma regressão entre NDVI e população.",
     ["analysis_missing_tooling_correlation"]),
    ("Qual foi a produtividade em sacas e o rendimento da colheita?",
     ["analysis_missing_data_yield"]),
    ("O manejo foi responsável por essa diferença ou causou o resultado?",
     ["analysis_missing_data_causal_design"]),
    ("Faça uma previsão futura do NDVI.", ["analysis_missing_tooling_forecast"]),
    ("Gere um mapa de variabilidade espacial e zonas de manejo.",
     ["analysis_missing_tooling_spatial"]),
    ("Use PCA e clusterização para formar agrupamentos.",
     ["analysis_missing_tooling_multivariate"]),
])
def test_known_unsupported_requests_are_detected(question, expected):
    assert codes(question) == expected


def test_supported_descriptive_request_has_no_gap():
    assert codes("Compare o NDVI e a população entre o alvo e a referência.") == []


def test_multiple_terms_do_not_duplicate_one_gap():
    assert codes("Teste t, ANOVA e significância com p-valor") == ["analysis_missing_tooling_hypothesis_test"]


def test_catalog_lookup_rejects_unknown_warning_codes():
    gap = capability_gap_for_code("analysis_missing_tooling_hypothesis_test")
    assert gap is not None and gap.blocker_type == "missing_tooling"
    assert capability_gap_for_code("external_untrusted_code") is None


def test_missing_data_catalog_explains_required_inputs_for_each_optional_tool():
    for name in (
        "compare_ndvi", "check_initial_condition", "compare_population", "application_compliance",
        "summarize_soil_analysis", "compare_soil_measurement_groups",
    ):
        gap = missing_data_gap_for_tool(name)
        assert gap is not None and gap.blocker_type == "missing_data"
        assert gap.title.startswith("Dados ausentes —")
        assert capability_gap_for_code(gap.code) is gap
    assert missing_data_gap_for_tool("validate_comparison") is None


def test_context_exposes_blocker_type_without_conflating_tool_and_data():
    tooling = assess_question_capabilities("Faça um teste de hipótese.")[0].as_context()
    data = assess_question_capabilities("Compare a produtividade da colheita.")[0].as_context()
    assert tooling["blocker_type"] == "missing_tooling"
    assert data["blocker_type"] == "missing_data"
    assert set(tooling) == {"code", "status", "blocker_type", "title", "required"}
