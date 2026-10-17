"""Opt-in W3.15 live check. Never called by the ordinary pytest suite.

Run from backend: python -m app.harness.smoke --check-only
Then, with a local key: python -m app.harness.smoke
Only normalized evidence is sent by the existing harness, never raw CSVs.
"""

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path

from app.api.datasets import _process_package
from app.config import Settings
from app.data.loader import EXPECTED_FILE_NAMES, CsvInput, validate_package_files
from app.harness.orchestrator import run_investigation
from app.harness.report_validation import validate_report_evidence
from app.harness.language_validation import validate_report_language
from app.harness.schemas import InvestigationRequest, InvestigationResponse


BACKEND = Path(__file__).resolve().parents[2]
FIXTURES = BACKEND / "tests" / "fixtures" / "manual"
OUTPUT = BACKEND / ".local" / "w3-15"
QUESTION = (
    "Compare o NDVI e a condição inicial dos talhões. Resuma também o solo no escopo do dataset, "
    "sem atribuí-lo aos talhões. Considere população e calagem quando disponíveis e explicite as limitações."
)


def load_package(directory: Path, max_upload_mb: int) -> dict[str, bytes]:
    """Require one of each expected file and enforce the normal upload limit."""
    if not directory.is_dir():
        raise ValueError("invalid_data_directory")
    inputs = []
    remaining = max_upload_mb * 1024 * 1024
    for name in EXPECTED_FILE_NAMES:
        matches = [path for path in directory.rglob(name) if path.is_file()]
        if len(matches) != 1:
            raise ValueError("missing_or_duplicate_file")
        with matches[0].open("rb") as source:
            content = source.read(remaining + 1)
        if len(content) > remaining:
            raise ValueError("package_too_large")
        remaining -= len(content)
        inputs.append(CsvInput(name=name, content=content))
    return validate_package_files(inputs, max_upload_mb)


def inspect_result(result: InvestigationResponse) -> dict:
    result = InvestigationResponse.model_validate(result.model_dump())
    validate_report_evidence(result.report, result.evidence, result.warnings)
    validate_report_language(result.report)
    names = {item.tool.value for item in result.trace.calls if item.status == "success"}
    required = {"validate_comparison", "compare_ndvi", "summarize_soil_analysis"}
    trace_ids = {identifier for item in result.trace.calls for identifier in item.result_evidence_ids}
    facts_match_trace = trace_ids == {item.evidence_id for item in result.evidence}
    passed = (result.generated_by == "gemini" and required <= names and facts_match_trace
              and 1 <= len(result.trace.calls) <= 8 and all(item.status == "success" for item in result.trace.calls))
    return {
        "passed": passed, "generated_by": result.generated_by.value,
        "model": result.trace.model, "investigation_id": str(result.investigation_id),
        "tools": [{"name": item.tool.value, "status": item.status.value} for item in result.trace.calls],
        "missing_required_tools": sorted(required - names), "facts_match_trace": facts_match_trace,
        "repair_status": result.trace.repair.status if result.trace.repair else None,
        "warning_codes": sorted({item.code for item in result.warnings}),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Teste real controlado do Gemini (uma investigação).")
    parser.add_argument("--check-only", action="store_true", help="Valida configuração/pacote sem chamar o provedor.")
    parser.add_argument("--data-dir", type=Path, default=FIXTURES,
                        help="Pasta dos sete CSVs; padrão: fixtures pequenas do projeto.")
    parser.add_argument("--target", default="103144")
    parser.add_argument("--reference", default="103145")
    args = parser.parse_args(argv)
    try:
        settings = Settings()
        package = load_package(args.data_dir, settings.max_upload_mb)
        uploaded = _process_package(package)
        if uploaded.dataset_id is None or uploaded.errors:
            print(json.dumps({"passed": False, "error_code": "invalid_package",
                              "issue_codes": sorted({item.code for item in uploaded.errors})}))
            return 2
        request = InvestigationRequest(
            dataset_id=uploaded.dataset_id, target_field_id=args.target, reference_field_id=args.reference,
            period="full_season", question=QUESTION,
        )
        permitted = any(pair.target_field_id == args.target and pair.reference_field_id == args.reference
                        for pair in uploaded.valid_pairs)
        if not permitted:
            print(json.dumps({"passed": False, "error_code": "invalid_pair"}))
            return 2
        if args.check_only:
            print(json.dumps({"check_only": True, "package_valid": True,
                              "gemini_configured": settings.gemini_configured, "model": settings.gemini_model,
                              "input_kind": "fixtures" if args.data_dir.resolve() == FIXTURES else "local_package",
                              "file_count": len(package)}, ensure_ascii=False))
            return 0
        if not settings.gemini_configured:
            print(json.dumps({"passed": False, "error_code": "missing_api_key"}))
            return 2
        result = run_investigation(request, settings=settings)
        summary = inspect_result(result)
        OUTPUT.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        report_path = OUTPUT / f"{stamp}-{result.investigation_id}.json"
        report_path.write_text(result.model_dump_json(indent=2), encoding="utf-8")
        summary["report_path"] = str(report_path)
        print(json.dumps(summary, ensure_ascii=False))
        return 0 if summary["passed"] else 1
    except Exception:
        # No raw exception/provider bodies, paths from exceptions or credentials.
        print(json.dumps({"passed": False, "error_code": "controlled_test_failed"}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
