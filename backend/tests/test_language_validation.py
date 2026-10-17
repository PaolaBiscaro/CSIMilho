"""Portuguese assertion/disclaimer pairs and complete narrative-field coverage."""

import pytest

from app.harness.language_validation import ReportLanguageError, validate_report_language
from app.harness.schemas import InvestigationReport
from tests.test_harness_schemas import report_payload


def with_text(payload, text, location="overview.summary"):
    report = InvestigationReport.model_validate(payload)
    if location.startswith("overview."):
        setattr(report.overview, location.split(".")[1], text)
    else:
        section, field = location.split(".")
        setattr(getattr(report, section)[0], field, text)
    return report


@pytest.mark.parametrize("text", [
    "O manejo causou a diferença de NDVI.",
    "A calagem provou a superioridade do manejo.",
    "O tratamento foi responsável pelo maior vigor.",
    "As práticas foram responsáveis pela diferença.",
    "A aplicação garantiu a produtividade.",
    "A calagem levou a um aumento de NDVI.",
    "O manejo levou à melhora do vigor.",
    "O manejo levou ao aumento da produtividade.",
    "O manejo levaria a maior vigor.",
    "A aplicação causaria melhoria.",
    "A melhoria foi causada pela calagem.",
    "A diferença é consequência direta do manejo.",
    "O vigor é resultado direto da adubação.",
    "Os dados comprovam um efeito causal do manejo.",
    "A causalidade foi demonstrada: o manejo causou a diferença.",
    "A intervenção provocou ganho de vigor.",
    "O manejo não causou qualquer mudança.",
    "Não se pode descartar que a calagem causou a diferença.",
    "Não é possível negar que a calagem causou a diferença.",
    "Não é impossível afirmar que a calagem causou a diferença.",
    "Não é possível afirmar que não se pode negar que o manejo causou a diferença.",
    "O tratamento não apenas causou a melhora, mas garantiu o resultado.",
    "Talvez o manejo tenha causado a diferença.",
    "A calagem pode ter causado a diferença.",
    'O modelo disse "o manejo causou a diferença".',
    "O MANEJO CAUSOU A DIFERENÇA.",
    "O manejo cau\u200bsou a diferença.",
    "O manejo foi\u00a0responsável\u00a0por melhorar o vigor.",
    "A análise foi responsável por demonstrar ganho agronômico.",
    "O manejo garante maior produtividade.",
    "A intervenção é a causa da diferença.",
    "As diferenças foram causadas pelo manejo.",
    "Os resultados foram garantidos pela adubação.",
    "O manejo terá efeitos causais no vigor.",
])
def test_causal_or_overconfident_statements_are_rejected(report_payload, text):
    with pytest.raises(ReportLanguageError) as caught:
        validate_report_language(with_text(report_payload, text))
    assert all(item.code == "causal_language" and item.location == "overview.summary" for item in caught.value.issues)


@pytest.mark.parametrize("text", [
    "O resultado está associado a diferenças de manejo.",
    "O sinal é compatível com o contexto observado.",
    "Os dados indicam diferenças entre os talhões.",
    "A comparação mostra diferenças de NDVI.",
    "Não é possível concluir causalidade.",
    "Não é possível afirmar que o manejo causou a diferença.",
    "Não é possível afirmar que causou.",
    "Não podemos concluir que a calagem levou à diferença.",
    "Os dados não permitem afirmar que o manejo garantiu o resultado.",
    "Não se pode concluir que o tratamento foi responsável por maior vigor.",
    "Não há evidência de que o manejo causou a diferença.",
    "Não há evidências suficientes para afirmar que a calagem provocou a diferença.",
    "Sem evidências para afirmar que o manejo causou a diferença.",
    "A análise não provou que o manejo causou a diferença.",
    "A análise não comprovou superioridade do manejo.",
    "Não é possível provar causalidade com esses dados.",
    "Não se pode provar causalidade com esses dados.",
    "Não há prova de causalidade.",
    "O relatório está sem prova causal.",
    "Não é correto dizer que a calagem causou a diferença.",
    "Não é possível afirmar que a calagem causou a diferença e garantiu o resultado.",
    "Não é possível afirmar que o manejo causou a diferença; os dados são observacionais.",
    'Evite o termo "causou".',
    'A palavra “garantiu” deve ser evitada.',
    "O transporte levou a equipe ao campo.",
    "O veículo levou as amostras para o laboratório.",
    "A equipe foi responsável por coletar as amostras.",
    "O técnico foi responsável por conferir os registros.",
    "O pareamento garantiu datas comuns.",
    "O schema garante o formato da resposta.",
    "A causa é desconhecida.",
    "Não conhecemos a causa.",
    "Investigar a causa exige novos dados.",
    "A coleta levou apenas tempo; os resultados são descritivos.",
    "O resultado associado ao manejo não demonstra causalidade.",
    "O registro EV-APP-CAUSA-001 está disponível.",
])
def test_local_disclaimers_observational_and_literal_uses_are_allowed(report_payload, text):
    report = with_text(report_payload, text)
    before = report.model_dump_json()
    validated = validate_report_language(report)
    assert validated == report and validated is not report
    assert report.model_dump_json() == before


@pytest.mark.parametrize("separator", [". ", "; ", "\n", ": ", ", mas ", ", porém ",
                                        ", contudo ", ", no entanto ", ", e ", " e sabemos que ", " porque "])
def test_disclaimer_does_not_license_next_assertion(report_payload, separator):
    text = "Não é possível afirmar que o manejo causou a diferença" + separator + "o manejo garantiu maior vigor."
    with pytest.raises(ReportLanguageError):
        validate_report_language(with_text(report_payload, text))


@pytest.mark.parametrize("location", ["overview.headline", "overview.summary", "findings.title", "findings.explanation",
                                       "limitations.title", "limitations.explanation", "recommendations.action", "recommendations.reason"])
def test_all_narrative_fields_are_checked(report_payload, location):
    report = with_text(report_payload, "O manejo causou a diferença.", location)
    with pytest.raises(ReportLanguageError) as caught:
        validate_report_language(report)
    expected = location if location.startswith("overview") else location.replace(".", "[0].")
    assert caught.value.issues[0].location == expected


def test_disclaimer_in_another_field_does_not_exempt_a_claim(report_payload):
    report = with_text(report_payload, "Não é possível afirmar que o manejo causou a diferença.")
    report.findings[0].explanation = "O manejo causou a diferença."
    with pytest.raises(ReportLanguageError) as caught:
        validate_report_language(report)
    assert {item.location for item in caught.value.issues} == {"findings[0].explanation"}


def test_errors_are_safe_deduplicated_and_actionable(report_payload):
    report = with_text(report_payload, "PRIVATE_SECRET causou a diferença e causou o resultado.")
    with pytest.raises(ReportLanguageError) as caught:
        validate_report_language(report)
    assert len(caught.value.issues) == 1
    assert "causar" in caught.value.issues[0].message
    assert "PRIVATE_SECRET" not in str(caught.value) + caught.value.issues[0].model_dump_json()
    assert caught.value.__context__ is None
