"""Analytical chat routing and executive investigation API."""

import json
from queue import Queue
from threading import Thread
from uuid import UUID

from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse

from app.data.session_store import DatasetNotFoundError, dataset_store
from app.config import get_settings
from app.harness.chat_contracts import CapabilityItem, ChatEnvelopeV2, ChatRequestV2
from app.harness.chat_orchestrator import (
    build_capability_catalog, conversation_memory, run_chat_orchestration,
)
from app.harness.executive_report import ExecutiveReportError, run_investigative_chat
from app.harness.chat_responses import run_analytical_chat
from app.harness.orchestration_contracts import ChatOrchestrationRun
from app.reports.chat_report import chat_report_store, render_chat_report


router = APIRouter(prefix="/api/chat", tags=["analytical-chat"])


@router.get("/capabilities/{dataset_id}", response_model=list[CapabilityItem], responses={
    404: {"description": "Dataset não encontrado na sessão."},
})
def capabilities(dataset_id: UUID) -> list[CapabilityItem]:
    try:
        dataset = dataset_store.get(dataset_id)
    except DatasetNotFoundError:
        raise HTTPException(status_code=404, detail={
            "code": "dataset_not_found", "message": "Dataset não encontrado na sessão.",
        }) from None
    return build_capability_catalog(dataset)


@router.post("/route", response_model=ChatOrchestrationRun, responses={
    404: {"description": "Dataset ou turno anterior não encontrado na sessão."},
    422: {"description": "Escopo da pergunta incompatível com a conversa ou dataset."},
})
def route_chat(request: ChatRequestV2) -> ChatOrchestrationRun:
    try:
        return run_chat_orchestration(
            request, store=dataset_store, memory=conversation_memory,
        )
    except DatasetNotFoundError:
        raise HTTPException(status_code=404, detail={
            "code": "dataset_not_found", "message": "Dataset não encontrado na sessão.",
        }) from None
    except KeyError:
        raise HTTPException(status_code=404, detail={
            "code": "previous_turn_not_found",
            "message": "A pergunta anterior não está mais disponível nesta sessão.",
        }) from None
    except ValueError as error:
        raise HTTPException(status_code=422, detail={
            "code": "invalid_chat_scope", "message": str(error),
        }) from None


_REPORT_ERROR_STATUS = {
    "missing_api_key": 503,
    "authentication_error": 401,
    "permission_denied": 403,
    "rate_limit": 429,
    "timeout": 504,
    "unavailable": 503,
    "network_error": 503,
    "configuration_error": 503,
    "model_not_found": 502,
    "invalid_request": 502,
    "api_error": 502,
    "invalid_response": 502,
    "invalid_executive_report": 502,
    "not_investigative": 422,
    "report_not_ready": 422,
}


@router.post("/investigate", response_model=ChatEnvelopeV2, responses={
    401: {"description": "As credenciais disponíveis foram recusadas."},
    403: {"description": "As credenciais não possuem permissão."},
    404: {"description": "Dataset ou turno anterior não encontrado na sessão."},
    422: {"description": "A pergunta não pode iniciar um relatório investigativo."},
    429: {"description": "As cotas disponíveis foram atingidas."},
    502: {"description": "O relatório do provedor não passou pela validação."},
    503: {"description": "O Gemini está indisponível ou não configurado."},
    504: {"description": "O prazo total da investigação foi excedido."},
})
def investigate_chat(request: ChatRequestV2) -> ChatEnvelopeV2:
    """Return only a Gemini-synthesized report accepted by all local validators."""
    try:
        result = run_investigative_chat(
            request,
            settings=get_settings(),
            store=dataset_store,
            memory=conversation_memory,
        )
        chat_report_store.save(result)
        return result
    except DatasetNotFoundError:
        raise HTTPException(status_code=404, detail={
            "code": "dataset_not_found", "message": "Dataset não encontrado na sessão.",
        }) from None
    except KeyError:
        raise HTTPException(status_code=404, detail={
            "code": "previous_turn_not_found",
            "message": "A pergunta anterior não está mais disponível nesta sessão.",
        }) from None
    except ValueError as error:
        raise HTTPException(status_code=422, detail={
            "code": "invalid_chat_scope", "message": str(error),
        }) from None
    except ExecutiveReportError as error:
        raise HTTPException(
            status_code=_REPORT_ERROR_STATUS.get(error.code, 502),
            detail={
                "code": error.code,
                "message": str(error),
                "retryable": error.code not in {"not_investigative", "report_not_ready"},
            },
        ) from None


def _chat_error(error: Exception) -> HTTPException:
    if isinstance(error, DatasetNotFoundError):
        return HTTPException(status_code=404, detail={
            "code": "dataset_not_found", "message": "Dataset não encontrado na sessão.",
        })
    if isinstance(error, KeyError):
        return HTTPException(status_code=404, detail={
            "code": "previous_turn_not_found",
            "message": "A pergunta anterior não está mais disponível nesta sessão.",
        })
    if isinstance(error, ValueError):
        return HTTPException(status_code=422, detail={
            "code": "invalid_chat_scope", "message": str(error),
        })
    if isinstance(error, ExecutiveReportError):
        return HTTPException(
            status_code=_REPORT_ERROR_STATUS.get(error.code, 502),
            detail={"code": error.code, "message": str(error), "retryable": True},
        )
    return HTTPException(status_code=500, detail={
        "code": "chat_failed", "message": "Não foi possível concluir a solicitação.",
    })


@router.post("/respond", response_model=ChatEnvelopeV2)
def respond_chat(request: ChatRequestV2) -> ChatEnvelopeV2:
    try:
        result = run_analytical_chat(
            request, settings=get_settings(), store=dataset_store, memory=conversation_memory,
        )
        chat_report_store.save(result)
        return result
    except Exception as error:
        raise _chat_error(error) from None


def _sse(event: str, payload: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"


@router.post("/respond/stream")
def respond_chat_stream(request: ChatRequestV2) -> StreamingResponse:
    """Stream safe operational events; never expose prompts or private reasoning."""
    queue: Queue[tuple[str, dict] | None] = Queue()

    def progress(item) -> None:
        payload = item if isinstance(item, dict) else item.model_dump(mode="json")
        queue.put(("progress", payload))

    def worker() -> None:
        try:
            result = run_analytical_chat(
                request, settings=get_settings(), store=dataset_store,
                memory=conversation_memory, progress_sink=progress,
            )
            chat_report_store.save(result)
            queue.put(("result", result.model_dump(mode="json")))
        except Exception as error:
            detail = _chat_error(error)
            body = detail.detail if isinstance(detail.detail, dict) else {"message": str(detail.detail)}
            queue.put(("error", {"status": detail.status_code, **body}))
        finally:
            queue.put(None)

    Thread(target=worker, daemon=True).start()

    def events():
        while True:
            item = queue.get()
            if item is None:
                break
            yield _sse(*item)

    return StreamingResponse(events(), media_type="text/event-stream", headers={
        "Cache-Control": "no-store", "X-Accel-Buffering": "no",
    })


@router.get("/reports/{turn_id}", response_class=HTMLResponse)
def download_chat_report(turn_id: UUID) -> HTMLResponse:
    try:
        envelope = chat_report_store.get(turn_id)
    except KeyError:
        raise HTTPException(status_code=404, detail={
            "code": "report_not_found", "message": "Relatório não encontrado nesta sessão.",
        }) from None
    return HTMLResponse(
        render_chat_report(envelope),
        headers={"Content-Disposition": f'attachment; filename="farmlab-{turn_id}.html"'},
    )
