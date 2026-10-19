"""W4.12: real HTTP routes/SDK with injected transport failures, never live Gemini."""

import json
from unittest.mock import Mock

from fastapi.testclient import TestClient
from google import genai
import httpx
import pytest

from app.api import datasets, diagnostics, gemini, health, investigations
from app.data.session_store import SessionStore
from app.harness import orchestrator, registry
from app.harness.schemas import InvestigationResponse
from app.main import create_app
from app.reports.store import ReportStore
from tests.test_api import multipart
from tests.test_gemini_client import settings, TrackedTransport


@pytest.mark.parametrize("scenario,expected_calls,reason", [
    ("missing_key", 0, "Chave do provedor não configurada."),
    ("timeout_planning", 1, "Prazo da geração automática excedido."),
    ("timeout_synthesis", 3, "Prazo da geração automática excedido."),
    ("rate_limit_planning", 2, "Limite de requisições do provedor atingido."),
    ("rate_limit_synthesis", 4, "Limite de requisições do provedor atingido."),
    ("invalid_json", 4, "O relatório gerado não passou pela validação de formato."),
    ("invalid_schema", 4, "O relatório gerado não passou pela validação de formato."),
    ("empty_response", 1, "O provedor não retornou uma resposta utilizável."),
])
def test_failure_preserves_session_fallback_and_download(
    presentation_package, monkeypatch, scenario, expected_calls, reason,
):
    local = settings(APP_ENV="development", GEMINI_API_KEY=None if scenario == "missing_key" else "artificial-test-key")
    for module in (datasets, diagnostics, gemini, health, investigations):
        monkeypatch.setattr(module, "get_settings", lambda: local)
    store = SessionStore()
    for module in (datasets, investigations):
        monkeypatch.setattr(module, "dataset_store", store)
    monkeypatch.setattr(diagnostics, "execute_tool", lambda name, args: registry.execute_tool(name, args, store=store))
    monkeypatch.setattr(investigations, "report_store", ReportStore())
    pause = Mock()
    monkeypatch.setattr(orchestrator, "sleep", pause)
    sdk_constructor = genai.Client
    transports, requests = [], []
    phase = "probe"
    arguments = {}

    def text_response(text):
        return httpx.Response(200, json={"candidates": [{"finishReason": "STOP", "content": {
            "role": "model", "parts": [{"text": text}],
        }}]})

    def respond(request):
        requests.append(request)
        if phase == "investigation" and (scenario.endswith("synthesis") or scenario in ("invalid_json", "invalid_schema")):
            if len(requests) == 1:
                return httpx.Response(200, json={"candidates": [{"finishReason": "STOP", "content": {
                    "role": "model", "parts": [{"functionCall": {"name": "compare_ndvi", "args": arguments}}],
                }}]})
            if len(requests) == 2:
                return text_response("Análise finalizada.")
        if scenario.startswith("timeout"):
            raise httpx.ReadTimeout("PRIVATE_PROVIDER_TIMEOUT", request=request)
        if scenario.startswith("rate_limit"):
            return httpx.Response(429, json={"error": {"code": 429, "status": "RESOURCE_EXHAUSTED",
                                                       "message": "PRIVATE_PROVIDER_QUOTA"}})
        if scenario == "invalid_json" and phase == "investigation":
            return text_response("PRIVATE_INVALID_JSON")
        if scenario == "invalid_schema" and phase == "investigation":
            return text_response(json.dumps({"overview": {"headline": "PRIVATE_INVALID_SCHEMA"}}))
        return httpx.Response(200, json={"candidates": []})

    def sdk_factory(**kwargs):
        # Keep the production wrapper and official SDK; replace only outgoing I/O.
        transport = TrackedTransport(respond)
        transports.append(transport)
        kwargs["http_options"] = kwargs["http_options"].model_copy(update={"client_args": {"transport": transport}})
        return sdk_constructor(**kwargs)

    monkeypatch.setattr(genai, "Client", sdk_factory)
    with TestClient(create_app()) as api:
        assert api.get("/api/health").json()["gemini_configured"] == (scenario != "missing_key")
        assert not requests and not transports  # Health never contacts the provider.
        probe = api.post("/api/gemini/test")
        code = "missing_api_key" if scenario == "missing_key" else (
            "timeout" if scenario.startswith("timeout") else "rate_limit" if scenario.startswith("rate_limit") else "invalid_response"
        )
        assert probe.status_code == {"missing_api_key": 503, "timeout": 504, "rate_limit": 429, "invalid_response": 502}[code]
        assert probe.json()["error_code"] == code and probe.json()["success"] is False
        assert probe.json()["latency_ms"] >= 0 and "PRIVATE" not in probe.text
        assert len(requests) == (0 if scenario == "missing_key" else 1)
        assert all(transport.is_closed for transport in transports)
        requests.clear()
        phase = "investigation"

        uploaded = api.post("/api/datasets", files=multipart(presentation_package))
        assert uploaded.status_code == 201
        arguments.update(dataset_id=uploaded.json()["dataset_id"], target_field_id="103144",
                         reference_field_id="103145", period="full_season")
        comparison = {"tool": "validate_comparison", "arguments": arguments}
        assert api.post("/api/diagnostics/tools", json=comparison).json()["allowed"] is True
        body = {**arguments, "question": "Como os talhões se comparam?"}
        response = api.post("/api/investigations", json=body)
        assert response.status_code == 200
        result = InvestigationResponse.model_validate(response.json())
        assert result.status == "completed" and result.generated_by == "deterministic_fallback"
        notices = [item.message for item in result.warnings if item.code == "deterministic_fallback"]
        assert notices == [reason + " Relatório produzido por templates locais."]
        assert result.report.limitations and result.report.findings
        assert str(result.trace.dataset_id) == arguments["dataset_id"]
        ids = {item.evidence_id for item in result.evidence}
        assert all(set(item.evidence_ids) <= ids for item in [*result.report.findings, *result.report.recommendations])
        assert len(requests) == expected_calls
        assert pause.call_count == (1 if scenario.startswith("rate_limit") else 0)
        assert all(transport.is_closed for transport in transports)
        if scenario in ("invalid_json", "invalid_schema"):
            assert result.trace.repair.attempt == 1 and result.trace.repair.status == "error"
        else:
            assert result.trace.repair is None
        # Failures during synthesis preserve the NDVI already calculated, without rerunning it.
        if scenario.endswith("synthesis") or scenario in ("invalid_json", "invalid_schema"):
            assert [call.tool for call in result.trace.calls] == ["validate_comparison", "compare_ndvi"]
            assert result.chart_data.ndvi == result.evidence[1]

        document = api.get(f"/api/investigations/{result.investigation_id}/report")
        assert document.status_code == 200 and "attachment" in document.headers["content-disposition"]
        assert reason in document.text and "Fallback determinístico" in document.text
        for output in (response.text, document.text):
            assert "PRIVATE" not in output and "artificial-test-key" not in output
            assert "traceback" not in output.lower()
        assert len(requests) == expected_calls  # Download cannot retry the failed provider.

        # The same running app and dataset remain usable after every failure.
        local = settings(APP_ENV="development", GEMINI_API_KEY=None)
        assert api.get("/api/health").json()["status"] == "ok"
        assert api.post("/api/diagnostics/tools", json=comparison).json()["allowed"] is True
        again = api.post("/api/investigations", json=body)
        assert again.status_code == 200 and again.json()["status"] == "completed"
        assert again.json()["investigation_id"] != str(result.investigation_id)
        assert again.json()["trace"]["dataset_id"] == arguments["dataset_id"]
        assert len(requests) == expected_calls
        assert api.get(f'/api/investigations/{again.json()["investigation_id"]}/report').status_code == 200
        if scenario == "missing_key":
            assert not transports
