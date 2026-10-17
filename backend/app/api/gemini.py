"""Explicit, minimal connectivity probe; health checks never call Gemini."""

from time import perf_counter

from fastapi import APIRouter, Response
from google.genai import types
from pydantic import Field

from app.config import get_settings
from app.data.contracts import StrictModel
from app.harness import gemini_client


router = APIRouter(prefix="/api/gemini", tags=["gemini"])

_ERROR_STATUS = {
    "missing_api_key": 503,
    "authentication_error": 401,
    "permission_denied": 403,
    "model_not_found": 502,
    "rate_limit": 429,
    "timeout": 504,
    "unavailable": 503,
    "network_error": 503,
    "invalid_request": 502,
    "configuration_error": 503,
    "api_error": 502,
}


class GeminiTestResponse(StrictModel):
    success: bool
    model: str
    latency_ms: int = Field(ge=0)
    message: str
    error_code: str | None = None


def _model_responded(result: types.GenerateContentResponse) -> bool:
    feedback = result.prompt_feedback
    if feedback and feedback.block_reason not in (None, types.BlockedReason.BLOCKED_REASON_UNSPECIFIED):
        return False
    for candidate in result.candidates or []:
        # A small token budget may be consumed by thinking. Reaching that limit
        # still confirms connectivity, but says nothing about report quality.
        if candidate.finish_reason == types.FinishReason.MAX_TOKENS:
            return True
        if candidate.finish_reason not in (None, types.FinishReason.STOP):
            continue
        if candidate.content and any(
            part.text and part.text.strip() and not part.thought
            for part in candidate.content.parts or []
        ):
            return True
    return False


@router.post(
    "/test",
    response_model=GeminiTestResponse,
    responses={
        status: {"model": GeminiTestResponse}
        for status in (401, 403, 429, 502, 503, 504)
    },
)
def test_connection(response: Response) -> GeminiTestResponse:
    settings = get_settings()
    started = perf_counter()
    success = False
    error_code = None
    message = "Conexão com o Gemini verificada."
    try:
        with gemini_client.GeminiClient(settings) as client:
            result = client.generate_content(
                "Responda apenas OK.",
                config=types.GenerateContentConfig(max_output_tokens=32, candidate_count=1),
            )
        success = _model_responded(result)
        if not success:
            response.status_code = 502
            error_code = "invalid_response"
            message = "O Gemini retornou uma resposta vazia ou bloqueada. Não foi possível confirmar o teste."
    except gemini_client.GeminiError as error:
        response.status_code = _ERROR_STATUS.get(error.code, 502)
        error_code = error.code
        message = str(error)

    return GeminiTestResponse(
        success=success,
        model=settings.gemini_model,
        latency_ms=round((perf_counter() - started) * 1000),
        message=message,
        error_code=error_code,
    )
