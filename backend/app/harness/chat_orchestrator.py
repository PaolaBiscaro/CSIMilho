"""Deterministic routing and execution for the analytical chat.

This layer decides *what* can run. Gemini may later phrase the validated facts,
but it does not classify data eligibility or calculate analytical evidence.
"""

from threading import RLock
from collections.abc import Callable
import re
import unicodedata
from uuid import UUID, uuid4

from app.analytics.capabilities import assess_question_capabilities, missing_data_gap_for_tool
from app.analytics.common import AnalysisUnavailableError
from app.analytics.comparability import structural_pairs
from app.analytics.contracts import ComparisonArgs, SingleFieldArgs
from app.data.session_store import NormalizedDataset, SessionStore, dataset_store
from app.harness.chat_contracts import (
    AnswerGap, CapabilityAvailability, CapabilityItem, ChatRequestV2, ChatResponseKind,
    GapType, IntentDecision, IntentReason, QuestionIntent, RequestedMode,
)
from app.harness.orchestration_contracts import (
    AnalyticalHypothesisPlan, ChatOrchestrationRun, ConversationTurnMemory,
    IntegratedConclusion, OrchestrationEvent, OrchestrationStage, ToolExecutionSummary,
)
from app.harness.registry import TOOLS, execute_tool


def _plain(text: str) -> str:
    return "".join(
        character
        for character in unicodedata.normalize("NFKD", text.casefold())
        if not unicodedata.combining(character)
    )


class ConversationMemoryStore:
    """Session-only structured memory; prose from prior turns is never evidence."""

    def __init__(self) -> None:
        self._items: dict[UUID, ConversationTurnMemory] = {}
        self._lock = RLock()

    def save(self, item: ConversationTurnMemory) -> None:
        with self._lock:
            self._items[item.turn_id] = item.model_copy(deep=True)

    def get(self, turn_id: UUID) -> ConversationTurnMemory:
        with self._lock:
            if turn_id not in self._items:
                raise KeyError(turn_id)
            return self._items[turn_id].model_copy(deep=True)

    def clear(self) -> None:
        with self._lock:
            self._items.clear()


conversation_memory = ConversationMemoryStore()


_CAPABILITY_PATTERN = re.compile(
    r"\b(?:o que (?:a )?ferramenta (?:faz|consegue)|o que (?:voce|voces) (?:faz|consegue)|"
    r"quais (?:analises|testes|ferramentas|capacidades)|tipos? de analise)\b"
)
_DATA_PATTERN = re.compile(
    r"\b(?:quais dados|dados disponiveis|tipos? de dados|quais arquivos|o que ha nos dados|"
    r"que informacoes (?:temos|estao disponiveis))\b"
)
_INVESTIGATION_PATTERN = re.compile(
    r"\b(?:investig|compar|diferenc|relac|associ|diverg|anomali|mudanca|queda|aumento|"
    r"teste|hipotese|impacto|efeito|caus|indicam?|explica|brusc|influenc)\w*"
)
_UNSUPPORTED_PATTERN = re.compile(
    r"\b(?:futebol|eleicao|presidente|cotacao|criptomoeda|filme|receita culinaria|"
    r"previsao do tempo|horoscopo)\b"
)


