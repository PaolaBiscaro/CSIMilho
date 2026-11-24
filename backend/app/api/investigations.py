"""Investigation API with JSON compatibility and safe live progress events."""

import json
from queue import Queue
from threading import Thread
from typing import Iterator
from uuid import UUID

from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse

from app.config import get_settings
from app.data.session_store import DatasetNotFoundError, dataset_store
from app.harness.orchestrator import InvestigationError, run_investigation
from app.harness.schemas import InvestigationRequest, InvestigationResponse
from app.harness.validators import ToolCallValidationError
from app.reports.html_report import CSP
from app.reports.store import report_store


router = APIRouter(prefix="/api/investigations", tags=["investigations"])


def _safe_error(error: Exception) -> tuple[int, dict[str, str]]:
    if isinstance(error, DatasetNotFoundError):
        return 404, {"code": "dataset_not_found", "message": "Dataset não encontrado na sessão."}
    if isinstance(error, ToolCallValidationError):
        return (404 if error.code == "dataset_not_found" else 422), {"code": error.code, "message": str(error)}
    if isinstance(error, InvestigationError):
        return error.status_code, error.error.model_dump()
    return 503, {
        "code": "investigation_failed",
        "message": "Não foi possível produzir um relatório válido com as evidências disponíveis.",
    }


def _sse(event: str, payload: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(payload, ensure_ascii=False, allow_nan=False)}\n\n"


def _investigation_stream(request: InvestigationRequest) -> Iterator[str]:
    events: Queue[tuple[str, dict] | None] = Queue()

    def publish(payload: dict[str, str]) -> None:
        events.put(("progress", payload))

    def execute() -> None:
        try:
            result = run_investigation(
                request, settings=get_settings(), store=dataset_store, progress_sink=publish,
            )
            report_store.save(result)
            events.put(("result", result.model_dump(mode="json")))
        except Exception as error:
            status, detail = _safe_error(error)
            events.put(("error", {"status": status, **detail}))
        finally:
            events.put(None)

    Thread(target=execute, name="farmlab-investigation", daemon=True).start()
    while True:
        item = events.get()
        if item is None:
            return
        yield _sse(*item)


@router.post("", response_model=InvestigationResponse, responses={
    404: {"description": "Dataset não encontrado na sessão."},
    422: {"description": "Requisição ou par inválido."},
    503: {"description": "Não foi possível produzir um relatório válido."},
})
def investigate(request: InvestigationRequest) -> InvestigationResponse:
    try:
        result = run_investigation(request, settings=get_settings(), store=dataset_store)
        report_store.save(result)
        return result
    except DatasetNotFoundError:
        raise HTTPException(status_code=404, detail={"code": "dataset_not_found", "message": "Dataset não encontrado na sessão."}) from None
    except ToolCallValidationError as error:
        raise HTTPException(status_code=404 if error.code == "dataset_not_found" else 422,
                            detail={"code": error.code, "message": str(error)}) from None
    except InvestigationError as error:
        raise HTTPException(status_code=error.status_code, detail=error.error.model_dump()) from None
    except Exception:
        # Includes invalid local templates/results; do not expose provider or
        # Pydantic inputs and never return a completed response on internal error.
        raise HTTPException(status_code=503, detail={
            "code": "investigation_failed", "message": "Não foi possível produzir um relatório válido com as evidências disponíveis.",
        }) from None


@router.post("/stream", response_class=StreamingResponse, responses={
    200: {"description": "Eventos de progresso e resultado final em Server-Sent Events."},
})
def investigate_stream(request: InvestigationRequest) -> StreamingResponse:
    return StreamingResponse(
        _investigation_stream(request), media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-store",
            "X-Accel-Buffering": "no",
            "X-Content-Type-Options": "nosniff",
        },
    )


@router.get("/{investigation_id}/report", response_class=HTMLResponse, responses={
    404: {"description": "Relatório não disponível na sessão."},
})
def download_report(investigation_id: UUID) -> HTMLResponse:
    try:
        document = report_store.get(investigation_id)
    except KeyError:
        raise HTTPException(status_code=404, detail={
            "code": "report_not_found", "message": "Relatório não disponível nesta sessão. Execute uma nova investigação.",
        }) from None
    return HTMLResponse(document, headers={
        "Content-Disposition": f'attachment; filename="farmlab-{investigation_id}.html"',
        "Cache-Control": "no-store", "X-Content-Type-Options": "nosniff", "Content-Security-Policy": CSP,
    })
