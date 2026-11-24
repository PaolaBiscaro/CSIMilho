"""Local narrative templates over existing evidence; no client, tools or settings.

Endpoint activation and collection of missing evidence belong to the orchestrator.
This module never reruns analysis, including after a failed report repair.
"""

from decimal import Decimal, ROUND_HALF_UP, localcontext
from typing import Literal

from pydantic import Field, TypeAdapter, ValidationError

from app.analytics.contracts import (
    ApplicationEvidence, ComparisonEvidence, InitialEvidence, NdviEvidence,
    FieldApplicationEvidence, FieldNdviEvidence, FieldPopulationEvidence,
    PopulationEvidence, SoilGroupsEvidence, SoilSummaryEvidence,
)
from app.analytics.capabilities import capability_gap_for_code
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
            "scope_evidence_required": "O fallback exige evidência do talhão ou da comparação.",
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
    # Executive order: scope first, then the signals that answer the question;
    # dataset-wide soil context comes after field-level evidence.
    if isinstance(item, ComparisonEvidence):
        rank, detail = 0, ""
    elif isinstance(item, FieldNdviEvidence):
        rank, detail = 1, ""
    elif isinstance(item, FieldPopulationEvidence):
        rank, detail = 2, ""
    elif isinstance(item, FieldApplicationEvidence):
        rank, detail = 3, item.operation
    elif isinstance(item, InitialEvidence) and item.different is True:
        rank, detail = 1, ""
    elif isinstance(item, NdviEvidence):
        rank, detail = 2, ""
    elif isinstance(item, ApplicationEvidence):
        rank, detail = 3, (item.operation.strip().upper() != "CALAGEM", item.operation)
    elif isinstance(item, PopulationEvidence):
        rank, detail = 4, ""
    elif isinstance(item, InitialEvidence):
        rank, detail = 5, ""
    elif isinstance(item, SoilSummaryEvidence):
        rank, detail = 6, item.measurement_group
    elif isinstance(item, SoilGroupsEvidence):
        rank, detail = 7, ""
    else:
        rank, detail = 7, ""
    return rank, detail, item.evidence_id


def _finding(item: AnalyticalEvidence) -> ReportFinding:
    if isinstance(item, ComparisonEvidence):
        title = "Comparabilidade do par"
        text = f"O par permite comparação observacional, com {item.score} critérios satisfeitos."
    elif isinstance(item, FieldNdviEvidence):
        title = "Comportamento temporal do NDVI"
        text = (f"NDVI médio do talhão: {_number(item.mean_ndvi)}. "
                f"NDVI mínimo: {_number(item.min_ndvi)}. NDVI máximo: {_number(item.max_ndvi)}. "
                f"Variação entre a primeira e a última observação: {_number(item.total_change)}. "
                f"Foram {item.observations} observações e {len(item.abrupt_changes)} mudanças bruscas pela regra operacional. "
                "A regra sinaliza variações adjacentes para investigação e não identifica a origem.")
    elif isinstance(item, FieldPopulationEvidence):
        title = "População registrada no talhão"
        text = (f"População ponderada por área: {_number(item.population_per_ha, 2)} plantas/ha. "
                f"Foram {item.rows.valid} registros válidos e {item.rows.discarded} registros descartados.")
    elif isinstance(item, FieldApplicationEvidence):
        title = "Execução da aplicação no talhão"
        text = (f"Conformidade da aplicação: {_number(item.compliance_percent, 2)}%. "
                f"Dose aplicada: {_number(item.applied_dose, 2)} kg/ha. "
                f"Dose configurada: {_number(item.configured_dose, 2)} kg/ha. "
                "A conformidade descreve os registros e não avalia adequação agronômica.")
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
        title = "O vigor observado no recorte"
        if item.mean_gap == 0:
            insight = "O NDVI médio foi igual nos dois talhões."
        elif item.mean_gap > 0:
            insight = "O alvo apresentou NDVI médio maior que a referência no recorte."
        else:
            insight = "O alvo apresentou NDVI médio menor que a referência no recorte."
        text = (f"{insight} Gap de NDVI (alvo menos referência): {_number(item.mean_gap)}. "
                f"A leitura usa {item.paired_dates} datas pareadas e não mede produtividade.")
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
        same_execution = (item.target_compliance_percent == item.reference_compliance_percent
                          and item.target_applied_dose == item.reference_applied_dose)
        lead = ("Os registros mostram execução semelhante nos dois talhões. " if same_execution else
                "Os registros mostram diferenças de execução entre os talhões. ")
        text = (lead + f"Conformidade do alvo: {_number(item.target_compliance_percent, 2)}%. "
                f"Conformidade da referência: {_number(item.reference_compliance_percent, 2)}%. "
                "Isso descreve a execução registrada e não avalia adequação agronômica.")
    else:
        summary = isinstance(item, SoilSummaryEvidence)
        title = ("Solo — Conjunto 1" if item.measurement_group == "group_1" else "Solo — Conjunto 2") if summary else "Solo — contraste entre conjuntos"
        if summary:
            completeness = (f" A completude dos valores é {_number(item.completeness_percent, 2)}%."
                            if item.completeness_percent is not None else "")
            text = (f"O conjunto reúne {item.sample_count} amostras.{completeness} "
                    "Sem unidades documentadas e sem vínculo com os talhões, os valores não permitem classificar a condição do solo nem explicar o vigor observado.")
        else:
            text = (f"Há {item.sample_count} amostras com contrastes registrados entre os conjuntos. "
                    "Esses contrastes não representam mudança no tempo e, sem vínculo com os talhões, não explicam diferenças de vigor.")
    return ReportFinding(title=title, explanation=text, evidence_ids=[item.evidence_id])


