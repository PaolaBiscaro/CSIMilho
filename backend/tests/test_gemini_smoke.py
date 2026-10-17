"""W3.15 command checks: real CSV/tools/harness, simulated provider only."""

import json
from pathlib import Path
import shutil
from unittest.mock import Mock

from google.genai import types
import pytest

from app.config import Settings
from app.harness import gemini_client, smoke
from app.harness.orchestrator import run_investigation
from app.harness.schemas import InvestigationRequest, InvestigationResponse
from tests.test_orchestrator import call, done, response


class SmokeClient:
    model = "simulated-model"

    def __init__(self, include_soil=True):
        self.include_soil = include_soil
        self.calls = 0

    def generate_content(self, contents, *, config, timeout_seconds=None):
        self.calls += 1
        context = json.loads(contents[0].parts[0].text)
        if config.response_mime_type == "application/json":
            return response(types.Part(text=json.dumps({
                "overview": {"headline": "Comparação observacional", "summary": "Os dados têm limitações.",
                             "evidence_strength": "weak"},
                "findings": [{"title": "Contexto disponível", "explanation": "Os dados têm limitações.",
                              "evidence_ids": [item["evidence_id"] for item in context["evidence"]]}],
                "limitations": context["required_limitations"], "recommendations": [],
            })))
        if self.calls == 1:
            args = {"dataset_id": context["dataset_id"], "target_field_id": context["target"]["field_id"],
                    "reference_field_id": context["reference"]["field_id"], "period": context["period"]}
            calls = [call("compare_ndvi", args)]
            if self.include_soil:
                calls.append(call("summarize_soil_analysis", {"dataset_id": context["dataset_id"]}))
            return response(*calls)
        return done()


@pytest.fixture(autouse=True)
def isolated_environment(monkeypatch, tmp_path):
    # Do not read a developer's .env or contact the provider, even if configured.
    monkeypatch.setattr(smoke, "Settings", lambda: Settings(_env_file=None, GEMINI_API_KEY=None))
    monkeypatch.setattr(smoke, "OUTPUT", tmp_path / "reports")
    monkeypatch.setattr(gemini_client, "GeminiClient", Mock(side_effect=AssertionError("Unexpected real client")))


def local_result(*, client=None):
    uploaded = smoke._process_package(smoke.load_package(smoke.FIXTURES, 100))
    request = InvestigationRequest(dataset_id=uploaded.dataset_id, target_field_id="103144",
                                   reference_field_id="103145", period="full_season", question=smoke.QUESTION)
    return run_investigation(request, client=client, settings=Settings(_env_file=None, GEMINI_API_KEY=None))


def enable_fake_key(monkeypatch):
    monkeypatch.setattr(smoke, "Settings", lambda: Settings(_env_file=None, GEMINI_API_KEY="test-secret-never-print"))


def test_check_only_uses_fixtures_even_when_private_package_env_is_set(monkeypatch, capsys):
    enable_fake_key(monkeypatch)
    monkeypatch.setenv("FARMLAB_REAL_DATA_DIR", "not-the-selected-package")
    runner = Mock(side_effect=AssertionError("check-only must not run investigation"))
    monkeypatch.setattr(smoke, "run_investigation", runner)
    assert smoke.main(["--check-only"]) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["package_valid"] and result["gemini_configured"]
    assert result["input_kind"] == "fixtures" and result["file_count"] == 7
    assert "passed" not in result and "test-secret" not in str(result)
    runner.assert_not_called()
    assert not smoke.OUTPUT.exists()


def test_missing_key_never_runs_or_creates_report(monkeypatch, capsys):
    runner = Mock()
    monkeypatch.setattr(smoke, "run_investigation", runner)
    assert smoke.main([]) == 2
    assert json.loads(capsys.readouterr().out)["error_code"] == "missing_api_key"
    runner.assert_not_called()
    assert not smoke.OUTPUT.exists()


