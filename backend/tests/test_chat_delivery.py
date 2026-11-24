"""Final chat delivery, operational progress and downloadable report."""

from app.harness.chat_contracts import (
    AnswerStatus, ChatEnvelopeV2, ExecutiveInvestigationReportV2,
    InvestigativeChatResponse,
)
from app.harness.chat_responses import build_data_catalog_response, run_analytical_chat
from app.harness.chat_orchestrator import ConversationMemoryStore
from app.reports.chat_report import ChatReportStore, render_chat_report
from tests.test_chat_orchestrator import request, routed_dataset
from tests.test_executive_report import orchestration, request as executive_request, valid_payload


def test_data_catalog_lists_only_active_package_assets(routed_dataset):
    store, dataset_id = routed_dataset
    response = build_data_catalog_response(store.get(dataset_id))
    assert response.status == AnswerStatus.COMPLETE
    assert {item.name for item in response.assets} >= {"fields.csv", "ndvi_metadata.csv", "soil_analysis.csv"}
    assert all(item.record_count is None or item.record_count >= 0 for item in response.assets)


def test_general_chat_delivers_catalog_and_safe_progress(routed_dataset):
    store, dataset_id = routed_dataset
    events = []
    envelope = run_analytical_chat(
        request("O que a ferramenta consegue fazer?", dataset_id=dataset_id),
        store=store, memory=ConversationMemoryStore(), progress_sink=events.append,
    )
    assert envelope.response.kind == "capability_catalog"
    assert envelope.response.capabilities
    assert [item.stage.value for item in events] == ["question_received", "intent_classified"]
    assert all("prompt" not in item.message.casefold() for item in events)


def test_descriptive_chat_returns_insights_without_executive_report(routed_dataset):
    store, dataset_id = routed_dataset
    envelope = run_analytical_chat(
        request(
            "Qual é o resumo do vigor deste espaço?", dataset_id=dataset_id,
            target_field_id="103144", requested_mode="descriptive",
        ),
        store=store, memory=ConversationMemoryStore(),
    )
    assert envelope.response.kind == "descriptive"
    assert envelope.response.insights
    assert not hasattr(envelope.response, "report")


def test_executive_html_is_scrollable_self_contained_and_printable():
    chat_request = executive_request()
    run = orchestration(chat_request)
    report = ExecutiveInvestigationReportV2.model_validate(valid_payload(chat_request, run))
    envelope = ChatEnvelopeV2(
        turn_id=run.turn_id, intent=run.intent,
        response=InvestigativeChatResponse(status="complete", report=report, evidence=run.evidence),
    )
    store = ChatReportStore()
    store.save(envelope)
    html = render_chat_report(store.get(run.turn_id))
    assert "<h2>Resposta</h2>" in html
    assert "Principais insights" in html
    assert "Detalhes técnicos" in html
    assert "@page" in html and "size:A4" in html
    assert "<script" not in html
    assert "Próximos passos" not in html
