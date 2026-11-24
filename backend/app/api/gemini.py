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


class GeminiKeyTestResult(StrictModel):
    slot: int = Field(ge=1, le=3)
    success: bool
    latency_ms: int = Field(ge=0)
    error_code: str | None = None


class GeminiTestResponse(StrictModel):
    success: bool
    model: str
    latency_ms: int = Field(ge=0)
    message: str
    error_code: str | None = None
    configured_key_count: int = Field(ge=0, le=3)
    available_key_count: int = Field(ge=0, le=3)
    key_results: list[GeminiKeyTestResult]


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
    keys = settings.gemini_api_keys
    if not keys:
        response.status_code = 503
        error = gemini_client.GeminiError("missing_api_key")
        return GeminiTestResponse(
            success=False, model=settings.gemini_model, latency_ms=0,
            message=str(error), error_code=error.code,
            configured_key_count=0, available_key_count=0, key_results=[],
        )

    key_results = []
    error_messages: list[tuple[str, str]] = []
    for index, key in enumerate(keys, start=1):
        slot_settings = settings.model_copy(update={
            "gemini_api_key": key,
            "gemini_api_key_2": None,
            "gemini_api_key_3": None,
        })
        started = perf_counter()
        success = False
        error_code = None
        try:
            with gemini_client.GeminiClient(slot_settings) as client:
                result = client.generate_content(
                    "Responda apenas OK.",
                    config=types.GenerateContentConfig(max_output_tokens=32, candidate_count=1),
                )
            success = _model_responded(result)
            if not success:
                error_code = "invalid_response"
                error_messages.append((error_code, "O Gemini retornou uma resposta vazia ou bloqueada."))
        except gemini_client.GeminiError as error:
            error_code = error.code
            error_messages.append((error.code, str(error)))
        key_results.append(GeminiKeyTestResult(
            slot=index,
            success=success,
            latency_ms=round((perf_counter() - started) * 1000),
            error_code=error_code,
        ))

    available = sum(item.success for item in key_results)
    success = available > 0
    error_code = None if available == len(keys) else (
        "partial_availability" if available else error_messages[-1][0]
    )
    if available == len(keys):
        message = ("1 de 1 chave do Gemini está disponível." if len(keys) == 1
                   else f"{available} de {len(keys)} chaves do Gemini estão disponíveis.")
    elif available:
        message = f"Somente {available} de {len(keys)} chaves do Gemini está disponível."
    else:
        message = error_messages[-1][1]
        response.status_code = _ERROR_STATUS.get(error_code, 502)

    return GeminiTestResponse(
        success=success,
        model=settings.gemini_model,
        latency_ms=sum(item.latency_ms for item in key_results),
        message=message,
        error_code=error_code,
        configured_key_count=len(keys),
        available_key_count=available,
        key_results=key_results,
    )
