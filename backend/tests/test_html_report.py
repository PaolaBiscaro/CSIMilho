"""Offline HTML and download contract, using only local fixtures/no provider."""
from html.parser import HTMLParser
from unittest.mock import Mock
from uuid import uuid4

from fastapi.testclient import TestClient
import pytest

from app.api import investigations
from app.harness.orchestrator import run_investigation
from app.harness.schemas import ReportRepairTrace, ToolCallError
from app.main import create_app
from app.reports import store as store_module
from app.reports.html_report import CSP, render_html_report
from app.reports.store import ReportStore
from tests.test_analytics import analytical_dataset
from tests.test_call_validators import context
from tests.test_gemini_client import settings


class Document(HTMLParser):
    def __init__(self, html):
        super().__init__(convert_charrefs=True)
        self.tags, self.attributes, self.content = [], [], []
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        self.tags.append(tag)
        self.attributes.extend(attrs)

    def handle_data(self, data):
        self.content.append(data)


@pytest.fixture
def completed(context):
    return run_investigation(context[0], store=context[1], settings=settings(GEMINI_API_KEY=None))


@pytest.mark.parametrize("origin", ["gemini", "deterministic_fallback"])
def test_self_contained_report_has_required_sections_and_offline_tables(completed, tmp_path, origin):
    completed.generated_by = origin
    html = render_html_report(completed)
    path = tmp_path / "report.html"
    path.write_text(html, encoding="utf-8")
    document = Document(path.read_text(encoding="utf-8"))
    assert not {"script", "iframe", "object", "embed", "link", "img", "form", "base"}.intersection(document.tags)
    assert all(not name.startswith("on") for name, _ in document.attributes)
    assert all(value.startswith("#") for name, value in document.attributes if name in ("href", "src"))
    ids = {value for name, value in document.attributes if name == "id"}
    assert all(value[1:] in ids for name, value in document.attributes if name == "href")
    assert "style" in document.tags and "table" in document.tags
    assert {"overview", "evidence", "limitations", "methods"} <= ids
    assert CSP in [value for _, value in document.attributes]
    visible = " ".join(document.content)
    for word in ("Achados", "Recomendações", "Modelo configurado", "UTC", "Série NDVI pareada", "Textura normalizada", "Conjunto 2", "ndvi_metadata.csv"):
        assert word in visible
    assert str(completed.investigation_id) in visible
    assert "Fallback determinístico" in visible if origin == "deterministic_fallback" else "Origem Gemini" in visible


def test_all_external_text_is_escaped_including_attributes_and_closing_tags(completed):
    attack = '</title></style><script>alert("x")</script><img src="https://example.invalid/x" onerror="alert(2)"> & "texto"'
    completed.report.overview.headline = attack
    completed.report.overview.summary = attack
    completed.report.findings[0].title = attack
    completed.report.findings[0].explanation = attack
    completed.report.recommendations[0].action = attack
    completed.report.recommendations[0].reason = attack
    completed.report.limitations[0].title = attack
    completed.report.limitations[0].explanation = attack
    completed.report.limitations[0].rule_id = attack
    completed.evidence[0].method = attack
    completed.evidence[0].source_files = [attack]
    completed.trace.model = attack
    completed.trace.calls[0].tool_version = attack
    completed.trace.calls[0].source_files = [attack]
    completed.warnings[0].message = attack
    html = render_html_report(completed)
    document = Document(html)
    assert attack in ''.join(document.content)
    assert "<script>" not in html and "&lt;script&gt;" in html
    assert not {"script", "img"}.intersection(document.tags)
    assert all(not name.startswith("on") and name != "src" for name, _ in document.attributes)
    assert all(value.startswith("#") for name, value in document.attributes if name == "href")


