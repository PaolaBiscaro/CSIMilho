"""User-facing responses for the analytical chat.

The analytical modules remain the source of truth.  This module only turns
their validated, structured output into the closed chat response contracts.
"""

from app.data.session_store import NormalizedDataset, SessionStore, dataset_store
from app.harness.chat_contracts import (
    AnswerStatus, CapabilityCatalogChatResponse, ChatEnvelopeV2, ChatRequestV2,
    ChatResponseKind, DataCatalogChatResponse, DatasetAsset, DescriptiveChatResponse,
    DescriptiveInsight, UnsupportedChatResponse,
)
from app.harness.chat_orchestrator import (
    ConversationMemoryStore, build_capability_catalog, conversation_memory,
    classify_question, run_chat_orchestration,
)
from app.harness.executive_report import ExecutiveReportClient, run_investigative_chat


_ASSET_DESCRIPTIONS = {
    "fields.csv": "Cadastro e identificação dos talhões.",
    "ndvi_metadata.csv": "Observações temporais de vigor (NDVI).",
    "LAYER_MAP_PLANTING.csv": "Registros de plantio, área e população.",
    "LAYER_MAP_FERTILIZATION.csv": "Registros de aplicações e doses.",
    "service_orders.csv": "Catálogo das ordens e operações agrícolas.",
    "service_orders_fields.csv": "Vínculos entre ordens de serviço e talhões.",
    "soil_analysis.csv": "Amostras e medições químicas ou físicas do solo.",
}


def _record_counts(dataset: NormalizedDataset) -> dict[str, int | None]:
    return {
        "fields.csv": len(dataset.fields),
        "ndvi_metadata.csv": len(dataset.ndvi_observations),
        "LAYER_MAP_PLANTING.csv": len(dataset.planting_operations),
        "LAYER_MAP_FERTILIZATION.csv": len(dataset.fertilization_operations),
        "service_orders.csv": len(dataset.service_order_operations),
        "service_orders_fields.csv": sum(len(value) for value in dataset.service_order_mapping.values()),
        "soil_analysis.csv": len(dataset.soil_samples),
    }


def build_data_catalog_response(dataset: NormalizedDataset) -> DataCatalogChatResponse:
    counts = _record_counts(dataset)
    names = dataset.dataset_metadata.get("source_files") or list(_ASSET_DESCRIPTIONS)
    assets = [DatasetAsset(
        name=name,
        description=_ASSET_DESCRIPTIONS.get(name, "Arquivo disponível no pacote importado."),
        available=True,
        record_count=counts.get(name),
        supported_uses=["Descrição dos dados", "Análises compatíveis com os campos disponíveis"],
        limitations=[],
    ) for name in names]
    return DataCatalogChatResponse(
        answer=(f"O pacote contém {len(assets)} fontes de dados válidas. "
                "A lista abaixo mostra o que está disponível sem expor linhas brutas."),
        assets=assets,
    )


def _evidence_title(item) -> str:
    names = {
        "FieldNdviEvidence": "Comportamento do vigor no talhão",
        "NdviEvidence": "Diferenças de vigor entre os talhões",
        "NdviChangeEvidence": "Mudanças relevantes na série temporal",
        "PairedNdviTestEvidence": "Resultado do teste estatístico de NDVI",
        "OperationNdviEvidence": "Operações e comportamento do vigor",
        "FieldApplicationEvidence": "Execução das aplicações",
        "ApplicationEvidence": "Comparação das aplicações",
        "FieldPopulationEvidence": "População registrada no plantio",
        "PopulationEvidence": "Comparação da população de plantas",
        "SoilSummaryEvidence": "Contexto das análises de solo",
        "SoilGroupsEvidence": "Diferenças entre conjuntos de solo",
        "SoilStatisticalEvidence": "Teste estatístico das medições do solo",
    }
    return names.get(type(item).__name__, "Resultado analítico")


def _descriptive_response(run) -> DescriptiveChatResponse:
    conclusion = run.conclusion
    gaps = [] if conclusion is None else conclusion.gaps
    insights = [DescriptiveInsight(
        title=_evidence_title(item),
        explanation=(
            "O módulo calculou esta evidência a partir dos dados válidos do pacote. "
            "Os valores completos e o método ficam preservados na rastreabilidade técnica."
        ),
        evidence_ids=[item.evidence_id],
    ) for item in run.evidence]
    answer = (conclusion.answer if conclusion is not None else
              "Não foi necessário executar módulos analíticos para responder.")
    return DescriptiveChatResponse(
        status=AnswerStatus.PARTIAL if gaps else AnswerStatus.COMPLETE,
        answer=answer,
        insights=insights,
        gaps=gaps,
    )


def run_analytical_chat(
    request: ChatRequestV2,
    *,
    store: SessionStore = dataset_store,
    memory: ConversationMemoryStore = conversation_memory,
    client: ExecutiveReportClient | None = None,
    settings=None,
    progress_sink=None,
) -> ChatEnvelopeV2:
    """Route every supported chat message and return its final closed response."""
    previous = memory.get(request.prior_turn_id) if request.prior_turn_id is not None else None
    decision = classify_question(request, previous=previous)
    if decision.response_kind == ChatResponseKind.INVESTIGATION_REPORT:
        # run_investigative_chat owns the one shared 90-second deadline, including
        # deterministic modules, synthesis and the optional repair.
        return run_investigative_chat(
            request, client=client, settings=settings, store=store, memory=memory,
            progress_sink=progress_sink,
        )
    decision_run = run_chat_orchestration(
        request, store=store, memory=memory, progress_sink=progress_sink,
    )
    kind = decision_run.intent.response_kind
    if kind == ChatResponseKind.DATA_CATALOG:
        response = build_data_catalog_response(store.get(request.dataset_id))
    elif kind == ChatResponseKind.CAPABILITY_CATALOG:
        response = CapabilityCatalogChatResponse(
            status=AnswerStatus.COMPLETE,
            answer=("Estas são as análises disponíveis para o pacote atual. Cada item informa "
                    "se pode ser executado agora ou o que falta."),
            capabilities=build_capability_catalog(store.get(request.dataset_id)),
            gaps=[],
        )
    elif kind == ChatResponseKind.DESCRIPTIVE:
        response = _descriptive_response(decision_run)
    else:
        response = UnsupportedChatResponse(
            status=AnswerStatus.UNSUPPORTED,
            answer=decision_run.conclusion.answer,
            gaps=decision_run.conclusion.gaps,
        )
    return ChatEnvelopeV2(
        turn_id=decision_run.turn_id,
        intent=decision_run.intent,
        response=response,
    )