def classify_question(
    request: ChatRequestV2,
    *,
    previous: ConversationTurnMemory | None = None,
) -> IntentDecision:
    """Classify intent locally, honoring an explicit user mode correction."""
    text = _plain(request.message)
    if previous is not None:
        if request.requested_mode == RequestedMode.INVESTIGATIVE:
            response_kind = ChatResponseKind.INVESTIGATION_REPORT
        elif request.requested_mode == RequestedMode.DESCRIPTIVE:
            response_kind = ChatResponseKind.DESCRIPTIVE
        else:
            response_kind = previous.intent.response_kind
        return IntentDecision(
            intent=QuestionIntent.CONTEXTUAL_FOLLOWUP,
            response_kind=response_kind,
            reason=IntentReason.FOLLOWUP_REFERENCE,
            requires_tools=response_kind in {
                ChatResponseKind.DESCRIPTIVE, ChatResponseKind.INVESTIGATION_REPORT,
            },
            requires_report=response_kind == ChatResponseKind.INVESTIGATION_REPORT,
            uses_conversation_context=True,
        )
    if _UNSUPPORTED_PATTERN.search(text):
        values = (QuestionIntent.UNSUPPORTED_QUERY, ChatResponseKind.UNSUPPORTED,
                  IntentReason.OUTSIDE_SUPPORTED_SCOPE, False)
    elif request.requested_mode == RequestedMode.DESCRIPTIVE:
        values = (QuestionIntent.DESCRIPTIVE_QUERY, ChatResponseKind.DESCRIPTIVE,
                  IntentReason.DESCRIPTIVE_SUMMARY_REQUEST, True)
    elif request.requested_mode == RequestedMode.INVESTIGATIVE:
        values = (QuestionIntent.INVESTIGATIVE_QUERY, ChatResponseKind.INVESTIGATION_REPORT,
                  IntentReason.HYPOTHESIS_OR_RELATIONSHIP_REQUEST, True)
    elif _CAPABILITY_PATTERN.search(text):
        values = (QuestionIntent.CAPABILITY_CATALOG, ChatResponseKind.CAPABILITY_CATALOG,
                  IntentReason.CAPABILITY_INVENTORY_REQUEST, False)
    elif _DATA_PATTERN.search(text):
        values = (QuestionIntent.DATA_CATALOG, ChatResponseKind.DATA_CATALOG,
                  IntentReason.DATA_INVENTORY_REQUEST, False)
    elif _INVESTIGATION_PATTERN.search(text):
        values = (QuestionIntent.INVESTIGATIVE_QUERY, ChatResponseKind.INVESTIGATION_REPORT,
                  IntentReason.HYPOTHESIS_OR_RELATIONSHIP_REQUEST, True)
    else:
        values = (QuestionIntent.DESCRIPTIVE_QUERY, ChatResponseKind.DESCRIPTIVE,
                  IntentReason.DESCRIPTIVE_SUMMARY_REQUEST, True)
    intent, kind, reason, tools = values
    return IntentDecision(
        intent=intent,
        response_kind=kind,
        reason=reason,
        requires_tools=tools,
        requires_report=kind == ChatResponseKind.INVESTIGATION_REPORT,
        uses_conversation_context=False,
    )


_TOOL_CATALOG = {
    "validate_comparison": ("Validar comparação", "descriptive", ["Dois talhões compatíveis"]),
    "compare_ndvi": ("Comparar vigor", "temporal", ["NDVI dos dois talhões nas mesmas datas"]),
    "test_paired_ndvi_difference": ("Testar diferença de vigor", "statistical", ["Cinco diferenças não empatadas de NDVI"]),
    "analyze_field_ndvi": ("Descrever vigor de um talhão", "temporal", ["NDVI vinculado ao talhão"]),
    "detect_field_ndvi_changes": ("Detectar mudanças no vigor", "temporal", ["Cinco observações de NDVI"]),
    "associate_field_operations_ndvi": ("Relacionar operações e vigor no tempo", "operational", ["Operações datadas e NDVI antes e depois"]),
    "summarize_field_population": ("Resumir população registrada", "operational", ["Plantio, área e população do talhão"]),
    "summarize_field_application": ("Resumir execução de aplicação", "operational", ["Dose configurada e aplicada no talhão"]),
    "check_initial_condition": ("Verificar condição inicial", "temporal", ["Três datas pareadas anteriores ao plantio"]),
    "compare_population": ("Comparar população", "operational", ["Plantio válido nos dois talhões"]),
    "application_compliance": ("Comparar execução de aplicação", "operational", ["Mesma operação com doses válidas nos dois talhões"]),
    "summarize_soil_analysis": ("Descrever o solo do conjunto", "soil", ["Amostras de solo com valores numéricos"]),
    "compare_soil_measurement_groups": ("Contrastar conjuntos de solo", "soil", ["Variáveis pareadas pela mesma amostra"]),
    "test_soil_measurement_groups": ("Testar diferenças entre conjuntos de solo", "statistical", ["Cinco pares não empatados por variável"]),
}


