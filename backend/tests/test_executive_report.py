"""Executive v2 synthesis uses only validated facts and never publishes fallback."""

from copy import deepcopy
import json
from uuid import uuid4

from google.genai import types
from fastapi import HTTPException
import pytest

from app.api import chat as chat_api
from app.analytics.contracts import PairedNdviTestEvidence
from app.harness import gemini_client
from app.harness.chat_contracts import ChatRequestV2, ExecutiveInvestigationReportV2, IntentDecision
from app.harness.executive_report import (
    ExecutiveReportError, build_executive_context, executive_provider_schema, synthesize_executive_report,
)
from app.harness.orchestration_contracts import (
    AnalyticalHypothesisPlan, ChatOrchestrationRun, IntegratedConclusion,
    OrchestrationEvent, OrchestrationStage, ToolExecutionSummary,
)
from tests.test_gemini_client import settings
from tests.test_orchestrator import FakeClient, response


EVIDENCE_ID = "EV-NDVI-TEST-001"


def request():
    return ChatRequestV2(
        dataset_id=uuid4(),
        message="O vigor dos dois talhões apresenta diferença consistente durante a safra?",
        requested_mode="investigative",
        target_field_id="103144",
        reference_field_id="103145",
    )


def orchestration(chat_request):
    evidence = PairedNdviTestEvidence(
        evidence_id=EVIDENCE_ID,
        unit="NDVI",
        source_files=["ndvi_metadata.csv"],
        method="Teste exato pareado de sinais",
        observation_count=6,
        tool_version="1.0.0",
        target_field_id="103144",
        reference_field_id="103145",
        period="full_season",
        pair_count=6,
        nonzero_pairs=6,
        positive_pairs=5,
        negative_pairs=1,
        target_median=0.42,
        reference_median=0.31,
        median_difference=0.11,
        confidence_level=0.95,
        median_ci_low=0.04,
        median_ci_high=0.18,
        p_value=0.03125,
        rank_biserial=0.666666,
        alpha=0.05,
        significant=True,
    )
    events = [
        OrchestrationEvent(sequence=1, stage="question_received", message="Pergunta recebida."),
        OrchestrationEvent(sequence=2, stage="intent_classified", message="Investigação selecionada."),
        OrchestrationEvent(sequence=3, stage="hypotheses_planned", message="Hipótese planejada."),
        OrchestrationEvent(sequence=4, stage="data_checked", message="Dados conferidos."),
        OrchestrationEvent(sequence=5, stage="tool_started", message="Teste iniciado.",
                           tool="test_paired_ndvi_difference"),
        OrchestrationEvent(sequence=6, stage="tool_completed", message="Teste concluído.",
                           tool="test_paired_ndvi_difference", evidence_ids=[EVIDENCE_ID]),
        OrchestrationEvent(sequence=7, stage="evidence_integrated", message="Evidência integrada.",
                           evidence_ids=[EVIDENCE_ID]),
        OrchestrationEvent(sequence=8, stage="conclusion_ready", message="Conclusão pronta.",
                           evidence_ids=[EVIDENCE_ID]),
    ]
    return ChatOrchestrationRun(
        turn_id=uuid4(),
        dataset_id=chat_request.dataset_id,
        intent=IntentDecision(
            intent="investigative_query",
            response_kind="investigation_report",
            reason="hypothesis_or_relationship_request",
            requires_tools=True,
            requires_report=True,
            uses_conversation_context=False,
        ),
        target_field_id="103144",
        reference_field_id="103145",
        hypotheses=[AnalyticalHypothesisPlan(
            hypothesis_id="ndvi_behavior",
            question="Os talhões apresentam comportamento de vigor diferente?",
            scope="comparison",
            tools=["test_paired_ndvi_difference"],
            status="executed",
            evidence_ids=[EVIDENCE_ID],
        )],
        executions=[ToolExecutionSummary(
            tool="test_paired_ndvi_difference",
            status="completed",
            evidence_ids=[EVIDENCE_ID],
            source_files=["ndvi_metadata.csv"],
        )],
        evidence=[evidence],
        conclusion=IntegratedConclusion(
            status="answered",
            answer="O teste pareado encontrou sinal estatístico de diferença no vigor.",
            evidence_ids=[EVIDENCE_ID],
        ),
        events=events,
    )


