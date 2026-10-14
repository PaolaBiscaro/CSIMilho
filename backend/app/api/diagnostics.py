"""Development-only deterministic tool execution; no model/API integration."""
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import ValidationError

from app.analytics.common import AnalysisUnavailableError
from app.config import get_settings
from app.data.contracts import StrictModel
from app.data.session_store import DatasetNotFoundError
from app.harness.registry import execute_tool
from app.harness.schemas import NonEmptyText


def require_development():
    if get_settings().app_env != "development":
        raise HTTPException(status_code=404, detail="Recurso indisponível.")


router = APIRouter(prefix="/api/diagnostics", tags=["diagnostics"], dependencies=[Depends(require_development)])


class DiagnosticRequest(StrictModel):
    tool: NonEmptyText
    arguments: dict[str, Any]


@router.post("/tools", include_in_schema=False)
def diagnose_tool(request: DiagnosticRequest):
    try:
        evidence = execute_tool(request.tool, request.arguments)
        # Preserve the specialized schema fields in the JSON response.
        return evidence.model_dump(mode="json")
    except DatasetNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Dataset não encontrado na sessão.") from exc
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail="Parâmetros inválidos para a ferramenta selecionada.") from exc
    except AnalysisUnavailableError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