def test_report_uses_explicit_projection_without_private_trace_or_repair_data(completed):
    secret = "PRIVATE_SENTINEL_NOT_FOR_REPORT"
    completed.trace = completed.trace.model_copy(update={"prompt": secret, "api_key": secret, "raw_data": secret})
    completed.trace.calls[0] = completed.trace.calls[0].model_copy(update={
        "response": secret, "error": ToolCallError(code="tool_execution_failed", message=secret), "status": "error",
        "arguments": completed.trace.calls[0].arguments.model_copy(update={"prompt": secret, "dataframe": secret}),
    })
    completed.trace.repair = ReportRepairTrace(attempt=1, started_at=completed.trace.created_at,
        duration_ms=0, status="error", trigger=ToolCallError(code="failed", message=secret),
        error=ToolCallError(code="failed", message=secret))
    html = render_html_report(completed)
    assert secret not in html
    assert "Reparo do relatório" in html and "A ferramenta não concluiu" in html


def test_zero_null_and_signed_values_are_preserved_without_recalculation(completed):
    ndvi = completed.chart_data.ndvi
    target = next(item for item in completed.evidence if item.evidence_id == ndvi.evidence_id)
    target.target_value = None
    target.reference_value = 0.0
    target.difference = -12.3456
    html = render_html_report(completed)
    assert '<td>Indisponível</td><td>0</td><td>-12,3456</td>' in html
    assert "unidade não documentada" in html


def test_store_is_immutable_bounded_and_session_only(completed):
    store = ReportStore(max_entries=2)
    first = completed.investigation_id
    store.save(completed)
    snapshot = store.get(first)
    completed.report.overview.headline = "MODIFIED_AFTER_SAVE"
    assert store.get(first) == snapshot
    second, third = uuid4(), uuid4()
    store.save(completed.model_copy(update={"investigation_id": second}))
    store.save(completed.model_copy(update={"investigation_id": third}))
    with pytest.raises(KeyError):
        store.get(first)
    assert "MODIFIED_AFTER_SAVE" in store.get(second)
    store.clear()
    with pytest.raises(KeyError):
        store.get(third)


def test_post_then_download_has_safe_headers_and_does_not_rerun_investigation(context, monkeypatch):
    monkeypatch.setattr(investigations, "dataset_store", context[1])
    monkeypatch.setattr(investigations, "get_settings", lambda: settings(GEMINI_API_KEY=None))
    monkeypatch.setattr(investigations, "report_store", ReportStore())
    with TestClient(create_app()) as client:
        response = client.post("/api/investigations", json=context[0].model_dump(mode="json"))
        assert response.status_code == 200
        identifier = response.json()["investigation_id"]
        forbidden = Mock(side_effect=AssertionError("Do not call provider or analytics again"))
        monkeypatch.setattr(investigations, "run_investigation", forbidden)
        one = client.get(f"/api/investigations/{identifier}/report")
        two = client.get(f"/api/investigations/{identifier}/report")
        assert one.status_code == 200 and one.content == two.content
        assert one.headers["content-type"] == "text/html; charset=utf-8"
        assert one.headers["content-disposition"] == f'attachment; filename="farmlab-{identifier}.html"'
        assert one.headers["cache-control"] == "no-store"
        assert one.headers["x-content-type-options"] == "nosniff"
        assert one.headers["content-security-policy"] == CSP
        assert "Relatório" in one.text and forbidden.call_count == 0


def test_unknown_and_malformed_report_ids_have_controlled_errors(monkeypatch):
    monkeypatch.setattr(investigations, "report_store", ReportStore())
    with TestClient(create_app()) as client:
        response = client.get(f"/api/investigations/{uuid4()}/report")
        assert response.status_code == 404 and response.json()["detail"]["code"] == "report_not_found"
        assert client.get("/api/investigations/not-a-uuid/report").status_code == 422


def test_failed_render_does_not_publish_a_report_or_expose_internal_error(completed, context, monkeypatch):
    store = ReportStore()
    monkeypatch.setattr(investigations, "report_store", store)
    monkeypatch.setattr(investigations, "run_investigation", lambda *args, **kwargs: completed)
    monkeypatch.setattr(store_module, "render_html_report", Mock(side_effect=RuntimeError("PRIVATE_RENDER_ERROR")))
    with TestClient(create_app()) as client:
        response = client.post("/api/investigations", json=context[0].model_dump(mode="json"))
        assert response.status_code == 503 and "PRIVATE" not in response.text
        assert client.get(f"/api/investigations/{completed.investigation_id}/report").status_code == 404
