"""Local narrative templates over existing evidence; no client, tools or settings.

Endpoint activation and collection of missing evidence belong to the orchestrator.
This module never reruns analysis, including after a failed report repair.
"""

from decimal import Decimal, ROUND_HALF_UP, localcontext
from typing import Literal

from pydantic import Field, TypeAdapter, ValidationError

from app.analytics.contracts import (
    ApplicationEvidence, ComparisonEvidence, InitialEvidence, NdviEvidence,
    PopulationEvidence, SoilGroupsEvidence, SoilSummaryEvidence,
)
from app.data.contracts import StrictModel, ValidationIssue
from app.harness.language_validation import validate_report_language
from app.harness.report_validation import required_limitations, validate_report_evidence
from app.harness.schemas import (
    AnalyticalEvidence, InvestigationReport, ReportFinding, ReportLimitation,
    ReportOrigin, ReportOverview, ReportRecommendation,
)


class FallbackResult(StrictModel):
    """Internal report with backend-owned origin and visible fallback notice."""

    generated_by: Literal[ReportOrigin.DETERMINISTIC_FALLBACK] = ReportOrigin.DETERMINISTIC_FALLBACK
    report: InvestigationReport
    warnings: list[ValidationIssue] = Field(default_factory=list)


class FallbackError(ValueError):
    """Insufficient or inconsistent facts cannot become a completed report."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__({
            "invalid_fallback_input": "As evidências do fallback são inválidas ou inconsistentes.",
            "comparison_required": "O fallback exige evidência de comparabilidade do par.",
            "invalid_comparison": "O par selecionado não permite esta comparação.",
        }[code])


_REASONS = {
    "missing_api_key": "Chave do provedor não configurada.",
    "rate_limit": "Limite de requisições do provedor atingido.",
    "timeout": "Prazo da geração automática excedido.",
    "authentication_error": "Autenticação no provedor indisponível.",
    "invalid_report": "O relatório gerado não passou pela validação de formato.",
    "invalid_report_evidence": "O relatório gerado não passou pela validação das evidências.",
    "invalid_report_language": "O relatório gerado não passou pela validação de linguagem.",
    "invalid_response": "O provedor não retornou uma resposta utilizável.",
    "unavailable": "Geração automática indisponível.",
}


def _number(value: float, places: int = 6) -> str:
    """Display rounding only; do not calculate new metrics or erase tiny signs."""
    original = Decimal(str(value))
    with localcontext() as ctx:
        ctx.prec = max(32, original.adjusted() + places + 3)
        rounded = original.quantize(Decimal(1).scaleb(-places), rounding=ROUND_HALF_UP)
    shown = original if rounded == 0 and original != 0 else rounded
    if shown == 0:
        return "0"
    text = format(shown, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text.replace(".", ",")


def _order(item: AnalyticalEvidence) -> tuple:
    # No inferred causal importance: stable presentation order, critical initial
    # differences first, soil before field signals and CALAGEM before other operations.
    if isinstance(item, ComparisonEvidence):
        rank, detail = 0, ""
    elif isinstance(item, InitialEvidence) and item.different is True:
        rank, detail = 1, ""
    elif isinstance(item, SoilSummaryEvidence):
        rank, detail = 2, item.measurement_group
    elif isinstance(item, SoilGroupsEvidence):
        rank, detail = 3, ""
    elif isinstance(item, NdviEvidence):
        rank, detail = 4, ""
    elif isinstance(item, InitialEvidence):
        rank, detail = 5, ""
    elif isinstance(item, ApplicationEvidence):
        rank, detail = 6, (item.operation.strip().upper() != "CALAGEM", item.operation)
    else:
        rank, detail = 7, ""
    return rank, detail, item.evidence_id


def _finding(item: AnalyticalEvidence) -> ReportFinding:
    if isinstance(item, ComparisonEvidence):
        title = "Comparabilidade do par"
        text = f"O par permite comparação observacional, com {item.score} critérios satisfeitos."
    elif isinstance(item, InitialEvidence):
        title = "Condição anterior ao plantio"
        if not item.available:
            text = "A condição inicial está indisponível; não é possível descartar diferenças anteriores ao plantio."
        else:
            text = (f"Gap médio de NDVI antes do plantio: {_number(item.mean_gap)}. "
                    f"Foram {item.paired_dates} datas pareadas. ")
            text += ("Há diferença inicial segundo a heurística operacional; essa condição limita a interpretação do manejo."
                     if item.different else "A heurística operacional não sinaliza diferença inicial; isso não demonstra equivalência entre os talhões.")
    elif isinstance(item, NdviEvidence):
        title = "Comparação observacional de NDVI"
        text = (f"NDVI médio do alvo: {_number(item.target_mean)}; "
                f"NDVI médio da referência: {_number(item.reference_mean)}; "
                f"gap médio: {_number(item.mean_gap)}. Foram {item.paired_dates} datas pareadas. "
                "O gap expressa alvo menos referência e não mede produtividade.")
    elif isinstance(item, PopulationEvidence):
        title = "População de plantas"
        text = (f"População do alvo: {_number(item.target_population_per_ha, 2)} plantas/ha; "
                f"população da referência: {_number(item.reference_population_per_ha, 2)} plantas/ha; "
                f"diferença de população: {_number(item.difference_percent, 2)}%. "
                "Esses valores descrevem os registros de plantio disponíveis.")
    elif isinstance(item, ApplicationEvidence):
        # Arbitrary operation labels are not trusted narrative. The linked
        # evidence retains the exact label for inspection.
        title = "Conformidade de calagem" if item.operation.strip().upper() == "CALAGEM" else "Conformidade de aplicação"
        text = (f"Conformidade do alvo: {_number(item.target_compliance_percent, 2)}%; "
                f"conformidade da referência: {_number(item.reference_compliance_percent, 2)}%. "
                f"Dose aplicada do alvo: {_number(item.target_applied_dose, 2)} kg/ha; "
                f"dose aplicada da referência: {_number(item.reference_applied_dose, 2)} kg/ha. "
                "A conformidade compara a dose aplicada com a configurada, sem avaliar adequação agronômica.")
    else:
        summary = isinstance(item, SoilSummaryEvidence)
        title = ("Solo — Conjunto 1" if item.measurement_group == "group_1" else "Solo — Conjunto 2") if summary else "Solo — contraste entre conjuntos"
        parts = [f"Contexto geral do dataset: {item.sample_count} amostras."]
        if summary and item.completeness_percent is not None:
            parts.append(f"Completude: {_number(item.completeness_percent, 2)}%.")
        for metric in sorted(item.metrics, key=lambda metric: metric.name):
            value = metric.mean if summary else metric.median_delta
            if value is None or metric.valid_n == 0:
                parts.append(f"{metric.name}: resultado indisponível por ausência de valores válidos.")
                continue
            label = "média" if summary else "mediana do delta"
            # Current W2 soil metrics have no documented units. If units are
            # provided later, preserve them rather than infer agronomic meaning.
            unit = f" {metric.unit}" if metric.unit else " (unidade não documentada)"
            parts.append(f"{metric.name}, {label}: {_number(value)}{unit}.")
        if not summary:
            parts.append("O delta representa Conjunto 2 menos Conjunto 1, sem interpretação de tempo ou profundidade.")
        parts.append("O solo não está vinculado aos talhões da comparação.")
        text = " ".join(parts)
    return ReportFinding(title=title, explanation=text, evidence_ids=[item.evidence_id])


def _recommendations(evidence: list[AnalyticalEvidence]) -> list[ReportRecommendation]:
    groups = [
        ((ComparisonEvidence,), "Conferir a comparabilidade e os avisos do pacote.",
         "A comparação depende dos critérios e da qualidade dos dados registrados."),
        ((InitialEvidence, NdviEvidence), "Conferir a cobertura temporal e os registros anteriores ao plantio.",
         "A interpretação do NDVI exige considerar lacunas e diferenças iniciais."),
        ((SoilSummaryEvidence, SoilGroupsEvidence), "Documentar unidades, origem das amostras e significado dos conjuntos de solo.",
         "As análises de solo têm escopo geral e não sustentam atribuição a talhões ou prescrição agronômica."),
        ((ApplicationEvidence, PopulationEvidence), "Conferir os registros operacionais, áreas e configurações de aplicação e plantio.",
         "As métricas operacionais descrevem registros disponíveis e precisam ser interpretadas com seus métodos e avisos."),
    ]
    return [ReportRecommendation(action=action, reason=reason,
                                 evidence_ids=[item.evidence_id for item in evidence if isinstance(item, kinds)])
            for kinds, action, reason in groups if any(isinstance(item, kinds) for item in evidence)]


def build_fallback_report(evidence: list[AnalyticalEvidence], warnings: list[ValidationIssue] = (),
                          *, reason: str = "unavailable") -> FallbackResult:
    """Build a validated local report without credentials or any external call.

    Requires a permitted comparison from this investigation. Partial evidence
    is usable but explicitly limited. Inputs are copied, never supplemented.
    Unknown failure codes receive a safe generic notice, never echoed text.
    """
    invalid = False
    try:
        evidence = TypeAdapter(list[AnalyticalEvidence]).validate_python([item.model_dump() for item in evidence])
        warnings = [ValidationIssue.model_validate(item.model_dump()) for item in warnings]
    except (ValidationError, AttributeError, TypeError):
        invalid = True
    if invalid:
        raise FallbackError("invalid_fallback_input")
    comparisons = [item for item in evidence if isinstance(item, ComparisonEvidence)]
    if not comparisons:
        raise FallbackError("comparison_required")
    if any(not item.allowed for item in comparisons):
        raise FallbackError("invalid_comparison")
    comparison = comparisons[0]
    context = (comparison.target_field_id, comparison.reference_field_id, comparison.period)
    if (len(comparisons) != 1 or len({item.evidence_id for item in evidence}) != len(evidence)
            or any((item.target_field_id, item.reference_field_id, item.period) != context
                   for item in evidence if hasattr(item, "target_field_id"))
            or any(item.available and (item.mean_gap is None or item.different is None)
                   for item in evidence if isinstance(item, InitialEvidence))):
        raise FallbackError("invalid_fallback_input")
    evidence = sorted(evidence, key=_order)
    limitations = required_limitations(evidence, warnings)
    expected = (InitialEvidence, NdviEvidence, PopulationEvidence, ApplicationEvidence, SoilSummaryEvidence, SoilGroupsEvidence)
    partial = any(not any(isinstance(item, kind) for item in evidence) for kind in expected)
    if partial:
        limitations.append(ReportLimitation(
            rule_id="partial_analysis", title="Análises parciais",
            explanation="Nem todas as análises estão disponíveis neste relatório; ausência de resultado não indica ausência de diferença.",
        ))
    summary = ("Relatório determinístico elaborado por templates locais com as evidências disponíveis. "
               "Os resultados descrevem associações observacionais, sem demonstrar efeito do manejo ou ganho de produtividade. ")
    summary += ("A cobertura de análises é parcial; consulte as limitações e os avisos."
                if partial else "Consulte os achados, as limitações e os avisos antes de interpretar a comparação.")
    report = InvestigationReport(
        overview=ReportOverview(headline="Relatório determinístico — comparação observacional", summary=summary,
                                evidence_strength="weak"),
        findings=[_finding(item) for item in evidence], limitations=limitations,
        recommendations=_recommendations(evidence),
    )
    # Templates pass the same checks as generated prose. Validation failures
    # surface to the caller; never publish a report that bypasses these checks.
    report = validate_report_language(validate_report_evidence(report, evidence, warnings))
    notice = ValidationIssue(code="deterministic_fallback", message=(
        _REASONS.get(reason, _REASONS["unavailable"]) + " Relatório produzido por templates locais."
    ))
    return FallbackResult(report=report, warnings=[*warnings, notice])
