"""Presentation failures preserve the uploaded dataset and never publish a report."""

from unittest.mock import Mock

from fastapi import HTTPException
import pytest

from app.api import investigations
from app.harness.orchestrator import InvestigationError
from app.reports.store import ReportStore
from tests.test_analytics import analytical_dataset
from tests.test_call_validators import context


@pytest.mark.parametrize(("code", "status"), [
    ("missing_api_key", 503),
    ("authentication_error", 401),
    ("permission_denied", 403),
    ("rate_limit", 429),
    ("timeout", 504),
    ("unavailable", 503),
    ("invalid_report", 502),
])
def test_failure_preserves_session_and_blocks_download(context, monkeypatch, code, status):
    request, store = context
    reports = ReportStore()
    monkeypatch.setattr(investigations, "dataset_store", store)
    monkeypatch.setattr(investigations, "report_store", reports)
    failure = InvestigationError(
        code,
        "Não foi possível gerar o relatório. O dataset foi preservado para uma nova tentativa.",
        status,
    )
    execute = Mock(side_effect=failure)
    monkeypatch.setattr(investigations, "run_investigation", execute)

    with pytest.raises(HTTPException) as caught:
        investigations.investigate(request)

    assert caught.value.status_code == status
    assert caught.value.detail["code"] == code
    assert "preservado" in caught.value.detail["message"]
    assert store.get(request.dataset_id)
    with pytest.raises(KeyError):
        reports.get(request.dataset_id)


def test_stream_failure_contains_safe_error_and_no_result(context, monkeypatch):
    request, store = context
    monkeypatch.setattr(investigations, "dataset_store", store)
    monkeypatch.setattr(
        investigations,
        "run_investigation",
        Mock(side_effect=InvestigationError("unavailable", "Serviço indisponível; dataset preservado.", 503)),
    )
    body = "".join(investigations._investigation_stream(request))
    assert "event: error" in body
    assert '"code": "unavailable"' in body
    assert "event: result" not in body
