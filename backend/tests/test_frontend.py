"""Single-origin build, SPA fallback and API isolation; no provider requests."""
from html.parser import HTMLParser
from unittest.mock import Mock

from fastapi.testclient import TestClient
import pytest

from app.api import datasets, diagnostics, health, investigations
from app.frontend import FRONTEND_DIST
from app.harness import gemini_client, registry
from app.main import create_app
from app.data.session_store import SessionStore
from app.reports.store import ReportStore
from tests.test_api import multipart
from tests.test_gemini_client import settings


@pytest.fixture
def build(tmp_path):
    dist = tmp_path / "dist"
    (dist / "assets").mkdir(parents=True)
    (dist / "index.html").write_text('<!doctype html><html><div id="app">TEST_BUILD</div></html>', encoding="utf-8")
    (dist / "assets" / "app-123.js").write_text('console.log("BUILD_ASSET")', encoding="utf-8")
    (dist / "assets" / "app-123.css").write_text('body { color: brown }', encoding="utf-8")
    (dist / ".env").write_text("PRIVATE_TEST_SENTINEL", encoding="utf-8")
    (tmp_path / "outside.txt").write_text("PRIVATE_TEST_SENTINEL", encoding="utf-8")
    return dist


@pytest.fixture
def client(build, monkeypatch):
    monkeypatch.setattr(health, "get_settings", lambda: settings(GEMINI_API_KEY=None))
    with TestClient(create_app(frontend_dist=build)) as client:
        yield client


@pytest.mark.parametrize("path", ["/", "/index.html", "/investigation", "/comparison/nested/"])
def test_html_entry_and_navigation_fallback(client, path):
    response = client.get(path)
    assert response.status_code == 200 and "TEST_BUILD" in response.text
    assert response.headers["content-type"].startswith("text/html")
    assert response.headers["cache-control"] == "no-cache"
    assert response.headers["x-content-type-options"] == "nosniff"
    head = client.head(path)
    assert head.status_code == 200 and head.content == b""
    assert head.headers["content-length"] == response.headers["content-length"]


@pytest.mark.parametrize(("name", "mime"), [("app-123.js", "javascript"), ("app-123.css", "text/css")])
def test_build_assets_and_conditional_requests(client, name, mime):
    response = client.get(f"/assets/{name}")
    assert response.status_code == 200 and mime in response.headers["content-type"]
    assert "TEST_BUILD" not in response.text
    assert client.get(f"/assets/{name}", headers={"If-None-Match": response.headers["etag"]}).status_code == 304


@pytest.mark.parametrize("path", ["/assets/missing.js", "/assets/missing", "/missing.css", "/api", "/api/missing", "/docs/missing"])
def test_missing_files_and_api_paths_never_fall_back_to_html(client, path):
    response = client.get(path)
    assert response.status_code == 404 and "TEST_BUILD" not in response.text


def test_api_docs_and_methods_keep_their_original_responses(client):
    assert client.get("/api/health").json()["status"] == "ok"
    assert "/api/investigations" in client.get("/openapi.json").json()["paths"]
    assert client.get("/docs").status_code == 200
    assert client.get("/redoc").status_code == 200
    assert client.post("/api/health").status_code == 405
    assert client.get("/api/investigations").status_code == 405
    assert client.post("/comparison").status_code == 405
    assert client.post("/api/missing").status_code == 404


@pytest.mark.parametrize("path", ["/.env", "/%2eenv", "/assets/../.env", "/%2e%2e/outside.txt", "/assets/%2e%2e/%2e%2e/outside.txt", "/assets%5c..%5c.env", "/C:/outside.txt"])
def test_hidden_and_escaping_paths_are_not_served(client, path):
    response = client.get(path)
    assert response.status_code == 404 and "PRIVATE_TEST_SENTINEL" not in response.text


def test_api_starts_without_build_and_later_build_becomes_available(tmp_path, monkeypatch):
    monkeypatch.setattr(health, "get_settings", lambda: settings(GEMINI_API_KEY=None))
    dist = tmp_path / "not-built-yet"
    with TestClient(create_app(frontend_dist=dist)) as client:
        assert client.get("/api/health").status_code == 200
        response = client.get("/")
        assert response.status_code == 503 and "pnpm build" in response.text
        assert str(tmp_path) not in response.text
        assert client.get("/api/missing").status_code == 404
        assert client.get("/assets/missing.js").status_code == 404
        dist.mkdir()
        (dist / "index.html").write_text("BUILD_READY", encoding="utf-8")
        assert client.get("/").text == "BUILD_READY"


class BuildResources(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.paths = []
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "script" and "src" in attrs:
            self.paths.append(attrs["src"])
        if tag == "link" and attrs.get("rel") == "stylesheet":
            self.paths.append(attrs["href"])


def test_actual_build_and_complete_local_flow_share_one_origin(presentation_package, monkeypatch):
    if not (FRONTEND_DIST / "index.html").is_file():
        pytest.skip("Execute pnpm build em frontend para validar a entrega compilada.")
    local = settings(GEMINI_API_KEY=None, APP_ENV="development")
    for module in (datasets, diagnostics, health, investigations):
        monkeypatch.setattr(module, "get_settings", lambda: local)
    store = SessionStore()
    for module in (datasets, investigations):
        monkeypatch.setattr(module, "dataset_store", store)
    monkeypatch.setattr(diagnostics, "execute_tool", lambda tool, args: registry.execute_tool(tool, args, store=store))
    monkeypatch.setattr(investigations, "report_store", ReportStore())
    provider = Mock(side_effect=AssertionError("No real Gemini call"))
    monkeypatch.setattr(gemini_client, "GeminiClient", provider)
    # Changing cwd must not affect where FastAPI finds the compiled output.
    monkeypatch.chdir(FRONTEND_DIST)
    with TestClient(create_app(), base_url="http://localhost:8000") as client:
        index = client.get("/")
        assert index.status_code == 200 and 'id="app"' in index.text
        paths = BuildResources(index.text).paths
        assert len(paths) >= 2 and all(path.startswith("/assets/") for path in paths)
        for path in paths:
            asset = client.get(path)
            assert asset.status_code == 200 and asset.content
            assert "text/html" not in asset.headers["content-type"]
        assert client.get("/api/health").json()["status"] == "ok"
        upload = client.post("/api/datasets", files=multipart(presentation_package))
        assert upload.status_code == 201
        args = dict(dataset_id=upload.json()["dataset_id"], target_field_id="103144", reference_field_id="103145", period="full_season")
        comparison = client.post("/api/diagnostics/tools", json={"tool": "validate_comparison", "arguments": args})
        assert comparison.status_code == 200 and comparison.json()["allowed"] is True
        result = client.post("/api/investigations", json={**args, "question": "Como os talhões se comparam?"})
        assert result.status_code == 200 and result.json()["status"] == "completed"
        assert result.json()["generated_by"] == "deterministic_fallback"
        report = client.get(f'/api/investigations/{result.json()["investigation_id"]}/report')
        assert report.status_code == 200 and "attachment" in report.headers["content-disposition"]
        assert provider.call_count == 0
