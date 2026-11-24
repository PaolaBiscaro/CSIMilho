from datetime import date
from uuid import uuid4

import pandas as pd
import pytest
from fastapi import HTTPException

from app.api import chat as chat_api
from app.api.datasets import _process_package
from app.data.session_store import SessionStore, dataset_store
from app.harness.chat_contracts import ChatRequestV2, GapType
from app.harness.chat_orchestrator import (
    ConversationMemoryStore,
    build_capability_catalog,
    classify_question,
    run_chat_orchestration,
)
from app.harness.orchestration_contracts import OrchestrationStage
from app.harness.registry import TOOLS
from app.main import create_app


@pytest.fixture
def routed_dataset(presentation_package):
    uploaded = _process_package(presentation_package)
    dataset = dataset_store.get(uploaded.dataset_id)
    dataset.ndvi_observations = pd.DataFrame([
        {
            "field_id": field_id,
            "date": date(2025, 1, day),
            "ndvi": value,
            "valid_pixels": 100,
        }
        for field_id, values in (
            ("103144", [0.20, 0.22, 0.24, 0.05, 0.07, 0.09]),
            ("103145", [0.10, 0.12, 0.14, -0.05, -0.03, -0.01]),
        )
        for day, value in enumerate(values, 1)
    ])
    dataset.planting_operations = pd.DataFrame([
        {
            "field_id": field_id,
            "operation": "MILHO",
            "operation_date": date(2025, 1, 5),
            "area_ha": 10.0,
            "population_per_ha": population,
        }
        for field_id, population in (("103144", 60000.0), ("103145", 58000.0))
    ])
    dataset.fertilization_operations = pd.DataFrame([
        {
            "field_id": field_id,
            "operation": "CALAGEM",
            "operation_date": date(2025, 1, 4),
            "area_ha": 10.0,
            "applied_dose_kg_ha": applied,
            "configured_dose_kg_ha": 100.0,
        }
        for field_id, applied in (("103144", 100.0), ("103145", 90.0))
    ])
    dataset.soil_samples = pd.DataFrame([
        {
            "sample_id": str(index),
            "scope": "dataset",
            "group_1": {"MO": float(index)},
            "group_2": {"MO": float(index + 1)},
        }
        for index in range(1, 7)
    ])
    store = SessionStore()
    return store, store.save(dataset)


def request(message, *, dataset_id=None, **fields):
    return ChatRequestV2(
        dataset_id=dataset_id or uuid4(),
        message=message,
        **fields,
    )


@pytest.mark.parametrize(
    ("message", "intent", "kind"),
    [
        ("Quais dados estão disponíveis neste pacote?", "data_catalog", "data_catalog"),
        ("O que a ferramenta consegue fazer?", "capability_catalog", "capability_catalog"),
        ("Qual é o resumo do NDVI disponível?", "descriptive_query", "descriptive"),
        ("Houve alguma mudança brusca na série de vigor?", "investigative_query", "investigation_report"),
        ("Qual foi o resultado do futebol?", "unsupported_query", "unsupported"),
    ],
)
def test_question_classifier_covers_product_intents(message, intent, kind):
    decision = classify_question(request(message))
    assert decision.intent.value == intent
    assert decision.response_kind.value == kind


def test_explicit_mode_corrects_automatic_classification():
    investigative = classify_question(request(
        "Resuma o NDVI.", requested_mode="investigative",
    ))
    assert investigative.response_kind.value == "investigation_report"

    descriptive = classify_question(request(
        "Compare e investigue os talhões.", requested_mode="descriptive",
    ))
    assert descriptive.response_kind.value == "descriptive"


def test_catalog_is_derived_from_registry_and_active_dataset(routed_dataset):
    store, dataset_id = routed_dataset
    catalog = build_capability_catalog(store.get(dataset_id))
    by_id = {item.capability_id: item for item in catalog}
    assert set(TOOLS) <= set(by_id)
    assert by_id["detect_field_ndvi_changes"].availability.value == "available_now"
    assert by_id["test_soil_measurement_groups"].availability.value == "available_now"
    assert by_id["yield_analysis"].availability.value == "needs_data"
    assert by_id["forecast"].availability.value == "needs_tooling"
    assert all(item.required_data for item in catalog)


def test_single_field_investigation_executes_every_planned_module(routed_dataset):
    store, dataset_id = routed_dataset
    memory = ConversationMemoryStore()
    run = run_chat_orchestration(
        request(
            "Investigue o vigor, as operações, a população e o contexto do solo.",
            dataset_id=dataset_id,
            target_field_id="103144",
        ),
        store=store,
        memory=memory,
    )
    completed = {item.tool for item in run.executions if item.status == "completed"}
    assert completed == {
        "analyze_field_ndvi", "detect_field_ndvi_changes",
        "summarize_field_application", "associate_field_operations_ndvi",
        "summarize_field_population", "summarize_soil_analysis",
        "compare_soil_measurement_groups", "test_soil_measurement_groups",
    }
    assert all(item.status == "executed" for item in run.hypotheses)
    assert run.conclusion.status == "partially_answered"
    assert GapType.MISSING_DATA in {gap.gap_type for gap in run.conclusion.gaps}
    assert "próximo" not in run.conclusion.answer.casefold()