def _dataset_flags(dataset: NormalizedDataset) -> dict[str, bool]:
    ndvi = dataset.ndvi_observations
    counts = ndvi.groupby("field_id").size().to_dict() if not ndvi.empty else {}
    has_single_ndvi = any(count > 0 for count in counts.values())
    has_five_ndvi = any(count >= 5 for count in counts.values())
    pairs = structural_pairs(dataset.fields)
    series = {}
    if not ndvi.empty:
        for field_id, rows in ndvi.groupby("field_id"):
            series[str(field_id)] = {
                row.date: float(row.ndvi)
                for row in rows.itertuples(index=False)
                if row.ndvi is not None and row.valid_pixels > 0
            }
    has_pair = bool(pairs)
    has_ndvi_pair = False
    has_paired_test = False
    for pair in pairs:
        target = series.get(pair.target_field_id, {})
        reference = series.get(pair.reference_field_id, {})
        common = set(target) & set(reference)
        has_ndvi_pair |= bool(common)
        has_paired_test |= sum(abs(target[key] - reference[key]) > 1e-12 for key in common) >= 5
    soil = not dataset.soil_samples.empty
    soil_groups = soil and any(bool(value) for value in dataset.soil_samples.group_2)
    soil_test = False
    if soil_groups:
        metrics = set().union(*(set(row.group_1) & set(row.group_2) for row in dataset.soil_samples.itertuples(index=False)))
        for metric in metrics:
            deltas = []
            for row in dataset.soil_samples.itertuples(index=False):
                one, two = row.group_1.get(metric), row.group_2.get(metric)
                if isinstance(one, (int, float)) and isinstance(two, (int, float)):
                    deltas.append(two - one)
            if sum(abs(value) > 1e-12 for value in deltas) >= 5:
                soil_test = True
                break
    return {
        "single_ndvi": has_single_ndvi,
        "five_ndvi": has_five_ndvi,
        "pair": has_pair,
        "ndvi_pair": has_ndvi_pair,
        "paired_test": has_paired_test,
        "planting": not dataset.planting_operations.empty,
        "application": not dataset.fertilization_operations.empty,
        "soil": soil,
        "soil_groups": soil_groups,
        "soil_test": soil_test,
    }


def build_capability_catalog(dataset: NormalizedDataset) -> list[CapabilityItem]:
    """Expose the registry as product capabilities for the active dataset."""
    flags = _dataset_flags(dataset)
    availability = {
        "validate_comparison": flags["pair"],
        "compare_ndvi": flags["ndvi_pair"],
        "test_paired_ndvi_difference": flags["paired_test"],
        "analyze_field_ndvi": flags["single_ndvi"],
        "detect_field_ndvi_changes": flags["five_ndvi"],
        "associate_field_operations_ndvi": flags["single_ndvi"] and (flags["planting"] or flags["application"]),
        "summarize_field_population": flags["planting"],
        "summarize_field_application": flags["application"],
        "check_initial_condition": flags["pair"] and flags["planting"],
        "compare_population": flags["pair"] and flags["planting"],
        "application_compliance": flags["pair"] and flags["application"],
        "summarize_soil_analysis": flags["soil"],
        "compare_soil_measurement_groups": flags["soil_groups"],
        "test_soil_measurement_groups": flags["soil_test"],
    }
    result = []
    for name, tool in TOOLS.items():
        title, category, required = _TOOL_CATALOG[name]
        available = availability[name]
        result.append(CapabilityItem(
            capability_id=name,
            title=title,
            description=tool.description,
            category=category,
            availability=(CapabilityAvailability.AVAILABLE_NOW if available else CapabilityAvailability.NEEDS_DATA),
            required_data=required,
            methods=[tool.result.__name__],
            limitation=None if available else "Os dados ativos ainda não atendem aos requisitos mínimos.",
        ))
    result.extend([
        CapabilityItem(
            capability_id="yield_analysis", title="Analisar produtividade",
            description="Comparar rendimento ou colheita por talhão e período.", category="operational",
            availability=CapabilityAvailability.NEEDS_DATA,
            required_data=["Produtividade, unidade, área colhida, data e vínculo com talhão"],
            methods=[], limitation="O pacote atual não contém produtividade confiável.",
        ),
        CapabilityItem(
            capability_id="forecast", title="Prever comportamento futuro",
            description="Projetar valores futuros com validação temporal.", category="temporal",
            availability=CapabilityAvailability.NEEDS_TOOLING,
            required_data=["Histórico temporal suficiente para treino e validação"],
            methods=[], limitation="Não há modelo de previsão validado no harness.",
        ),
    ])
    return result