def _recommendations(evidence: list[AnalyticalEvidence]) -> list[ReportRecommendation]:
    groups = [
        ((ComparisonEvidence,), "Conferir a comparabilidade e os avisos do pacote.",
         "A comparação depende dos critérios e da qualidade dos dados registrados.", "continue_now",
         "Quais limitações do par mais restringem a interpretação desta comparação?"),
        ((InitialEvidence, NdviEvidence), "Conferir a cobertura temporal e os registros anteriores ao plantio.",
         "A interpretação do NDVI exige considerar lacunas e diferenças iniciais.", "needs_data", None),
        ((SoilSummaryEvidence, SoilGroupsEvidence), "Documentar unidades, origem das amostras e significado dos conjuntos de solo.",
         "As análises de solo têm escopo geral e não sustentam atribuição a talhões ou prescrição agronômica.", "needs_data", None),
        ((ApplicationEvidence, PopulationEvidence), "Relacionar os registros operacionais aos sinais observados.",
         "Os dados já permitem verificar se execução, população e vigor se movem juntos no recorte, sem concluir causalidade.", "continue_now",
         "Os sinais de execução, população e NDVI aparecem nas mesmas datas ou períodos?"),
        ((FieldNdviEvidence,), "Conferir em campo as datas próximas às maiores mudanças da série.",
         "A trajetória mostra quando a mudança ocorreu, mas não identifica sua origem.", "continue_now",
         "Em quais datas ocorreram as maiores mudanças de NDVI e quais registros operacionais estão próximos delas?"),
        ((FieldApplicationEvidence, FieldPopulationEvidence), "Cruzar os sinais da série com os registros operacionais do talhão.",
         "Plantio e aplicações ajudam a contextualizar a trajetória, sem comprovar relação causal.", "continue_now",
         "Quais eventos operacionais coincidem com as mudanças observadas na série do talhão?"),
    ]
    return [ReportRecommendation(action=action, reason=reason, availability=availability,
                                 suggested_question=suggested_question,
                                 evidence_ids=[item.evidence_id for item in evidence if isinstance(item, kinds)])
            for kinds, action, reason, availability, suggested_question in groups
            if any(isinstance(item, kinds) for item in evidence)]