def valid_payload(chat_request, run):
    deterministic = build_executive_context(chat_request, run)
    return {
        "question": chat_request.message,
        "scope_summary": "Comparação do comportamento de vigor dos talhões nas datas pareadas.",
        "executive_answer": {
            "status": "indicative",
            "headline": "Os talhões apresentaram diferença consistente no vigor observado.",
            "answer": (
                "A diferença mediana de NDVI foi 0,11, com o alvo acima da referência. "
                "O resultado é observacional e não atribui a diferença ao manejo."
            ),
            "confidence": "moderate",
            "main_caveat": "A comparação identifica o sinal, mas não determina sua causa.",
            "evidence_ids": [EVIDENCE_ID],
        },
        "insights": [{
            "claim": "A maior parte das diferenças pareadas favoreceu o talhão alvo.",
            "analytical_method": "Teste exato pareado de sinais.",
            "evidence_summary": "O p-valor observado foi 0,03125.",
            "interpretation": "O padrão entre datas é mais consistente do que uma diferença isolada.",
            "uncertainty": "A evidência não permite afirmar que o manejo causou a diferença.",
            "evidence_ids": [EVIDENCE_ID],
            "chart_ids": ["chart-ndvi-comparison"],
        }],
        "charts": [{
            "chart_id": "chart-ndvi-comparison",
            "title": "O vigor do alvo permaneceu acima da referência na maior parte das datas",
            "takeaway": "A trajetória pareada sustenta o sinal encontrado pelo teste.",
            "evidence_ids": [EVIDENCE_ID],
        }],
        "unanswered_parts": deterministic["unanswered_parts"],
        "limitations": deterministic["required_limitations"],
        "field_recommendations": [
            "Conferir em campo se o contraste visual de vigor permanece nas áreas observadas."
        ],
        "technical_appendix": deterministic["technical_appendix"],
    }


def report_response(payload):
    return response(types.Part(text=json.dumps(payload, ensure_ascii=False)))


def test_valid_report_is_top_down_traceable_and_uses_structured_output():
    chat_request = request()
    run = orchestration(chat_request)
    client = FakeClient(report_response(valid_payload(chat_request, run)))
    report = synthesize_executive_report(
        chat_request, run, client=client, settings=settings(GEMINI_TIMEOUT_SECONDS=8),
    )
    assert report.executive_answer.headline.startswith("Os talhões")
    assert report.insights[0].evidence_ids == [EVIDENCE_ID]
    assert report.technical_appendix.source_files == ["ndvi_metadata.csv"]
    assert len(client.calls) == 1
    contents, config, remaining = client.calls[0]
    assert 0 < remaining <= 8
    assert config.response_schema is None
    assert config.response_json_schema == executive_provider_schema()
    assert "additionalProperties" not in json.dumps(config.response_json_schema)
    assert set(config.response_json_schema["properties"]) == {"headline", "answer", "main_caveat"}
    body = json.loads(contents[0].parts[0].text)
    assert set(body) == {"facts"}
    assert "raw_csv" not in contents[0].parts[0].text


def test_unsupported_number_triggers_one_repair_with_same_facts():
    chat_request = request()
    run = orchestration(chat_request)
    invalid = valid_payload(chat_request, run)
    invalid["executive_answer"]["answer"] = "A diferença observada foi 0,777."
    valid = valid_payload(chat_request, run)
    client = FakeClient(report_response(invalid), report_response(valid))
    report = synthesize_executive_report(
        chat_request, run, client=client, settings=settings(GEMINI_TIMEOUT_SECONDS=8),
    )
    assert "0,11" in report.executive_answer.answer
    assert len(client.calls) == 2
    first = json.loads(client.calls[0][0][0].parts[0].text)
    repair = json.loads(client.calls[1][0][0].parts[0].text)
    assert repair["facts"] == first["facts"]
    assert "schema" not in repair
    assert {item["code"] for item in repair["validation_errors"]} >= {
        "direct_answer_without_result", "unsupported_number",
    }
    assert "0,777" not in client.calls[1][0][0].parts[0].text