def _question_gaps(text: str) -> list[AnswerGap]:
    gaps = [
        AnswerGap(
            gap_type=GapType(gap.blocker_type),
            question_part=gap.title,
            explanation=gap.explanation,
            requirement=gap.explanation,
        )
        for gap in assess_question_capabilities(text)
    ]
    plain = _plain(text)
    if re.search(r"\b(?:caus|impacto|efeito|responsavel|influenc)\w*", plain):
        gaps.append(AnswerGap(
            gap_type=GapType.SCIENTIFIC_LIMIT,
            question_part="Atribuição de causa ou efeito",
            explanation="Os dados observacionais permitem identificar sinais conjuntos, mas não demonstram causalidade.",
            requirement="Desenho experimental ou quase experimental com controles e condição inicial válida.",
        ))
    if "solo" in plain and re.search(r"\b(?:talhao|grao 4|convencional|vigor)\b", plain):
        gaps.append(AnswerGap(
            gap_type=GapType.MISSING_DATA,
            question_part="Relação entre solo e talhão",
            explanation="As amostras de solo não possuem vínculo documentado com talhão ou coordenada.",
            requirement="Identificador de talhão ou coordenadas válidas para cada amostra de solo.",
        ))
    return _deduplicate_gaps(gaps)


def _deduplicate_gaps(gaps: list[AnswerGap]) -> list[AnswerGap]:
    result = []
    seen = set()
    for gap in gaps:
        key = (gap.gap_type, gap.question_part)
        if key not in seen:
            seen.add(key)
            result.append(gap)
    return result


def _topics(text: str) -> set[str]:
    plain = _plain(text)
    found = set()
    patterns = {
        "ndvi": r"\b(?:ndvi|vigor|serie|trajetoria|mudanca|queda|anomali)\w*",
        "operations": r"\b(?:operac|aplicac|calagem|correcao|dose|execucao|plantio)\w*",
        "population": r"\b(?:populacao|plantas por hectare|estande)\b",
        "soil": r"\b(?:solo|nutriente|quimic|argila|areia|silte|ph|materia organica)\w*",
    }
    for topic, pattern in patterns.items():
        if re.search(pattern, plain):
            found.add(topic)
    return found or {"ndvi", "operations", "population", "soil"}


def _plan_hypotheses(
    text: str, *, comparison: bool, investigative: bool,
) -> list[AnalyticalHypothesisPlan]:
    topics = _topics(text)
    plans = []
    if "ndvi" in topics:
        tools = (
            (["compare_ndvi", "test_paired_ndvi_difference", "check_initial_condition"]
             if investigative else ["compare_ndvi"])
            if comparison else
            (["analyze_field_ndvi", "detect_field_ndvi_changes"]
             if investigative else ["analyze_field_ndvi"])
        )
        plans.append(AnalyticalHypothesisPlan(
            hypothesis_id="ndvi_behavior",
            question=("Os talhões apresentam comportamento de vigor diferente?" if comparison
                      else "A série do talhão apresenta mudanças relevantes?"),
            scope="comparison" if comparison else "single_field", tools=tools, status="planned",
        ))
    if "operations" in topics:
        tools = (["application_compliance"] if comparison else
                 (["summarize_field_application", "associate_field_operations_ndvi"]
                  if investigative else ["summarize_field_application"]))
        plans.append(AnalyticalHypothesisPlan(
            hypothesis_id="operation_execution", question="Quais sinais aparecem na execução das operações?",
            scope="comparison" if comparison else "single_field", tools=tools, status="planned",
        ))
    if "population" in topics:
        plans.append(AnalyticalHypothesisPlan(
            hypothesis_id="plant_population", question="O registro de população apresenta diferença ou sinal relevante?",
            scope="comparison" if comparison else "single_field",
            tools=["compare_population" if comparison else "summarize_field_population"], status="planned",
        ))
    if "soil" in topics:
        plans.append(AnalyticalHypothesisPlan(
            hypothesis_id="soil_context", question="O que os conjuntos de solo permitem concluir no escopo do dataset?",
            scope="dataset", tools=(
                ["summarize_soil_analysis", "compare_soil_measurement_groups", "test_soil_measurement_groups"]
                if investigative else ["summarize_soil_analysis", "compare_soil_measurement_groups"]
            ),
            status="planned",
        ))
    return plans