def _overview(evidence: list[AnalyticalEvidence], *, comparisons: bool, partial: bool,
              blockers: list) -> ReportOverview:
    """Build the top-down answer before exposing supporting detail."""
    ndvi = next((item for item in evidence if isinstance(item, NdviEvidence)), None)
    field_ndvi = next((item for item in evidence if isinstance(item, FieldNdviEvidence)), None)
    application = next((item for item in evidence if isinstance(item, ApplicationEvidence)), None)
    soil = any(isinstance(item, (SoilSummaryEvidence, SoilGroupsEvidence)) for item in evidence)
    missing_tooling = any(item is not None and item.blocker_type == "missing_tooling" for item in blockers)
    missing_data = any(item is not None and item.blocker_type == "missing_data" for item in blockers)

    if comparisons and ndvi is not None:
        headline = "O recorte permite comparar o vigor observado nos dois talhões"
        first = "Resposta direta: a comparação encontrou uma diferença média de NDVI no recorte disponível."
        second = ("Os registros de aplicação são semelhantes entre os talhões, mas não avaliam a adequação agronômica."
                  if application is not None and application.target_compliance_percent == application.reference_compliance_percent
                  else "Os registros operacionais ajudam a contextualizar o resultado, sem determinar sua origem.")
        if soil:
            third = "O solo ainda não pode explicar esse resultado porque as amostras não estão vinculadas aos talhões e não têm unidades documentadas."
        elif ndvi.paired_dates < 5:
            third = "Vale continuar, mas são necessárias mais datas pareadas para reconhecer uma tendência."
        else:
            third = "A leitura é observacional e não demonstra efeito do manejo nem produtividade."
    elif not comparisons and field_ndvi is not None:
        changed = bool(field_ndvi.abrupt_changes)
        headline = ("A série apresenta mudanças que merecem investigação" if changed
                    else "A série não apresenta mudanças bruscas pela regra disponível")
        first = ("Resposta direta: a trajetória contém mudanças bruscas sinalizadas para investigação."
                 if changed else "Resposta direta: a regra disponível não sinalizou mudanças bruscas na trajetória.")
        second = "Os registros mostram quando a mudança ocorreu, mas não identificam sua origem."
        third = "O resultado deve ser lido junto às datas de plantio e aplicações já registradas."
    else:
        headline = "Os dados disponíveis ainda não respondem à pergunta com segurança"
        first = "Resposta direta: o recorte não contém evidência suficiente para uma conclusão específica."
        second = "Os resultados disponíveis servem apenas como contexto e não sustentam uma conclusão adicional."
        third = "A leitura é parcial; as limitações abaixo identificam exatamente o que não foi respondido."

    if missing_tooling and missing_data:
        third = (
            "Partes diferentes da pergunta ficaram sem resposta: em uma, a ferramenta analítica necessária "
            "ainda não está implementada; em outra, os dados necessários estão ausentes, inválidos ou sem o vínculo exigido."
        )
    elif missing_tooling:
        third = "Parte da pergunta não pôde ser respondida porque a ferramenta analítica necessária ainda não está implementada."
    elif missing_data:
        third = "Parte da pergunta não pôde ser respondida porque os dados necessários estão ausentes, inválidos ou sem o vínculo exigido."
    elif partial and "Vale continuar" not in third and "necessário" not in third:
        third = "A leitura é parcial e as limitações abaixo identificam exatamente o que não foi respondido."
    return ReportOverview(headline=headline, summary=" ".join((first, second, third)), evidence_strength="weak")


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
    individual = [item for item in evidence if isinstance(item, (FieldNdviEvidence, FieldPopulationEvidence, FieldApplicationEvidence))]
    if not comparisons and not individual:
        raise FallbackError("scope_evidence_required")
    if comparisons and individual:
        raise FallbackError("invalid_fallback_input")
    if comparisons and any(not item.allowed for item in comparisons):
        raise FallbackError("invalid_comparison")
    if comparisons:
        comparison = comparisons[0]
        context = (comparison.target_field_id, comparison.reference_field_id, comparison.period)
        invalid_context = (len(comparisons) != 1 or any(
            (item.target_field_id, item.reference_field_id, item.period) != context
            for item in evidence if hasattr(item, "target_field_id")
        ))
    else:
        first = individual[0]
        context = (first.field_id, first.period)
        invalid_context = any((item.field_id, item.period) != context for item in individual)
    if (len({item.evidence_id for item in evidence}) != len(evidence) or invalid_context
            or any(item.available and (item.mean_gap is None or item.different is None)
                   for item in evidence if isinstance(item, InitialEvidence))):
        raise FallbackError("invalid_fallback_input")
    evidence = sorted(evidence, key=_order)
    limitations = required_limitations(evidence, warnings)
    expected = ((InitialEvidence, NdviEvidence, PopulationEvidence, ApplicationEvidence, SoilSummaryEvidence, SoilGroupsEvidence)
                if comparisons else (FieldNdviEvidence, FieldPopulationEvidence, FieldApplicationEvidence))
    partial = any(not any(isinstance(item, kind) for item in evidence) for kind in expected)
    if partial:
        limitations.append(ReportLimitation(
            rule_id="partial_analysis", title="Análises parciais",
            explanation="Nem todas as análises estão disponíveis neste relatório; ausência de resultado não indica ausência de diferença.",
        ))
    blockers = [capability_gap_for_code(item.code) for item in warnings]
    report = InvestigationReport(
        overview=_overview(evidence, comparisons=bool(comparisons), partial=partial, blockers=blockers),
        findings=[_finding(item) for item in evidence], limitations=limitations,
        recommendations=_recommendations(evidence),
    )
    # Templates pass the same checks as generated prose. Validation failures
    # surface to the caller; never publish a report that bypasses these checks.
    report = validate_report_language(validate_report_evidence(report, evidence, warnings))
    notice = ValidationIssue(code="deterministic_fallback", message=(
        _REASONS.get(reason, _REASONS["unavailable"]) + " Relatório elaborado com as evidências calculadas."
    ))
    return FallbackResult(report=report, warnings=[*warnings, notice])