def test_generic_evidence_count_is_repaired_into_a_direct_answer():
    chat_request = request()
    run = orchestration(chat_request)
    invalid = valid_payload(chat_request, run)
    invalid["executive_answer"]["answer"] = "Foram produzidas 2 evidências válidas para responder à pergunta."
    valid = valid_payload(chat_request, run)
    client = FakeClient(report_response(invalid), report_response(valid))

    report = synthesize_executive_report(
        chat_request, run, client=client, settings=settings(GEMINI_TIMEOUT_SECONDS=8),
    )

    assert report.executive_answer.answer == valid["executive_answer"]["answer"]
    repair = json.loads(client.calls[1][0][0].parts[0].text)
    assert repair["validation_errors"][0]["code"] == "generic_process_answer"


def test_analyzable_report_without_a_concrete_result_is_repaired():
    chat_request = request()
    run = orchestration(chat_request)
    invalid = valid_payload(chat_request, run)
    invalid["executive_answer"]["answer"] = "Os talhões apresentaram comportamentos diferentes no período."
    valid = valid_payload(chat_request, run)
    client = FakeClient(report_response(invalid), report_response(valid))

    report = synthesize_executive_report(
        chat_request, run, client=client, settings=settings(GEMINI_TIMEOUT_SECONDS=8),
    )

    assert "0,11" in report.executive_answer.answer
    repair = json.loads(client.calls[1][0][0].parts[0].text)
    assert repair["validation_errors"][0]["code"] == "direct_answer_without_result"


def test_number_present_in_user_field_label_can_be_repeated_in_narrative():
    chat_request = request().model_copy(update={
        "message": "O talhão Grão 4.0 apresenta diferença consistente durante a safra?"
    })
    run = orchestration(chat_request)
    payload = valid_payload(chat_request, run)
    payload["executive_answer"]["headline"] = "O Grão 4.0 apresentou um sinal consistente."
    client = FakeClient(report_response(payload))
    report = synthesize_executive_report(
        chat_request, run, client=client, settings=settings(GEMINI_TIMEOUT_SECONDS=8),
    )
    assert "4.0" in report.executive_answer.headline
    assert len(client.calls) == 1


def test_provider_recommendations_are_ignored_because_backend_owns_the_report_structure():
    chat_request = request()
    run = orchestration(chat_request)
    payload = valid_payload(chat_request, run)
    payload["field_recommendations"] = [
        "Conferir em campo o registro correspondente às 6 observações pareadas."
    ]
    client = FakeClient(report_response(payload))
    report = synthesize_executive_report(
        chat_request, run, client=client, settings=settings(GEMINI_TIMEOUT_SECONDS=8),
    )
    assert report.field_recommendations == []
    assert len(client.calls) == 1


def test_provider_cannot_change_backend_owned_technical_blocks():
    chat_request = request()
    run = orchestration(chat_request)
    attempted = valid_payload(chat_request, run)
    attempted["question"] = "Pergunta alterada pelo provedor"
    attempted["unanswered_parts"] = [{"gap_type": "missing_data", "question_part": "Inventada", "explanation": "Inventada", "requirement": "Inventada"}]
    attempted["limitations"] = []
    attempted["technical_appendix"]["methods_summary"] = ["Método inventado"]
    client = FakeClient(report_response(attempted))

    report = synthesize_executive_report(
        chat_request, run, client=client, settings=settings(GEMINI_TIMEOUT_SECONDS=8),
    )

    deterministic = build_executive_context(chat_request, run)
    assert report.question == chat_request.message
    assert report.unanswered_parts == []
    assert report.technical_appendix.model_dump(mode="json") == deterministic["technical_appendix"]
    assert report.technical_appendix.methods_summary != ["Método inventado"]
    assert len(client.calls) == 1