def test_command_with_simulated_provider_validates_and_saves_complete_report(monkeypatch, capsys):
    enable_fake_key(monkeypatch)
    client = SmokeClient()
    monkeypatch.setattr(smoke, "run_investigation", lambda request, settings:
                        run_investigation(request, settings=settings, client=client))
    assert smoke.main([]) == 0
    summary = json.loads(capsys.readouterr().out)
    assert summary["passed"] and summary["generated_by"] == "gemini"
    assert summary["facts_match_trace"] and summary["missing_required_tools"] == []
    artifact = Path(summary["report_path"])
    assert artifact.parent == smoke.OUTPUT and len(list(smoke.OUTPUT.iterdir())) == 1
    report = InvestigationResponse.model_validate_json(artifact.read_text(encoding="utf-8"))
    assert len(report.evidence) == len(report.trace.calls) == 3 and client.calls == 3
    assert "test-secret" not in artifact.read_text(encoding="utf-8")


def test_fallback_is_saved_but_never_passes_live_gate(monkeypatch, capsys):
    enable_fake_key(monkeypatch)
    result = local_result()
    monkeypatch.setattr(smoke, "run_investigation", lambda *args, **kwargs: result)
    assert smoke.main([]) == 1
    summary = json.loads(capsys.readouterr().out)
    assert not summary["passed"] and summary["generated_by"] == "deterministic_fallback"
    assert Path(summary["report_path"]).is_file()


def test_successful_report_without_soil_does_not_pass_scenario():
    summary = smoke.inspect_result(local_result(client=SmokeClient(include_soil=False)))
    assert not summary["passed"] and summary["missing_required_tools"] == ["summarize_soil_analysis"]


def test_evidence_missing_from_trace_fails_gate():
    result = local_result(client=SmokeClient())
    result.trace.calls[-1].result_evidence_ids = ["EV-SOIL-999"]
    summary = smoke.inspect_result(result)
    assert not summary["passed"] and not summary["facts_match_trace"]


def test_unsupported_report_numbers_are_rejected_before_artifact(monkeypatch, capsys):
    enable_fake_key(monkeypatch)
    result = local_result(client=SmokeClient())
    result.report.findings[0].explanation = "NDVI médio do alvo: 999,876."
    monkeypatch.setattr(smoke, "run_investigation", lambda *args, **kwargs: result)
    assert smoke.main([]) == 2
    assert not json.loads(capsys.readouterr().out)["passed"]
    assert not smoke.OUTPUT.exists()


def test_unexpected_errors_do_not_print_credentials_or_provider_details(monkeypatch, capsys):
    enable_fake_key(monkeypatch)
    monkeypatch.setattr(smoke, "run_investigation", Mock(side_effect=RuntimeError("test-secret-never-print")))
    assert smoke.main([]) == 2
    assert json.loads(capsys.readouterr().out) == {"passed": False, "error_code": "controlled_test_failed"}


@pytest.mark.parametrize("args", [["--target", "unknown"], ["--target", "103145", "--reference", "103145"]])
def test_invalid_pair_is_rejected_before_provider(args, monkeypatch, capsys):
    runner = Mock()
    monkeypatch.setattr(smoke, "run_investigation", runner)
    assert smoke.main(args) == 2
    assert json.loads(capsys.readouterr().out)["error_code"] == "invalid_pair"
    runner.assert_not_called()


@pytest.mark.parametrize("problem", ["missing", "duplicate", "oversize"])
def test_loader_rejects_missing_duplicate_or_oversized_package(problem, tmp_path):
    package = tmp_path / "input"
    shutil.copytree(smoke.FIXTURES, package)
    first = next(package.rglob("fields.csv"))
    if problem == "missing":
        first.unlink()
    elif problem == "duplicate":
        (package / "duplicate").mkdir()
        shutil.copyfile(first, package / "duplicate" / "fields.csv")
    with pytest.raises(ValueError, match="package_too_large" if problem == "oversize" else "missing_or_duplicate_file"):
        smoke.load_package(package, 0 if problem == "oversize" else 100)


def test_invalid_csv_package_is_reported_without_investigation(tmp_path, capsys):
    package = tmp_path / "input"
    shutil.copytree(smoke.FIXTURES, package)
    next(package.rglob("fields.csv")).write_text("unrelated\nvalue\n", encoding="utf-8")
    assert smoke.main(["--data-dir", str(package)]) == 2
    summary = json.loads(capsys.readouterr().out)
    assert not summary["passed"] and summary["error_code"] == "invalid_package" and summary["issue_codes"]
