"""Run the presentation acceptance scenarios against the active configuration.

This script never prints or stores credentials, prompts, raw provider responses or
CSV rows.  Successful investigative reports are frozen as self-contained HTML.
"""

from __future__ import annotations

from json import dumps
from pathlib import Path
import sys
from time import perf_counter

from app.api.datasets import _process_package
from app.data.loader import EXPECTED_FILE_NAMES
from app.data.session_store import dataset_store
from app.harness.chat_contracts import ChatRequestV2
from app.harness.chat_orchestrator import conversation_memory
from app.harness.chat_responses import run_analytical_chat
from app.harness.executive_report import ExecutiveReportError
from app.reports.chat_report import render_chat_report


ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "backend" / "tests" / "fixtures" / "manual"
OUTPUT = ROOT / "backend" / ".local" / "phase7-validation.json"
RESERVES = ROOT / "demo-data" / "relatorios-reserva"


SCENARIOS = [
    {
        "id": "data_catalog",
        "message": "Quais tipos de dados estão disponíveis neste pacote?",
        "mode": "auto",
    },
    {
        "id": "capability_catalog",
        "message": "O que a ferramenta consegue analisar com estes dados?",
        "mode": "auto",
    },
    {
        "id": "descriptive_ndvi",
        "message": "Descreva as informações de vigor disponíveis para o talhão Grão 4.0.",
        "mode": "descriptive",
        "target": "103144",
    },
    {
        "id": "single_field_temporal",
        "message": (
            "Na série temporal de NDVI do talhão Grão 4.0, houve mudanças bruscas "
            "ou divergências relevantes durante a safra?"
        ),
        "mode": "investigative",
        "target": "103144",
    },
    {
        "id": "comparison_divergences",
        "message": "Quais são as principais divergências entre os talhões analisados?",
        "mode": "auto",
        "target": "103144",
        "reference": "103145",
    },
    {
        "id": "soil_operations_vigor",
        "message": (
            "O que as análises de solo indicam sobre o contexto da área e quais sinais "
            "aparecem na execução de correção e no vigor dos talhões Grão 4.0 e Grão Convencional?"
        ),
        "mode": "investigative",
        "target": "103144",
        "reference": "103145",
    },
]


def _load_dataset():
    package = {name: (FIXTURES / name).read_bytes() for name in EXPECTED_FILE_NAMES}
    uploaded = _process_package(package)
    if uploaded.dataset_id is None:
        raise RuntimeError("O pacote sintético aprovado não foi aceito.")
    return uploaded


def _safe_error(error: Exception) -> dict:
    if isinstance(error, ExecutiveReportError):
        return {
            "code": error.code,
            "message": str(error),
            "issues": [
                {"code": item.code, "location": item.location, "message": item.message}
                for item in error.issues[:20]
            ],
        }
    return {"code": type(error).__name__, "message": "Falha controlada durante a validação."}


def main() -> int:
    dataset_store.clear()
    conversation_memory.clear()
    uploaded = _load_dataset()
    RESERVES.mkdir(parents=True, exist_ok=True)
    results = []
    prior_turn_id = None
    selected = set(sys.argv[1:])
    scenarios = [item for item in SCENARIOS if not selected or item["id"] in selected]
    for scenario in scenarios:
        started = perf_counter()
        try:
            envelope = run_analytical_chat(ChatRequestV2(
                dataset_id=uploaded.dataset_id,
                message=scenario["message"],
                requested_mode=scenario["mode"],
                target_field_id=scenario.get("target"),
                reference_field_id=scenario.get("reference"),
            ))
            elapsed = round(perf_counter() - started, 3)
            response = envelope.response
            item = {
                "id": scenario["id"], "ok": True, "seconds": elapsed,
                "kind": response.kind.value, "status": response.status.value,
            }
            if response.kind.value == "investigation_report":
                report = response.report
                serialized = dumps(report.model_dump(mode="json"), ensure_ascii=False).casefold()
                item.update({
                    "conclusion": report.executive_answer.status.value,
                    "confidence": report.executive_answer.confidence.value,
                    "insights": len(report.insights),
                    "unanswered_parts": len(report.unanswered_parts),
                    "has_direct_answer": bool(report.executive_answer.answer.strip()),
                    "has_forbidden_next_steps": "próximos passos" in serialized or "proximos passos" in serialized,
                })
                html = render_chat_report(envelope)
                if "<script" in html.casefold() or "api_key" in html.casefold():
                    raise RuntimeError("O relatório de reserva não passou pela verificação de privacidade.")
                (RESERVES / f"phase7-{scenario['id']}.html").write_text(html, encoding="utf-8")
            prior_turn_id = envelope.turn_id
        except Exception as error:  # safe summary only; raw provider data is never persisted.
            elapsed = round(perf_counter() - started, 3)
            item = {"id": scenario["id"], "ok": False, "seconds": elapsed, "error": _safe_error(error)}
        results.append(item)
        print(dumps(item, ensure_ascii=False), flush=True)
    summary = {
        "dataset_status": uploaded.status.value,
        "quality_score": uploaded.quality_score,
        "scenario_count": len(results),
        "passed": sum(item["ok"] for item in results),
        "within_90_seconds": all(item["seconds"] <= 90 for item in results),
        "results": results,
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return 0 if summary["passed"] == len(results) and summary["within_90_seconds"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