def test_provider_technical_mistakes_are_normalized_instead_of_blocking_report():
    chat_request = request()
    run = orchestration(chat_request)
    attempted = valid_payload(chat_request, run)
    attempted["executive_answer"].update({
        "status": "invented-status",
        "confidence": "absolute",
        "evidence_ids": ["EV-INVENTED-999"],
    })
    attempted["insights"][0]["evidence_ids"] = ["EV-INVENTED-999"]
    attempted["insights"][0]["chart_ids"] = ["chart-invented"]
    attempted["charts"][0]["evidence_ids"] = ["EV-INVENTED-999"]
    client = FakeClient(report_response(attempted))

    report = synthesize_executive_report(
        chat_request, run, client=client, settings=settings(GEMINI_TIMEOUT_SECONDS=8),
    )

    assert report.executive_answer.status.value == "conclusive"
    assert report.executive_answer.confidence.value == "moderate"
    assert report.executive_answer.evidence_ids == [EVIDENCE_ID]
    assert report.insights[0].evidence_ids == [EVIDENCE_ID]
    assert report.insights[0].chart_ids == []
    assert report.charts == []
    assert len(client.calls) == 1


def test_missing_optional_insights_gets_traceable_backend_fallback():
    chat_request = request()
    run = orchestration(chat_request)
    attempted = valid_payload(chat_request, run)
    attempted["insights"] = []
    attempted["charts"] = []
    client = FakeClient(report_response(attempted))

    report = synthesize_executive_report(
        chat_request, run, client=client, settings=settings(GEMINI_TIMEOUT_SECONDS=8),
    )

    assert len(report.insights) == 1
    assert report.insights[0].evidence_ids == [EVIDENCE_ID]
    assert report.insights[0].claim == report.executive_answer.headline


def test_provider_analytical_next_step_is_ignored_not_published():
    chat_request = request()
    run = orchestration(chat_request)
    invalid = valid_payload(chat_request, run)
    invalid["field_recommendations"] = ["Executar um teste de correlação como próximo passo."]
    client = FakeClient(report_response(invalid))
    report = synthesize_executive_report(
        chat_request, run, client=client, settings=settings(GEMINI_TIMEOUT_SECONDS=8),
    )
    assert report.field_recommendations == []
    assert len(client.calls) == 1


def test_provider_failure_blocks_delivery_without_local_report():
    chat_request = request()
    run = orchestration(chat_request)
    client = FakeClient(gemini_client.GeminiError("unavailable"))
    with pytest.raises(ExecutiveReportError) as caught:
        synthesize_executive_report(
            chat_request, run, client=client, settings=settings(GEMINI_TIMEOUT_SECONDS=8),
        )
    assert caught.value.code == "unavailable"
    assert len(client.calls) == 1


def test_report_context_contains_only_validated_evidence_and_deterministic_blocks():
    chat_request = request()
    run = orchestration(chat_request)
    context = build_executive_context(chat_request, run)
    assert set(context) == {
        "question", "scope", "answer_contract", "evidence", "unanswered_parts",
        "required_limitations", "technical_appendix", "allowed_charts",
    }
    assert "answer" not in context["answer_contract"]
    assert context["answer_contract"]["question_parts"] == [{
        "hypothesis_id": "ndvi_behavior",
        "question": "Os talhões apresentam comportamento de vigor diferente?",
        "status": "executed",
        "evidence_ids": [EVIDENCE_ID],
        "gaps": [],
    }]
    serialized = json.dumps(context)
    assert "GEMINI_API_KEY" not in serialized
    assert "system_prompt" not in serialized


@pytest.mark.parametrize(("code", "status"), [
    ("authentication_error", 401), ("permission_denied", 403), ("rate_limit", 429),
    ("timeout", 504), ("unavailable", 503), ("invalid_executive_report", 502),
])
def test_chat_api_maps_report_failures_without_exposing_issues(monkeypatch, code, status):
    monkeypatch.setattr(
        chat_api, "run_investigative_chat",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            ExecutiveReportError(code, "Falha segura do relatório.")
        ),
    )
    with pytest.raises(HTTPException) as caught:
        chat_api.investigate_chat(request())
    assert caught.value.status_code == status
    assert caught.value.detail == {
        "code": code,
        "message": "Falha segura do relatório.",
        "retryable": True,
    }