def _integrate(evidence: list, gaps: list[AnswerGap]) -> IntegratedConclusion:
    statements = []
    for item in evidence:
        name = type(item).__name__
        if name == "PairedNdviTestEvidence":
            statements.append(
                "O teste pareado encontrou um sinal estatístico de diferença no NDVI."
                if item.significant else
                "O teste pareado não encontrou sinal estatístico suficiente de diferença no NDVI."
            )
        elif name == "NdviChangeEvidence":
            statements.append(
                f"A análise temporal identificou {len(item.changes)} mudança(s) adjacente(s) atípica(s) na série."
            )
        elif name == "OperationNdviEvidence":
            statements.append(
                f"Foram encontradas {len(item.links)} coincidência(s) temporal(is) entre operações e observações de NDVI, sem atribuição causal."
            )
        elif name == "SoilStatisticalEvidence":
            statements.append(
                f"Foram executados {item.executed_tests} teste(s) pareado(s) de solo no escopo geral do dataset."
            )
    if evidence and not statements:
        statements.append(f"Foram produzidas {len(evidence)} evidências válidas para responder à pergunta.")
    evidence_ids = [item.evidence_id for item in evidence]
    gaps = _deduplicate_gaps(gaps)
    if evidence_ids and gaps:
        status = "partially_answered"
        answer = " ".join(statements) + " As partes não sustentadas estão identificadas separadamente."
    elif evidence_ids:
        status = "answered"
        answer = " ".join(statements)
    else:
        status = "not_answered"
        answer = "A pergunta não pôde ser respondida com os dados e ferramentas atualmente disponíveis."
    return IntegratedConclusion(status=status, answer=answer, evidence_ids=evidence_ids, gaps=gaps)