def test_comparison_executes_test_effect_context_and_dataset_soil(routed_dataset):
    store, dataset_id = routed_dataset
    run = run_chat_orchestration(
        request(
            "Compare o vigor, a execução, a população e o solo dos dois espaços.",
            dataset_id=dataset_id,
            target_field_id="103144",
            reference_field_id="103145",
        ),
        store=store,
        memory=ConversationMemoryStore(),
    )
    completed = {item.tool for item in run.executions if item.status == "completed"}
    assert {
        "validate_comparison", "compare_ndvi", "test_paired_ndvi_difference",
        "check_initial_condition", "application_compliance", "compare_population",
        "summarize_soil_analysis", "compare_soil_measurement_groups",
        "test_soil_measurement_groups",
    } <= completed
    assert "sinal estatístico" in run.conclusion.answer
    assert len(run.conclusion.evidence_ids) == len(completed)


@pytest.mark.parametrize(("message", "expected_tools"), [
    ("Compare o comportamento das séries de vigor.", {"compare_ndvi", "test_paired_ndvi_difference", "check_initial_condition"}),
    ("Quais diferenças aparecem na execução da calagem?", {"application_compliance"}),
    ("A população registrada difere entre os talhões?", {"compare_population"}),
    ("O que os conjuntos de solo indicam?", {"summarize_soil_analysis", "compare_soil_measurement_groups", "test_soil_measurement_groups"}),
])
def test_questions_are_decomposed_into_registry_tools_not_prebuilt_answers(
    routed_dataset, message, expected_tools,
):
    store, dataset_id = routed_dataset
    run = run_chat_orchestration(
        request(
            message,
            dataset_id=dataset_id,
            target_field_id="103144",
            reference_field_id="103145",
        ),
        store=store,
        memory=ConversationMemoryStore(),
    )
    planned_tools = {tool for hypothesis in run.hypotheses for tool in hypothesis.tools}
    assert planned_tools == expected_tools
    assert all(execution.tool in TOOLS for execution in run.executions)


def test_descriptive_question_runs_descriptive_tools_not_hypothesis_tests(routed_dataset):
    store, dataset_id = routed_dataset
    run = run_chat_orchestration(
        request(
            "Qual é o resumo do vigor deste espaço?",
            dataset_id=dataset_id,
            target_field_id="103144",
            requested_mode="descriptive",
        ),
        store=store,
        memory=ConversationMemoryStore(),
    )
    assert [item.tool for item in run.executions] == ["analyze_field_ndvi"]
    assert run.intent.response_kind.value == "descriptive"


def test_insufficient_data_blocks_only_affected_tools(routed_dataset):
    store, dataset_id = routed_dataset
    dataset = store.get(dataset_id)
    dataset.ndvi_observations = dataset.ndvi_observations.loc[
        dataset.ndvi_observations["date"] <= date(2025, 1, 4)
    ]
    store.save(dataset, dataset_id=dataset_id)
    run = run_chat_orchestration(
        request(
            "Investigue mudanças na série de vigor.",
            dataset_id=dataset_id,
            target_field_id="103144",
        ),
        store=store,
        memory=ConversationMemoryStore(),
    )
    by_tool = {item.tool: item for item in run.executions}
    assert by_tool["analyze_field_ndvi"].status == "completed"
    assert by_tool["detect_field_ndvi_changes"].status == "blocked"
    assert by_tool["detect_field_ndvi_changes"].gap.gap_type == GapType.MISSING_DATA
    assert run.conclusion.status == "partially_answered"


def test_contextual_followup_reuses_only_structured_scope(routed_dataset):
    store, dataset_id = routed_dataset
    memory = ConversationMemoryStore()
    first = run_chat_orchestration(
        request(
            "Investigue mudanças no vigor deste espaço.",
            dataset_id=dataset_id,
            target_field_id="103144",
        ),
        store=store,
        memory=memory,
    )
    followup = run_chat_orchestration(
        request(
            "E o que aconteceu próximo das operações?",
            dataset_id=dataset_id,
            prior_turn_id=first.turn_id,
        ),
        store=store,
        memory=memory,
    )
    assert followup.intent.intent.value == "contextual_followup"
    assert followup.intent.uses_conversation_context is True
    assert followup.target_field_id == "103144"
    assert OrchestrationStage.CONTEXT_LOADED in {event.stage for event in followup.events}
    assert all(first.conclusion.answer not in event.message for event in followup.events)


