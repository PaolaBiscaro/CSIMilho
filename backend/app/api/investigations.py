"""Synchronous investigation API; errors expose only local safe messages."""

from fastapi import APIRouter, HTTPException

from app.config import get_settings
from app.data.session_store import DatasetNotFoundError, dataset_store
from app.harness.orchestrator import InvestigationError, run_investigation
from app.harness.schemas import InvestigationRequest, InvestigationResponse
from app.harness.validators import ToolCallValidationError


router = APIRouter(prefix="/api/investigations", tags=["investigations"])


@router.post("", response_model=InvestigationResponse, responses={
    404: {"description": "Dataset não encontrado na sessão."},
    422: {"description": "Requisição ou par inválido."},
    503: {"description": "Não foi possível produzir um relatório válido."},
})
def investigate(request: InvestigationRequest) -> InvestigationResponse:
    try:
        return run_investigation(request, settings=get_settings(), store=dataset_store)
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