def run_chat_orchestration(
    request: ChatRequestV2,
    *,
    store: SessionStore = dataset_store,
    memory: ConversationMemoryStore = conversation_memory,
    progress_sink: Callable[[OrchestrationEvent], None] | None = None,
) -> ChatOrchestrationRun:
    """Route, plan and exhaust every eligible deterministic analysis."""
    dataset = store.get(request.dataset_id)
    previous = memory.get(request.prior_turn_id) if request.prior_turn_id is not None else None
    if previous is not None and previous.dataset_id != request.dataset_id:
        raise ValueError("O complemento deve usar o mesmo dataset da conversa anterior.")
    target = request.target_field_id or (previous.target_field_id if previous else None)
    reference = request.reference_field_id or (previous.reference_field_id if previous else None)
    decision = classify_question(request, previous=previous)
    turn_id = uuid4()
    events = []

    def emit(stage, message, **fields):
        event = OrchestrationEvent(
            sequence=len(events) + 1, stage=stage, message=message, **fields,
        )
        events.append(event)
        if progress_sink is not None:
            progress_sink(event.model_copy(deep=True))

    emit(OrchestrationStage.QUESTION_RECEIVED, "Pergunta recebida para classificação.")
    emit(OrchestrationStage.INTENT_CLASSIFIED, f"Pergunta classificada como {decision.intent.value}.")
    if previous is not None:
        emit(OrchestrationStage.CONTEXT_LOADED, "Contexto estruturado da pergunta anterior carregado.")

    if decision.intent == QuestionIntent.UNSUPPORTED_QUERY:
        gap = AnswerGap(
            gap_type=GapType.OUT_OF_SCOPE, question_part="Tema da pergunta",
            explanation="A pergunta está fora do escopo analítico agrícola do FarmLab.",
            requirement="Pergunta sobre os dados agrícolas, operações, NDVI, solo ou capacidades do FarmLab.",
        )
        conclusion = IntegratedConclusion(
            status="not_answered", answer="A pergunta está fora do escopo do FarmLab.", gaps=[gap],
        )
        emit(OrchestrationStage.CONCLUSION_READY, "Limite de escopo identificado.")
        run = ChatOrchestrationRun(
            turn_id=turn_id, dataset_id=request.dataset_id, intent=decision,
            target_field_id=target, reference_field_id=reference,
            hypotheses=[], executions=[], evidence=[], conclusion=conclusion, events=events,
        )
        _remember(run, memory)
        return run

    if not decision.requires_tools:
        run = ChatOrchestrationRun(
            turn_id=turn_id, dataset_id=request.dataset_id, intent=decision,
            target_field_id=target, reference_field_id=reference,
            hypotheses=[], executions=[], evidence=[], conclusion=None, events=events,
        )
        _remember(run, memory)
        return run
    if target is None:
        gap = AnswerGap(
            gap_type=GapType.MISSING_DATA, question_part="Talhão da análise",
            explanation="A pergunta exige análise, mas nenhum talhão foi selecionado.",
            requirement="Selecionar um talhão para análise individual ou dois para comparação.",
        )
        conclusion = IntegratedConclusion(
            status="not_answered", answer="Não foi possível iniciar a análise sem um talhão selecionado.", gaps=[gap],
        )
        emit(OrchestrationStage.CONCLUSION_READY, "Análise bloqueada por seleção ausente.")
        run = ChatOrchestrationRun(
            turn_id=turn_id, dataset_id=request.dataset_id, intent=decision,
            hypotheses=[], executions=[], evidence=[], conclusion=conclusion, events=events,
        )
        _remember(run, memory)
        return run

    field_ids = {field.field_id for field in dataset.fields}
    if target not in field_ids or (reference is not None and reference not in field_ids):
        raise ValueError("O talhão selecionado não pertence ao dataset.")
    comparison = reference is not None
    hypotheses = _plan_hypotheses(
        request.message,
        comparison=comparison,
        investigative=decision.response_kind == ChatResponseKind.INVESTIGATION_REPORT,
    )
    emit(OrchestrationStage.HYPOTHESES_PLANNED, f"{len(hypotheses)} hipótese(s) analítica(s) planejada(s).")
    emit(OrchestrationStage.DATA_CHECKED, "Dados ativos verificados para as análises planejadas.")
    gaps = _question_gaps(request.message)
    executions = []
    evidence = []
    tool_names = []
    if comparison:
        tool_names.append("validate_comparison")
    tool_names.extend(tool for hypothesis in hypotheses for tool in hypothesis.tools)
    tool_names = list(dict.fromkeys(tool_names))
    comparison_allowed = True
    for name in tool_names:
        if name not in TOOLS:
            gap = AnswerGap(
                gap_type=GapType.MISSING_TOOLING, question_part=f"Ferramenta {name}",
                explanation="A análise planejada não possui ferramenta registrada.",
                requirement="Implementar e validar a ferramenta no registry.",
            )
            gaps.append(gap)
            executions.append(ToolExecutionSummary(tool=name, status="blocked", gap=gap))
            emit(OrchestrationStage.TOOL_BLOCKED, "Ferramenta não registrada.", tool=name, gap=gap)
            continue
        if comparison and not comparison_allowed and issubclass(TOOLS[name].parameters, ComparisonArgs):
            gap = AnswerGap(
                gap_type=GapType.SCIENTIFIC_LIMIT, question_part=f"Execução de {name}",
                explanation="O par selecionado não atende aos critérios mínimos de comparação.",
                requirement="Dois talhões com finalidade e cultura compatíveis e manejos distintos.",
            )
            gaps.append(gap)
            executions.append(ToolExecutionSummary(tool=name, status="blocked", gap=gap))
            emit(OrchestrationStage.TOOL_BLOCKED, "Análise bloqueada pela comparabilidade.", tool=name, gap=gap)
            continue
        parameters = TOOLS[name].parameters
        if issubclass(parameters, ComparisonArgs):
            args = {"dataset_id": str(request.dataset_id), "target_field_id": target,
                    "reference_field_id": reference, "period": "full_season"}
        elif issubclass(parameters, SingleFieldArgs):
            args = {"dataset_id": str(request.dataset_id), "field_id": target, "period": "full_season"}
        else:
            args = {"dataset_id": str(request.dataset_id)}
        emit(OrchestrationStage.TOOL_STARTED, "Ferramenta analítica iniciada.", tool=name)
        try:
            result = execute_tool(name, args, store=store)
        except AnalysisUnavailableError:
            catalog_gap = missing_data_gap_for_tool(name)
            gap = AnswerGap(
                gap_type=GapType.MISSING_DATA,
                question_part=catalog_gap.title if catalog_gap else f"Execução de {name}",
                explanation=(catalog_gap.explanation if catalog_gap else
                             "Os dados ativos não sustentam esta análise."),
                requirement=(catalog_gap.explanation if catalog_gap else
                             "Fornecer os dados mínimos exigidos pela ferramenta."),
            )
            gaps.append(gap)
            executions.append(ToolExecutionSummary(tool=name, status="blocked", gap=gap))
            emit(OrchestrationStage.TOOL_BLOCKED, "Ferramenta bloqueada por dados insuficientes.", tool=name, gap=gap)
            continue
        if name == "validate_comparison":
            comparison_allowed = result.allowed
        evidence.append(result)
        executions.append(ToolExecutionSummary(
            tool=name, status="completed", evidence_ids=[result.evidence_id], source_files=result.source_files,
        ))
        emit(OrchestrationStage.TOOL_COMPLETED, "Ferramenta concluída com evidência validada.",
             tool=name, evidence_ids=[result.evidence_id])
    execution_by_tool = {item.tool: item for item in executions}
    completed_hypotheses = []
    for hypothesis in hypotheses:
        related = [execution_by_tool[name] for name in hypothesis.tools if name in execution_by_tool]
        ids = [evidence_id for item in related for evidence_id in item.evidence_ids]
        hypothesis_gaps = [item.gap for item in related if item.gap is not None]
        status = ("executed" if ids and not hypothesis_gaps else
                  "partially_executed" if ids else "blocked")
        completed_hypotheses.append(hypothesis.model_copy(update={
            "status": status, "evidence_ids": ids, "gaps": hypothesis_gaps,
        }))
    conclusion = _integrate(evidence, gaps)
    emit(OrchestrationStage.EVIDENCE_INTEGRATED, "Evidências de módulos diferentes foram integradas.",
         evidence_ids=conclusion.evidence_ids)
    emit(OrchestrationStage.CONCLUSION_READY, "Conclusão analítica estruturada e pronta para síntese.",
         evidence_ids=conclusion.evidence_ids)
    run = ChatOrchestrationRun(
        turn_id=turn_id, dataset_id=request.dataset_id, intent=decision,
        target_field_id=target, reference_field_id=reference,
        hypotheses=completed_hypotheses, executions=executions, evidence=evidence,
        conclusion=conclusion, events=events,
    )
    _remember(run, memory)
    return run


def _remember(run: ChatOrchestrationRun, memory: ConversationMemoryStore) -> None:
    conclusion = run.conclusion
    memory.save(ConversationTurnMemory(
        turn_id=run.turn_id,
        dataset_id=run.dataset_id,
        intent=run.intent,
        target_field_id=run.target_field_id,
        reference_field_id=run.reference_field_id,
        hypothesis_ids=[item.hypothesis_id for item in run.hypotheses],
        evidence_ids=[] if conclusion is None else conclusion.evidence_ids,
        conclusion_status=None if conclusion is None else conclusion.status,
        conclusion_summary=None if conclusion is None else conclusion.answer,
        gap_types=[] if conclusion is None else [item.gap_type.value for item in conclusion.gaps],
    ))