def test_followup_cannot_cross_datasets(routed_dataset):
    store, dataset_id = routed_dataset
    memory = ConversationMemoryStore()
    first = run_chat_orchestration(
        request("Quais dados estão disponíveis?", dataset_id=dataset_id),
        store=store,
        memory=memory,
    )
    other_id = store.save(store.get(dataset_id))
    with pytest.raises(ValueError, match="mesmo dataset"):
        run_chat_orchestration(
            request("E as capacidades?", dataset_id=other_id, prior_turn_id=first.turn_id),
            store=store,
            memory=memory,
        )


def test_gaps_distinguish_tooling_data_and_scientific_limit(routed_dataset):
    store, dataset_id = routed_dataset
    run = run_chat_orchestration(
        request(
            "Use Mann-Whitney para provar o efeito causal do solo no vigor do talhão.",
            dataset_id=dataset_id,
            target_field_id="103144",
        ),
        store=store,
        memory=ConversationMemoryStore(),
    )
    assert {gap.gap_type for gap in run.conclusion.gaps} >= {
        GapType.MISSING_TOOLING, GapType.MISSING_DATA, GapType.SCIENTIFIC_LIMIT,
    }


def test_trace_is_ordered_safe_and_reaches_conclusion(routed_dataset):
    store, dataset_id = routed_dataset
    secret = "CHAVE-NAO-PODE-APARECER"
    run = run_chat_orchestration(
        request(
            f"Investigue mudanças no vigor. {secret}",
            dataset_id=dataset_id,
            target_field_id="103144",
        ),
        store=store,
        memory=ConversationMemoryStore(),
    )
    assert [event.sequence for event in run.events] == list(range(1, len(run.events) + 1))
    assert run.events[0].stage == OrchestrationStage.QUESTION_RECEIVED
    assert run.events[-1].stage == OrchestrationStage.CONCLUSION_READY
    assert secret not in run.model_dump_json()
    assert {event.stage for event in run.events} >= {
        OrchestrationStage.QUESTION_RECEIVED,
        OrchestrationStage.HYPOTHESES_PLANNED,
        OrchestrationStage.TOOL_STARTED,
        OrchestrationStage.TOOL_COMPLETED,
        OrchestrationStage.EVIDENCE_INTEGRATED,
        OrchestrationStage.CONCLUSION_READY,
    }


def test_out_of_scope_question_is_explained_without_tools(routed_dataset):
    store, dataset_id = routed_dataset
    run = run_chat_orchestration(
        request("Qual foi o resultado do futebol?", dataset_id=dataset_id),
        store=store,
        memory=ConversationMemoryStore(),
    )
    assert run.executions == []
    assert run.conclusion.status == "not_answered"
    assert run.conclusion.gaps[0].gap_type == GapType.OUT_OF_SCOPE


def test_chat_routes_are_exposed_with_closed_response_schemas():
    schema = create_app().openapi()
    assert "/api/chat/route" in schema["paths"]
    assert "/api/chat/investigate" in schema["paths"]
    assert "/api/chat/capabilities/{dataset_id}" in schema["paths"]
    assert schema["paths"]["/api/chat/route"]["post"]["requestBody"]


def test_api_callables_use_session_dataset_and_structured_memory(routed_dataset, monkeypatch):
    store, dataset_id = routed_dataset
    memory = ConversationMemoryStore()
    monkeypatch.setattr(chat_api, "dataset_store", store)
    monkeypatch.setattr(chat_api, "conversation_memory", memory)
    catalog = chat_api.capabilities(dataset_id)
    assert {item.capability_id for item in catalog} >= set(TOOLS)
    result = chat_api.route_chat(request(
        "Investigue mudanças no vigor.",
        dataset_id=dataset_id,
        target_field_id="103144",
    ))
    assert result.turn_id == memory.get(result.turn_id).turn_id


def test_api_errors_are_safe_and_classified(routed_dataset, monkeypatch):
    store, dataset_id = routed_dataset
    monkeypatch.setattr(chat_api, "dataset_store", store)
    monkeypatch.setattr(chat_api, "conversation_memory", ConversationMemoryStore())
    with pytest.raises(HTTPException) as missing_dataset:
        chat_api.capabilities(uuid4())
    assert missing_dataset.value.status_code == 404
    assert missing_dataset.value.detail["code"] == "dataset_not_found"

    with pytest.raises(HTTPException) as missing_turn:
        chat_api.route_chat(request(
            "Continue a análise.", dataset_id=dataset_id, prior_turn_id=uuid4(),
        ))
    assert missing_turn.value.status_code == 404
    assert missing_turn.value.detail["code"] == "previous_turn_not_found"
